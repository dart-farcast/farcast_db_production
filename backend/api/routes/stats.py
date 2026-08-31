from fastapi import APIRouter, Depends
from ..cache import cache
from ..auth import get_current_whitelisted_user
from database.data_loader import compute_stats, find_col, SID_ALIASES
import pandas as pd

router = APIRouter()



@router.get('/stats')
def stats(current_user: dict = Depends(get_current_whitelisted_user)):
    allowed_studies = current_user.get('allowed_studies', '*')
    if allowed_studies == '*':
        return cache.stats

    # Scope stats dynamically for restricted user
    study_col = 'Study' if 'Study' in cache.metadata.columns else None
    if not study_col or not isinstance(allowed_studies, list):
        return cache.stats

    allowed_set = {s.strip().lower() for s in allowed_studies}
    meta_mask = cache.metadata[study_col].astype(str).str.strip().str.lower().isin(allowed_set)
    meta_scoped = cache.metadata[meta_mask]
    
    if meta_scoped.empty:
        return {
            'samples': 0, 'drugs': 0, 'assay_samples': {},
            'studies': 0, 'indications': {}, 'top_drugs': [], 'study_list': allowed_studies
        }

    scoped_sids = set(meta_scoped['Sample_ID'])
    overlay_scoped = cache.overlay[cache.overlay['Sample_ID'].isin(scoped_sids)]
    
    a_samples = {}
    from ..data_loader import find_col, SID_ALIASES
    for name, df in cache.assay_dfs.items():
        sid_col = find_col(df, SID_ALIASES)
        if sid_col and sid_col in df.columns:
            cnt = df[df[sid_col].isin(scoped_sids)][sid_col].nunique()
            a_samples[name] = int(cnt)
        else:
            a_samples[name] = 0

    drugs = overlay_scoped['Drug'].replace('', pd.NA).dropna()
    indications = (meta_scoped['CancerType'].replace('', pd.NA).dropna().value_counts().to_dict()
                   if 'CancerType' in meta_scoped.columns else {})
    study_list = sorted(meta_scoped[study_col].replace('', pd.NA).dropna().unique().tolist())

    return {
        'samples':       int(meta_scoped['Sample_ID'].nunique()),
        'drugs':         int(drugs.nunique()),
        'assay_samples': a_samples,
        'studies':       int(meta_scoped[study_col].nunique()),
        'indications':   indications,
        'top_drugs':     drugs.value_counts().head(20).index.tolist(),
        'study_list':    study_list,
    }



@router.get('/debug')
def debug():
    df = cache.assay_dfs.get('Histopathology')
    return {
        'type': str(type(df)),
        'len': len(df) if df is not None else 0,
        'unique_sids': int(df['Sample_ID'].nunique()) if df is not None and 'Sample_ID' in df.columns else 0,
        'cols': list(df.columns) if df is not None else []
    }

@router.get('/assay_types')
def assay_types():
    from ..data_loader import find_col, SID_ALIASES, ARM_ALIASES
    out = []
    for name, df in cache.assay_dfs.items():
        sid_col = find_col(df, SID_ALIASES)
        arm_col = find_col(df, ARM_ALIASES)
        out.append({
            'name':    name,
            'columns': list(df.columns),
            'rows':    len(df),
            'sid_col': sid_col,
            'arm_col': arm_col,
        })
    return out


@router.get('/timepoints')
def timepoints(assay: str = ''):
    df = cache.assay_dfs.get(assay)
    if df is None or 'Timepoint' not in df.columns:
        return []
    return sorted(df['Timepoint'].str.strip().unique().tolist())
