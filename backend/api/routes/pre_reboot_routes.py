"""
FarCast DB v2 — Pre-Reboot Historical Bio-Repository API Routes (2017–2020 MBT)
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List
import pandas as pd
from ..cache import cache
from ..auth import get_current_whitelisted_user

router = APIRouter(tags=["Pre-Reboot Bio-Repository"])


def _parse_multi(val: str) -> list:
    if not val or not val.strip():
        return []
    return [x.strip() for x in val.split(',') if x.strip()]


@router.get('/pre_reboot/stats')
def get_pre_reboot_stats(current_user: dict = Depends(get_current_whitelisted_user)):
    """Returns high-level statistics and breakdown for the 2017–2020 Pre-Reboot Bio-Repository."""
    return cache.pre_reboot_stats


@router.get('/pre_reboot/autocomplete')
def get_pre_reboot_autocomplete(
    field: str = Query('main_cancer_type', description="Field to autocomplete: main_cancer_type, cancer_type, hospital, primary_study, physician, year"),
    q: str = Query('', description="Search prefix / substring"),
    current_user: dict = Depends(get_current_whitelisted_user)
):
    """Returns autocomplete suggestions for pre-reboot repository search filters."""
    df = cache.pre_reboot_metadata
    if df.empty or field not in df.columns:
        return []
    
    q_clean = q.strip().lower()
    unique_vals = df[field].replace('', pd.NA).dropna().unique().tolist()
    
    if q_clean:
        filtered = [v for v in unique_vals if q_clean in str(v).lower()]
    else:
        filtered = unique_vals
        
    return sorted([str(x) for x in filtered[:30]], key=lambda x: str(x).lower())


@router.get('/pre_reboot/search')
def search_pre_reboot(
    mbt: str = Query('', description="MBT Sample ID substring or exact match"),
    main_cancer_type: str = Query('', description="Comma-separated main cancer types"),
    cancer_type: str = Query('', description="Comma-separated specific cancer types"),
    primary_study: str = Query('', description="Comma-separated primary studies"),
    hospital: str = Query('', description="Comma-separated hospital names"),
    year: str = Query('', description="Comma-separated years e.g. 2017,2018,2019,2020"),
    qualification_status: str = Query('', description="Comma-separated qualification statuses"),
    final_qualification: str = Query('', description="Comma-separated final qualifications"),
    ffpe_block: str = Query('', description="true/yes to filter samples with FFPE blocks available"),
    scored_only: str = Query('', description="true/yes to filter samples with T0 or T72 scores"),
    page: int = Query(0, ge=0),
    page_size: int = Query(50, ge=1, le=500),
    sort_col: str = Query('mbt'),
    sort_asc: bool = Query(True),
    current_user: dict = Depends(get_current_whitelisted_user)
):
    """Searches and filters the 22,000+ Pre-Reboot Bio-Repository samples."""
    df = cache.pre_reboot_metadata
    if df.empty:
        return {'total': 0, 'page': page, 'page_size': page_size, 'total_pages': 0, 'results': []}

    mask = pd.Series(True, index=df.index)

    # 1. MBT Sample ID Filter
    if mbt.strip():
        mbt_clean = mbt.strip().lower()
        mask &= df['mbt'].astype(str).str.strip().str.lower().str.contains(mbt_clean, regex=False, na=False)

    # 2. Main Cancer Types
    main_cancers = _parse_multi(main_cancer_type)
    if main_cancers:
        c_set = {c.lower() for c in main_cancers}
        mask &= df['main_cancer_type'].astype(str).str.strip().str.lower().isin(c_set)

    # 3. Cancer Types
    cancers = _parse_multi(cancer_type)
    if cancers:
        c_set = {c.lower() for c in cancers}
        mask &= df['cancer_type'].astype(str).str.strip().str.lower().isin(c_set)

    # 4. Primary Study
    studies = _parse_multi(primary_study)
    if studies:
        s_set = {s.lower() for s in studies}
        mask &= df['primary_study'].astype(str).str.strip().str.lower().isin(s_set)

    # 5. Hospital
    hospitals = _parse_multi(hospital)
    if hospitals:
        h_set = {h.lower() for h in hospitals}
        mask &= df['hospital'].astype(str).str.strip().str.lower().isin(h_set)

    # 6. Year
    years = _parse_multi(year)
    if years:
        y_set = {y.lower() for y in years}
        mask &= df['year'].astype(str).str.strip().str.lower().isin(y_set)

    # 7. Qualification Status
    quals = _parse_multi(qualification_status)
    if quals:
        q_set = {q.lower() for q in quals}
        mask &= df['qualification_status'].astype(str).str.strip().str.lower().isin(q_set)

    # 8. Final Qualification
    final_quals = _parse_multi(final_qualification)
    if final_quals:
        fq_set = {fq.lower() for fq in final_quals}
        if 'final_qualification' in df.columns:
            mask &= df['final_qualification'].astype(str).str.strip().str.lower().isin(fq_set)

    # 9. FFPE Block Availability
    if ffpe_block.strip().lower() in ('true', '1', 'yes'):
        mask &= df['ffpe_block_availability'].astype(str).str.strip().replace({'': pd.NA, 'nan': pd.NA, 'None': pd.NA}).notna()

    # 10. Scored Samples Only
    if scored_only.strip().lower() in ('true', '1', 'yes'):
        t0_s = df['t0_score'].astype(str).str.strip().replace({'': pd.NA, 'nan': pd.NA, 'None': pd.NA}).notna()
        t72_s = df['t72_score'].astype(str).str.strip().replace({'': pd.NA, 'nan': pd.NA, 'None': pd.NA}).notna()
        mask &= (t0_s | t72_s)

    filtered_df = df[mask]
    total_count = len(filtered_df)

    # Sorting
    if sort_col in filtered_df.columns:
        # Check if numeric sortable (e.g. s_no or year or numeric mbt)
        if sort_col in ['s_no', 'year']:
            filtered_df = filtered_df.sort_values(
                by=sort_col,
                ascending=sort_asc,
                key=lambda s: pd.to_numeric(s, errors='coerce').fillna(0)
            )
        else:
            filtered_df = filtered_df.sort_values(
                by=sort_col,
                ascending=sort_asc,
                key=lambda s: s.astype(str).str.lower()
            )

    # Pagination
    start_idx = page * page_size
    end_idx = start_idx + page_size
    paged_df = filtered_df.iloc[start_idx:end_idx]

    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0

    return {
        'total': total_count,
        'page': page,
        'page_size': page_size,
        'total_pages': total_pages,
        'results': paged_df.to_dict(orient='records')
    }


@router.get('/pre_reboot/sample/{mbt_id}')
def get_pre_reboot_sample_detail(mbt_id: str, current_user: dict = Depends(get_current_whitelisted_user)):
    """Retrieves full pathology and block detail record for a specific MBT sample."""
    sample = cache.pre_reboot_mbt_map.get(mbt_id.strip().upper())
    if not sample:
        # Try finding in dataframe
        df = cache.pre_reboot_metadata
        matches = df[df['mbt'].astype(str).str.strip().str.upper() == mbt_id.strip().upper()]
        if not matches.empty:
            return matches.iloc[0].to_dict()
        raise HTTPException(status_code=404, detail=f"Pre-reboot sample '{mbt_id}' not found.")
    return sample
