from fastapi import APIRouter, Depends
from ..cache import cache
from ..auth import get_current_whitelisted_user
from database.data_loader import compute_stats, find_col, SID_ALIASES, ARM_ALIASES
import pandas as pd

router = APIRouter()



@router.get('/stats')
def stats(current_user: dict = Depends(get_current_whitelisted_user)):
    allowed_studies = current_user.get('allowed_studies', '*')
    if allowed_studies == '*':
        return cache.stats

    # Scope stats dynamically for restricted user
    study_col = 'Study' if 'Study' in cache.metadata.columns else ('RegisterType' if 'RegisterType' in cache.metadata.columns else None)
    if not study_col or not isinstance(allowed_studies, list):
        return cache.stats

    allowed_set = {s.strip().lower() for s in allowed_studies}
    meta_mask = cache.metadata[study_col].astype(str).str.strip().str.lower().isin(allowed_set)
    meta_scoped = cache.metadata[meta_mask]
    
    if meta_scoped.empty:
        return {
            'samples': 0, 'qualified_samples': 0, 'disqualified_samples': 0,
            'internal_rd_total': 0, 'internal_rd_qualified': 0,
            'biopharma_total': 0, 'biopharma_qualified': 0,
            'drugs': 0, 'assay_samples': {},
            'studies': 0, 'indications': {}, 'top_drugs': [], 'study_list': allowed_studies
        }

    scoped_sids = set(meta_scoped['Sample_ID'])
    overlay_scoped = cache.overlay[cache.overlay['Sample_ID'].isin(scoped_sids)]
    return compute_stats(meta_scoped, overlay_scoped, cache.assay_dfs)



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
