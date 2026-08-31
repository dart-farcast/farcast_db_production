"""
FarCast DB v2 — Database Layer Package
"""
from .db_client import get_db_connection
from .auth_db import (
    init_auth_db, hash_password, verify_password,
    is_email_whitelisted, log_audit_event
)
from .data_loader import (
    load_metadata, build_overlay, load_assay_dfs,
    build_assay_presence_map, compute_stats, build_indexes,
    find_col, SID_ALIASES, ARM_ALIASES
)
