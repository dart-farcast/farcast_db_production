"""
Autocomplete endpoint — sub-20ms because it reads from in-memory cache.
Supports multi-value prefix search: returns sorted unique matches, strictly scoped by user's study permissions.
"""
from fastapi import APIRouter, Query, Depends
from ..cache import cache
from ..auth import get_current_whitelisted_user
import pandas as pd

router = APIRouter()

FIELD_COL = {
    'drug':       ('overlay', 'Drug'),
    'arm':        ('overlay', 'Arm_Code'),
    'sample':     ('meta',    'Sample_ID'),
    'indication': ('meta',    'CancerType'),
    'tumor_site': ('meta',    'TumorSite'),
    'study':      ('meta',    'Study'),
    'project':    ('meta',    'Project_ID'),
    'hospital':   ('meta',    'Hospital'),
}


@router.get('/autocomplete')
def autocomplete(
    q: str = Query(default='', max_length=100),
    field: str = Query(default='drug', max_length=50),
    current_user: dict = Depends(get_current_whitelisted_user)
):
    q = q.strip().lower()
    src, col = FIELD_COL.get(field, ('meta', 'Sample_ID'))
    
    # ── Study-scoped filtering ───────────────────────────────────────────────
    allowed_studies = current_user.get('allowed_studies', '*')
    
    if src == 'meta':
        df = cache.metadata
        if allowed_studies != '*' and isinstance(allowed_studies, list) and 'Study' in df.columns:
            allowed_set = {s.strip().lower() for s in allowed_studies}
            df = df[df['Study'].astype(str).str.strip().str.lower().isin(allowed_set)]
    else:
        df = cache.overlay
        if allowed_studies != '*' and isinstance(allowed_studies, list):
            study_idx = cache.indexes.get('study', {})
            permitted_sids = set()
            for s in allowed_studies:
                permitted_sids |= study_idx.get(s.strip().lower(), set())
            df = df[df['Sample_ID'].isin(permitted_sids)]

    if col not in df.columns or df.empty:
        return []

    # If querying study field directly for a restricted user, scope study suggestions
    if field == 'study' and allowed_studies != '*' and isinstance(allowed_studies, list):
        filtered_studies = [s for s in allowed_studies if q in s.lower()] if q else allowed_studies
        return sorted(filtered_studies)[:25]

    # If query is empty, return top most frequent values
    if not q:
        top_vals = [str(v).strip() for v in df[col].replace('', pd.NA).dropna().value_counts().index if str(v).strip()]
        return top_vals[:25]

    vals = [str(v).strip() for v in df[col].dropna().unique() if str(v).strip()]
    matches = sorted(
        {v for v in vals if q in v.lower()},
        key=lambda x: (not x.lower().startswith(q), x.lower())
    )
    return matches[:25]

