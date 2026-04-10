"""
Supabase Storage upload module voor Kandidatentekort.
Uses plain requests (no supabase SDK) to upload to Supabase Storage REST API.
"""

import os
import json
import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
BUCKET = "kt-assets"


def _safe_name(name: str) -> str:
    """Maak naam URL-safe."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name).strip("_")[:50]


def _ensure_bucket():
    """Maak bucket aan als die niet bestaat (idempotent)."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return
    try:
        requests.post(
            f"{SUPABASE_URL}/storage/v1/bucket",
            headers={
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "apikey": SUPABASE_SERVICE_KEY,
                "Content-Type": "application/json",
            },
            json={"id": BUCKET, "name": BUCKET, "public": True},
            timeout=10,
        )
    except Exception:
        pass


def _upload_file(storage_path: str, content: bytes, content_type: str) -> bool:
    """Upload a file to Supabase Storage. Returns True on success."""
    try:
        resp = requests.post(
            f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{storage_path}",
            headers={
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "apikey": SUPABASE_SERVICE_KEY,
                "Content-Type": content_type,
                "x-upsert": "true",
            },
            data=content,
            timeout=15,
        )
        if resp.status_code in (200, 201):
            logger.info(f"✅ Uploaded: {storage_path}")
            return True
        else:
            logger.warning(f"⚠️ Upload status {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"❌ Upload failed for {storage_path}: {e}")
        return False


def get_storage_prefix(lead_name: str) -> str:
    """Return the date/name prefix for a lead's files."""
    date_prefix = datetime.now().strftime("%Y%m%d")
    safe = _safe_name(lead_name)
    return f"{date_prefix}/{safe}"


def upload_rapport(html_content: str, lead_name: str) -> str:
    """
    Upload hosted rapport HTML to Supabase Storage, return proxy URL.
    Uses Supabase Storage REST API directly (no SDK).
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        logger.warning("⚠️ SUPABASE_URL or SUPABASE_SERVICE_KEY not set — skipping upload")
        return ""

    _ensure_bucket()

    prefix = get_storage_prefix(lead_name)
    storage_path = f"{prefix}/rapport.html"

    _upload_file(storage_path, html_content.encode("utf-8"), "text/html; charset=utf-8")

    # Return Render proxy URL (serves HTML with correct Content-Type)
    render_base = os.environ.get("RENDER_URL", "https://kandidatentekort-automation.onrender.com")
    return f"{render_base}/rapport?path={storage_path}"


def upload_analysis_json(analysis: dict, lead_name: str) -> str:
    """
    Upload analysis JSON to Supabase Storage for nurture email drip.
    Returns the storage path prefix so nurture system can fetch it.
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return ""

    _ensure_bucket()

    prefix = get_storage_prefix(lead_name)
    storage_path = f"{prefix}/analysis.json"

    content = json.dumps(analysis, ensure_ascii=False, indent=2).encode("utf-8")
    _upload_file(storage_path, content, "application/json; charset=utf-8")

    return prefix


def fetch_analysis_json(storage_prefix: str) -> dict:
    """
    Fetch analysis JSON from Supabase Storage for nurture emails.
    Returns the analysis dict or empty dict on failure.
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY or not storage_prefix:
        return {}

    storage_path = f"{storage_prefix}/analysis.json"

    try:
        # Use public URL for reading (bucket is public)
        resp = requests.get(
            f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{storage_path}",
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            logger.warning(f"⚠️ Could not fetch analysis: {resp.status_code}")
    except Exception as e:
        logger.error(f"❌ Fetch analysis failed: {e}")

    return {}
