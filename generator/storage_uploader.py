"""
Supabase Storage upload module voor Kandidatentekort.
Uses plain requests (no supabase SDK) to upload to Supabase Storage REST API.
"""

import os
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


def upload_rapport(html_content: str, lead_name: str) -> str:
    """
    Upload hosted rapport HTML to Supabase Storage, return proxy URL.
    Uses Supabase Storage REST API directly (no SDK).
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        logger.warning("⚠️ SUPABASE_URL or SUPABASE_SERVICE_KEY not set — skipping upload")
        return ""

    _ensure_bucket()

    date_prefix = datetime.now().strftime("%Y%m%d")
    safe = _safe_name(lead_name)
    storage_path = f"{date_prefix}/{safe}/rapport.html"

    try:
        # Upload via Supabase Storage REST API
        resp = requests.post(
            f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{storage_path}",
            headers={
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "apikey": SUPABASE_SERVICE_KEY,
                "Content-Type": "text/html; charset=utf-8",
                "x-upsert": "true",
            },
            data=html_content.encode("utf-8"),
            timeout=15,
        )

        if resp.status_code in (200, 201):
            logger.info(f"✅ Rapport uploaded: {storage_path}")
        else:
            logger.warning(f"⚠️ Upload status {resp.status_code}: {resp.text[:200]}")

        # Return Netlify proxy URL (serves HTML with correct Content-Type)
        netlify_base = os.environ.get("NETLIFY_URL", "https://kandidatentekort.nl")
        return f"{netlify_base}/.netlify/functions/kt-rapport?path={storage_path}"

    except Exception as e:
        logger.error(f"❌ Rapport upload failed: {e}")
        return ""
