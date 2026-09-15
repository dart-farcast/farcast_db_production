"""
Autocomplete endpoint — sub-20ms because it reads from in-memory cache.
Supports multi-value prefix search: returns sorted unique matches.
"""
from fastapi import APIRouter, Query
from ..cache import cache

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
def autocomplete(q: str = '', field: str = 'drug'):
    q = q.strip().lower()
    src, col = FIELD_COL.get(field, ('meta', 'Sample_ID'))
    df = cache.overlay if src == 'overlay' else cache.metadata

    if col not in df.columns:
        return []

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
