"""
Search endpoint — multi-select, index-based, all filters correctly intersected.

Fixes vs v1:
  - Arm filter: keys now lowercase → matches correctly
  - Assay filter: restricts final_sids to samples present in selected assay
  - Indication/study/site/project: use partial matching (so "HNSCC" matches "HNSCC")
  - Multi-filter: proper AND intersection across all fields
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List
from ..cache import cache
from database.data_loader import find_col, SID_ALIASES, ARM_ALIASES
from ..auth import get_current_whitelisted_user
import pandas as pd


router = APIRouter()


def _parse_multi(value: str) -> list:
    """Split comma-separated param, strip whitespace, drop empties."""
    return [v.strip() for v in value.split(',') if v.strip()]


def _index_match(index: dict, terms: list, partial: bool = True) -> set:
    """
    Union of sample_ids whose index key matches ANY of the terms.
    All index keys are stored lowercase; terms are lowercased here.
    partial=True  → substring match (t in key)
    partial=False → exact match    (t == key)
    """
    result = set()
    for term in terms:
        t = term.strip().lower()
        if not t:
            continue
        for key, sids in index.items():
            if partial:
                if t in key:
                    result |= sids
            else:
                if t == key:
                    result |= sids
    return result


def _norm_drug(s: str) -> str:
    """Normalize drug name for exact strict comparison (whitespace, casing, underscores)."""
    if not s:
        return ""
    return " ".join(str(s).strip().lower().split())


def is_strict_drug_match(drug_val: str, selected_drugs: list) -> bool:
    """
    Check if drug_val strictly matches ANY of the selected_drugs.
    Unlike substring matching, 'Nivolumab_Cmax' will NOT match 'Nivolumab_Cmax + Carboplatin'.
    """
    if not drug_val or not selected_drugs:
        return False
    norm_val = _norm_drug(drug_val)
    norm_val_clean = norm_val.replace('_', ' ').replace('-', ' ')
    for d in selected_drugs:
        norm_d = _norm_drug(d)
        if norm_val == norm_d:
            return True
        norm_d_clean = norm_d.replace('_', ' ').replace('-', ' ')
        if norm_val_clean == norm_d_clean:
            return True
    return False


def is_control_arm(arm_code: str, drug_name: str = '', position: str = '') -> bool:
    """
    Check if an arm is strictly the control arm (RXA / Control / Vehicle).
    Excludes drug treatment arms that might have 'Control' in a secondary field.
    """
    ac = str(arm_code).strip().upper()
    dn = str(drug_name).strip().lower()
    pos = str(position).strip().upper()

    # Standard Control Arm Codes
    if ac in ('RXA', 'RX A', 'RX-A', 'ARM1', 'CTRL', 'CONTROL', 'CONTROL ARM', 'VEHICLE', 'DMSO', 'T0'):
        return True
    if ac.startswith('RXA') or ac.startswith('CTRL'):
        return True
    # Position A with vehicle / baseline / untreated drug description
    if pos == 'A' and any(c in dn for c in ('control', 'vehicle', 'dmso', 'media', 'baseline', 'untreated', 't0', 'igg', 'rxa')):
        return True
    return False


@router.get('/search')
def search(
    drug:           str = '',
    arm:            str = '',
    sample:         str = '',
    indication:     str = '',
    tumor_site:     str = '',
    study:          str = '',
    project:        str = '',
    assay:          str = '',   # comma-separated assay display names
    timepoint:      str = '',
    qualified_only: str = '',
    qualified:      str = '',
    strict_drug:    str = '',   # secondary strict filter: selected drug + control arm only
    current_user: dict = Depends(get_current_whitelisted_user),
):
    idx      = cache.indexes
    overlay  = cache.overlay
    meta     = cache.metadata

    # ── Parse all params ─────────────────────────────────────────────────────
    drugs      = _parse_multi(drug)
    arms       = _parse_multi(arm)
    indications= _parse_multi(indication)
    sites      = _parse_multi(tumor_site)
    studies    = _parse_multi(study)
    projects   = _parse_multi(project)
    assay_list = _parse_multi(assay)
    is_strict  = strict_drug.strip().lower() in ('true', '1', 'yes') and bool(drugs)

    # Start from the full sample universe
    final_sids: set = idx['all_sids'].copy()

    # ── Qualification Status Filter ─────────────────────────────────────────
    is_qual = qualified_only.strip().lower() in ('true', '1', 'yes') or qualified.strip().lower() in ('true', '1', 'yes')
    if is_qual:
        final_sids &= idx.get('qualified_sids', set())

    # ── 0. Mandatory User Study Scoping ──────────────────────────────────────
    allowed_studies = current_user.get('allowed_studies', '*')
    if allowed_studies != '*' and isinstance(allowed_studies, list):
        scoped_sids = _index_match(idx['study'], allowed_studies, partial=False)
        final_sids &= scoped_sids


    # ── 1. Assay pre-filter: samples must be present in ALL selected assays (AND) ──
    if assay_list:
        assay_universe: set = idx['all_sids'].copy()
        for aname in assay_list:
            sids_for_assay = cache.assay_sids_map.get(aname, set())
            assay_universe &= sids_for_assay
        final_sids &= assay_universe

    # ── 2. Drug filter (strict exact or partial match) ────────────────────────
    if drugs:
        if is_strict:
            strict_matching_sids = set(
                overlay[overlay['Drug'].apply(lambda v: is_strict_drug_match(v, drugs))]['Sample_ID']
            )
            final_sids &= strict_matching_sids
        else:
            final_sids &= _index_match(idx['drug'], drugs, partial=True)

    # ── 3. Arm filter (partial match, index keys are lowercase) ───────────────
    if arms:
        final_sids &= _index_match(idx['arm'], arms, partial=True)

    # ── 4. Metadata filters (partial match so partial typing still works) ─────
    if indications:
        final_sids &= _index_match(idx['cancer'], indications, partial=True)
    if sites:
        final_sids &= _index_match(idx['site'], sites, partial=True)
    if studies:
        final_sids &= _index_match(idx['study'], studies, partial=True)
    if projects:
        final_sids &= _index_match(idx['project'], projects, partial=True)

    # ── 5. Sample ID substring filter ────────────────────────────────────────
    if sample:
        s = sample.strip().lower()
        final_sids &= {sid for sid in final_sids if s in sid.lower()}

    if not final_sids:
        return {'total': 0, 'results': [], 'assay_cols': []}

    # ── 6. Build matched (sample_id, arm_code) pairs for arm highlighting & filtering ────
    ov_filtered = overlay[overlay['Sample_ID'].isin(final_sids)]

    any_arm_drug_filter = bool(drugs or arms)
    if is_strict:
        # Strict mode: keep only EXACT matched drug arms AND control arm (RXA / Vehicle)
        drug_mask = ov_filtered['Drug'].apply(lambda v: is_strict_drug_match(v, drugs))
        ctrl_mask = ov_filtered.apply(
            lambda r: is_control_arm(r.get('Arm_Code', ''), r.get('Drug', ''), r.get('Position', '')), axis=1)
        strict_mask = drug_mask | ctrl_mask
        
        matched_pairs = set(zip(ov_filtered[strict_mask]['Sample_ID'],
                                ov_filtered[strict_mask]['Arm_Code']))
        # In strict mode, limit overlay rendering strictly to these arms
        ov_for_arms = ov_filtered[strict_mask]
    elif any_arm_drug_filter:
        mask = pd.Series(True, index=ov_filtered.index)
        if drugs:
            mask &= ov_filtered['Drug'].str.lower().apply(
                lambda v: any(d.lower() in v.lower() for d in drugs))
        if arms:
            mask &= ov_filtered['Arm_Code'].str.lower().apply(
                lambda v: any(a.lower() in v.lower() for a in arms))
        matched_pairs = set(zip(ov_filtered[mask]['Sample_ID'],
                                ov_filtered[mask]['Arm_Code']))
        ov_for_arms = ov_filtered
    else:
        matched_pairs = set(zip(ov_filtered['Sample_ID'], ov_filtered['Arm_Code']))
        ov_for_arms = ov_filtered

    # ── 7. Load assay row data for selected assays ────────────────────────────
    assay_by_sid: dict = {}
    assay_cols:   list = []

    if assay_list:
        for aname in assay_list:
            adf = cache.assay_dfs.get(aname)
            if adf is None:
                continue
            adf = adf.copy()
            sid_col = find_col(adf, SID_ALIASES)
            arm_col = find_col(adf, ARM_ALIASES)
            if not sid_col:
                continue
            if sid_col != 'Sample_ID':
                adf = adf.rename(columns={sid_col: 'Sample_ID'})
            if arm_col and arm_col != 'Arms':
                adf = adf.rename(columns={arm_col: 'Arms'})
                arm_col = 'Arms'

            # Restrict assay rows to matched samples
            adf = adf[adf['Sample_ID'].isin(final_sids)]

            # If strict filter or arm/drug filter active, restrict assay rows to matched pairs only
            if arm_col and (is_strict or any_arm_drug_filter) and matched_pairs:
                adf['Arms'] = adf['Arms'].str.strip().str.upper()
                adf = adf[adf.apply(
                    lambda r: (r['Sample_ID'], r['Arms']) in matched_pairs, axis=1)]

            if timepoint and 'Timepoint' in adf.columns:
                adf = adf[adf['Timepoint'].str.upper() == timepoint.strip().upper()]

            if not assay_cols:
                assay_cols = list(adf.columns)

            adf['assay'] = aname

            for sid, grp in adf.groupby('Sample_ID'):
                assay_by_sid.setdefault(sid, []).extend(
                    grp.to_dict(orient='records'))

    # ── 8. Assemble per-sample results ────────────────────────────────────────
    meta_idx       = cache.meta_idx
    assay_presence = cache.assay_presence
    results = []

    for sid in sorted(final_sids):
        m_dict    = meta_idx.get(sid, {'Sample_ID': sid})
        sample_ov = ov_for_arms[ov_for_arms['Sample_ID'] == sid]
        arms_out  = [
            {
                'position': r['Position'],
                'arm_code': r['Arm_Code'],
                'drug':     r['Drug'],
                'matched':  (sid, r['Arm_Code']) in matched_pairs,
                'is_control': is_control_arm(r.get('Arm_Code', ''), r.get('Drug', ''), r.get('Position', '')),
            }
            for _, r in sample_ov.iterrows()
        ]
        results.append({
            'metadata':       m_dict,
            'arms':           arms_out,
            'assay_rows':     assay_by_sid.get(sid, []),
            'assay_cols':     assay_cols,
            'assays_present': assay_presence.get(sid, []),
        })

    return {'total': len(results), 'results': results, 'assay_cols': assay_cols}


@router.get('/sample_assays')
def sample_assays(
    sample_id:   str = '',
    strict_drug: str = '',
    drug:        str = '',
):
    """Return all assay rows for one sample across every assay type (with optional strict drug + control arm filter)."""
    if not sample_id:
        return {}
    sid = sample_id.strip()
    is_strict = strict_drug.strip().lower() in ('true', '1', 'yes') and bool(drug)
    drugs = _parse_multi(drug) if is_strict else []

    allowed_arms = set()
    if is_strict:
        ov = cache.overlay[cache.overlay['Sample_ID'] == sid]
        if not ov.empty:
            drug_mask = ov['Drug'].apply(lambda v: is_strict_drug_match(v, drugs))
            ctrl_mask = ov.apply(
                lambda r: is_control_arm(r.get('Arm_Code', ''), r.get('Drug', ''), r.get('Position', '')), axis=1)
            allowed_arms = set(ov[drug_mask | ctrl_mask]['Arm_Code'].astype(str).str.strip().str.upper())

    result = {}
    for name, df in cache.assay_dfs.items():
        sid_col = find_col(df, SID_ALIASES)
        arm_col = find_col(df, ARM_ALIASES)
        if not sid_col:
            continue
        rows = df[df[sid_col].astype(str).str.strip() == sid]
        if is_strict and allowed_arms and arm_col and arm_col in rows.columns:
            rows = rows[rows[arm_col].astype(str).str.strip().str.upper().isin(allowed_arms)]
        if not rows.empty:
            result[name] = {
                'columns': list(rows.columns),
                'rows':    rows.to_dict(orient='records'),
            }
    return result


class CohortRequest(BaseModel):
    sample_ids:  List[str]
    strict_drug: bool = False
    drugs:       List[str] = []


@router.post('/cohort_assays')
def cohort_assays(req: CohortRequest):
    """Return all assay rows for multiple samples across every assay type (with strict drug + control arm filtering support)."""
    if not req.sample_ids:
        return {}
    sids = {sid.strip() for sid in req.sample_ids if sid.strip()}
    if not sids:
        return {}

    strict_pairs = set()
    if req.strict_drug and req.drugs:
        ov = cache.overlay[cache.overlay['Sample_ID'].isin(sids)]
        if not ov.empty:
            drug_mask = ov['Drug'].apply(lambda v: is_strict_drug_match(v, req.drugs))
            ctrl_mask = ov.apply(
                lambda r: is_control_arm(r.get('Arm_Code', ''), r.get('Drug', ''), r.get('Position', '')), axis=1)
            strict_ov = ov[drug_mask | ctrl_mask]
            strict_pairs = set(zip(strict_ov['Sample_ID'].astype(str).str.strip(),
                                   strict_ov['Arm_Code'].astype(str).str.strip().str.upper()))

    result = {}
    for name, df in cache.assay_dfs.items():
        sid_col = find_col(df, SID_ALIASES)
        arm_col = find_col(df, ARM_ALIASES)
        if not sid_col:
            continue
        rows = df[df[sid_col].astype(str).str.strip().isin(sids)]
        
        if req.strict_drug and strict_pairs and arm_col and arm_col in rows.columns:
            rows = rows[rows.apply(
                lambda r: (str(r[sid_col]).strip(), str(r[arm_col]).strip().upper()) in strict_pairs,
                axis=1
            )]

        if not rows.empty:
            result[name] = {
                'columns': list(rows.columns),
                'rows':    rows.to_dict(orient='records'),
            }
    return result

