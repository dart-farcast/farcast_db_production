"""
Autocomplete endpoint — sub-20ms because it reads from in-memory cache.
Supports multi-value prefix search: returns sorted unique matches.
"""
from fastapi import APIRouter, Query, Depends
from ..cache import cache
from ..auth import get_current_whitelisted_user

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
    q: str = '',
    field: str = 'drug',
    qualified_only: str = '',
    qualified: str = '',
    current_user: dict = Depends(get_current_whitelisted_user)
):
    q = q.strip().lower()
    src, col = FIELD_COL.get(field, ('meta', 'Sample_ID'))
    df = (cache.overlay if src == 'overlay' else cache.metadata).copy()

    if col not in df.columns:
        return []

    # RBAC Study Scoping
    allowed_studies = current_user.get('allowed_studies', '*')
    if allowed_studies != '*' and isinstance(allowed_studies, list):
        if 'Study' in cache.metadata.columns and 'Sample_ID' in df.columns:
            allowed_studies_lower = {s.strip().lower() for s in allowed_studies}
            permitted_sids = set(cache.metadata[
                cache.metadata['Study'].astype(str).str.strip().str.lower().isin(allowed_studies_lower)
            ]['Sample_ID'])
            df = df[df['Sample_ID'].isin(permitted_sids)]

    # RBAC Sample Scoping
    allowed_samples = current_user.get('allowed_samples', '*')
    if allowed_samples != '*' and isinstance(allowed_samples, list):
        if 'Sample_ID' in df.columns:
            allowed_samples_lower = {s.strip().lower() for s in allowed_samples}
            df = df[df['Sample_ID'].astype(str).str.strip().str.lower().isin(allowed_samples_lower)]

    is_qual = qualified_only.strip().lower() in ('true', '1', 'yes') or qualified.strip().lower() in ('true', '1', 'yes')
    if is_qual and 'qualified_sids' in cache.indexes:
        qual_sids = cache.indexes['qualified_sids']
        if 'Sample_ID' in df.columns:
            df = df[df['Sample_ID'].isin(qual_sids)]

    # If query is empty, return top most frequent values
    if not q:
        top_vals = [str(v).strip() for v in df[col].replace('', None).dropna().value_counts().index if str(v).strip()]
        return top_vals[:25]

    vals = [str(v).strip() for v in df[col].dropna().unique() if str(v).strip()]
    matches = sorted(
        {v for v in vals if q in v.lower()},
        key=lambda x: (not x.lower().startswith(q), x.lower())
    )
    return matches[:25]
