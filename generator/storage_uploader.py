"""
Supabase Storage upload module voor Kandidatentekort.
Upload rapport HTML naar persistent storage en return Netlify proxy URL.
"""

import os
from datetime import datetime
from typing import Optional


def _get_storage_client():
    """Maak Supabase storage client met service_role key."""
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        raise ValueError("SUPABASE_URL of SUPABASE_SERVICE_KEY ontbreekt")
    return create_client(url, key)


def _ensure_bucket(client, bucket: str = "kt-assets"):
    """Maak bucket aan als die niet bestaat (idempotent)."""
    try:
        client.storage.create_bucket(bucket, options={"public": True})
    except Exception:
        pass


def _safe_name(name: str) -> str:
    """Maak naam URL-safe."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name).strip("_")[:50]


def upload_bytes(
    data: bytes,
    filename: str,
    content_type: str,
    lead_name: str,
    bucket: str = "kt-assets",
) -> str:
    """Upload bytes naar Supabase Storage, return public URL."""
    try:
        client = _get_storage_client()
        _ensure_bucket(client, bucket)

        date_prefix = datetime.now().strftime("%Y%m%d")
        safe = _safe_name(lead_name)
        storage_path = f"{date_prefix}/{safe}/{filename}"

        client.storage.from_(bucket).upload(
            storage_path, data, {"content-type": content_type, "upsert": "true"}
        )

        public_url = client.storage.from_(bucket).get_public_url(storage_path)
        print(f"   ✅ Storage upload: {storage_path}")
        return public_url

    except Exception as e:
        print(f"   ⚠️ Storage upload fout ({filename}): {e}")
        return ""


def upload_rapport(html_content: str, lead_name: str) -> str:
    """
    Upload hosted rapport HTML, return Netlify proxy URL.
    Supabase Storage serves HTML as text/plain (XSS prevention),
    so we route through a Netlify function that sets text/html.
    """
    # Upload to Supabase Storage
    date_prefix = datetime.now().strftime("%Y%m%d")
    safe = _safe_name(lead_name)
    storage_path = f"{date_prefix}/{safe}/rapport.html"

    upload_bytes(
        data=html_content.encode("utf-8"),
        filename="rapport.html",
        content_type="text/html; charset=utf-8",
        lead_name=lead_name,
    )

    # Return Netlify proxy URL instead of direct Supabase URL
    netlify_base = os.environ.get("NETLIFY_URL", "https://kandidatentekort.nl")
    return f"{netlify_base}/.netlify/functions/kt-rapport?path={storage_path}"


def upload_file(file_path: str, lead_name: str) -> str:
    """Upload bestand van disk, return public URL."""
    if not file_path or not os.path.exists(file_path):
        return ""

    filename = os.path.basename(file_path)
    content_type = "image/png" if filename.endswith(".png") else "text/html"

    with open(file_path, "rb") as f:
        data = f.read()

    return upload_bytes(data, filename, content_type, lead_name)
