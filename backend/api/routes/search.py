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
    # Starting from all_sids and intersecting ensures empty assay_sids_map entries
    # still correctly zero out the results.
    if assay_list:
        assay_universe: set = idx['all_sids'].copy()  # start full
        for aname in assay_list:
            sids_for_assay = cache.assay_sids_map.get(aname, set())
            assay_universe &= sids_for_assay           # AND: must be in every assay
        final_sids &= assay_universe

    # ── 2. Drug filter (partial match) ────────────────────────────────────────
    if drugs:
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

    # ── 6. Build matched (sample_id, arm_code) pairs for arm highlighting ────
    ov_filtered = overlay[overlay['Sample_ID'].isin(final_sids)]

    any_arm_drug_filter = bool(drugs or arms)
    if any_arm_drug_filter:
        mask = pd.Series(True, index=ov_filtered.index)
        if drugs:
            mask &= ov_filtered['Drug'].str.lower().apply(
                lambda v: any(d.lower() in v.lower() for d in drugs))
        if arms:
            mask &= ov_filtered['Arm_Code'].str.lower().apply(
                lambda v: any(a.lower() in v.lower() for a in arms))
        matched_pairs = set(zip(ov_filtered[mask]['Sample_ID'],
                                ov_filtered[mask]['Arm_Code']))
    else:
        matched_pairs = set(zip(ov_filtered['Sample_ID'], ov_filtered['Arm_Code']))

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

            # If arm/drug filter active, restrict assay rows to matched pairs only
            if arm_col and any_arm_drug_filter and matched_pairs:
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
        sample_ov = ov_filtered[ov_filtered['Sample_ID'] == sid]
        arms_out  = [
            {
                'position': r['Position'],
                'arm_code': r['Arm_Code'],
                'drug':     r['Drug'],
                'matched':  (sid, r['Arm_Code']) in matched_pairs,
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
def sample_assays(sample_id: str = ''):
    """Return all assay rows for one sample across every assay type."""
    if not sample_id:
        return {}
    sid = sample_id.strip()
    result = {}
    for name, df in cache.assay_dfs.items():
        sid_col = find_col(df, SID_ALIASES)
        if not sid_col:
            continue
        rows = df[df[sid_col].str.strip() == sid]
        if not rows.empty:
            result[name] = {
                'columns': list(rows.columns),
                'rows':    rows.to_dict(orient='records'),
            }
    return result

class CohortRequest(BaseModel):
    sample_ids: List[str]

@router.post('/cohort_assays')
def cohort_assays(req: CohortRequest):
    """Return all assay rows for multiple samples across every assay type."""
    if not req.sample_ids:
        return {}
    sids = {sid.strip() for sid in req.sample_ids if sid.strip()}
    if not sids:
        return {}
    
    result = {}
    for name, df in cache.assay_dfs.items():
        sid_col = find_col(df, SID_ALIASES)
        if not sid_col:
            continue
        rows = df[df[sid_col].astype(str).str.strip().isin(sids)]
        if not rows.empty:
            result[name] = {
                'columns': list(rows.columns),
                'rows':    rows.to_dict(orient='records'),
            }
    return result
