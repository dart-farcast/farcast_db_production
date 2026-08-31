import os, re
from fastapi import APIRouter, UploadFile, Form
from ..cache import cache
from ..data_loader import rcsv, DATA_DIR, discover_assays, load_assay_dfs, build_assay_presence_map, compute_stats, build_indexes

router = APIRouter()


@router.post('/upload')
async def upload(table: str = Form(...), file: UploadFile = None):
    if not file or not table:
        return {'error': 'Missing file or table name'}
    safe = re.sub(r'[^a-zA-Z0-9_\-]', '_', table.lower()) + '.csv'
    path = os.path.join(DATA_DIR, safe)
    content = await file.read()
    with open(path, 'wb') as f:
        f.write(content)
    try:
        df = rcsv(path)
        # Reload assay data into cache
        cache.assay_paths    = discover_assays()
        cache.assay_dfs      = load_assay_dfs(cache.assay_paths)
        cache.assay_presence = build_assay_presence_map(cache.assay_dfs)
        cache.stats          = compute_stats(cache.metadata, cache.overlay, cache.assay_dfs)
        return {'ok': True, 'rows': len(df), 'cols': list(df.columns), 'file': safe}
    except Exception as e:
        return {'error': str(e)}
