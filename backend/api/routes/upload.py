import os, re
from fastapi import APIRouter, UploadFile, Form, Depends, HTTPException, status
from ..cache import cache, reload_cache
from ..auth import get_current_admin_user
from database.data_loader import rcsv, DATA_DIR

router = APIRouter()

MAX_UPLOAD_SIZE = 25 * 1024 * 1024  # 25 MB max

@router.post('/upload')
async def upload(
    table: str = Form(...),
    file: UploadFile = None,
    current_admin: dict = Depends(get_current_admin_user)
):
    if not file or not table:
        raise HTTPException(status_code=400, detail="Missing file or table name.")

    # Validate table name pattern
    table_clean = table.strip()
    if not re.match(r'^[a-zA-Z0-9_\-]+$', table_clean):
        raise HTTPException(status_code=400, detail="Invalid table name. Only alphanumeric, dashes, and underscores allowed.")

    # Validate filename extension
    if not file.filename.lower().endswith(('.csv', '.tsv')):
        raise HTTPException(status_code=400, detail="Only CSV/TSV data files are supported.")

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE // (1024*1024)}MB.")

    safe = re.sub(r'[^a-zA-Z0-9_\-]', '_', table_clean.lower()) + '.csv'
    path = os.path.join(DATA_DIR, safe)
    
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(path, 'wb') as f:
        f.write(content)

    try:
        df = rcsv(path)
        if df.empty:
            raise ValueError("Uploaded file contains no rows.")
        # Reload cache safely
        reload_cache()
        return {
            'success': True,
            'ok': True,
            'rows': len(df),
            'cols': list(df.columns),
            'file': safe
        }
    except Exception as e:
        if os.path.exists(path):
            try: os.remove(path)
            except Exception: pass
        raise HTTPException(status_code=400, detail=f"Failed to process dataset: {str(e)}")

