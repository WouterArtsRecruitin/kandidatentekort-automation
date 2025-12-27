#!/usr/bin/env python3
"""
KANDIDATENTEKORT.NL - WEBHOOK AUTOMATION V5.0
Deploy: Render.com | Updated: 2025-11-28
- V2: Pipedrive organization, person, deal creation
- V3: Claude AI vacancy analysis + report email
- V3.1: Professional report template with Before/After comparison
- V3.2: PDF, DOCX and Word file extraction for vacancy analysis
- V3.3: Fixed Typeform file download with authentication
- V4.0: ULTIMATE email template - Score visualization, Category breakdown,
        Before/After comparison, Full improved text, Numbered checklist, Bonus tips
- V4.1: OUTLOOK COMPATIBLE - Full table-based layout, MSO conditionals, no flex/gradients
- V5.0: TRUST-FIRST EMAIL NURTURE - 8 automated follow-up emails over 30 days
"""

import os
import io
import json
import logging
import smtplib
import requests
import threading
import time
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify

# PDF and DOCX extraction
try:
    from PyPDF2 import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Config
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
PIPEDRIVE_API_TOKEN = os.getenv('PIPEDRIVE_API_TOKEN')
TYPEFORM_API_TOKEN = os.getenv('TYPEFORM_API_TOKEN')  # For file downloads
GMAIL_USER = os.getenv('GMAIL_USER', 'artsrecruitin@gmail.com')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD') or os.getenv('GMAIL_PASS')
PIPEDRIVE_BASE = "https://api.pipedrive.com/v1"
PIPELINE_ID = 4
STAGE_ID = 21

# Email Nurture Custom Field Keys (from Pipedrive)
FIELD_RAPPORT_VERZONDEN = "337f9ccca15334e6e4f937ca5ef0055f13ed0c63"
FIELD_EMAIL_SEQUENCE_STATUS = "22d33c7f119119e178f391a272739c571cf2e29b"
FIELD_LAATSTE_EMAIL = "753f37a1abc8e161c7982c1379a306b21fae1bab"

# Email sequence timing (days after rapport verzonden)
EMAIL_SCHEDULE = {
    1: {"day": 1, "template_id": 55, "name": "Check-in"},
    2: {"day": 3, "template_id": 56, "name": "Is het gelukt"},
    3: {"day": 5, "template_id": 57, "name": "Resultaten"},
    4: {"day": 8, "template_id": 58, "name": "Tip Functietitel"},
    5: {"day": 11, "template_id": 59, "name": "Tip Salaris"},
    6: {"day": 14, "template_id": 60, "name": "Tip Opening"},
    7: {"day": 21, "template_id": 61, "name": "Gesprek Aanbod"},
    8: {"day": 30, "template_id": 62, "name": "Final Check-in"},
}

# Stage filter: Only send nurture emails to deals in stage 21 (Gekwalificeerd)
# Deals in stage 22+ have active contact, so no automated emails needed
NURTURE_ACTIVE_STAGE = 21  # Gekwalificeerd


def extract_text_from_file(file_url):
    """
    Download and extract text from PDF, DOCX, or DOC files.
    Returns extracted text or empty string on failure.
    Typeform file URLs require Bearer token authentication.
    """
    if not file_url:
        return ""

    try:
        logger.info(f"📄 Downloading file: {file_url[:80]}...")

        # Prepare headers - Typeform API requires authentication
        headers = {}
        if TYPEFORM_API_TOKEN and 'typeform.com' in file_url:
            headers['Authorization'] = f'Bearer {TYPEFORM_API_TOKEN}'
            logger.info("🔑 Using Typeform API authentication")

        # Download the file
        response = requests.get(file_url, headers=headers, timeout=30)

        # Log response details for debugging
        content_type = response.headers.get('content-type', 'unknown')
        logger.info(f"📦 Response: status={response.status_code}, content-type={content_type}, size={len(response.content)} bytes")

        if response.status_code != 200:
            logger.error(f"❌ Failed to download file: {response.status_code}")
            return ""

        content = response.content

        # Check if we got an error page instead of the file
        if len(content) < 100 and b'error' in content.lower():
            logger.error(f"❌ Got error response: {content[:200]}")
            return ""

        # Detect file type by content (magic bytes) - most reliable
        if content[:4] == b'%PDF':
            logger.info("📄 Detected PDF by magic bytes")
            return extract_pdf_text(content)
        elif content[:2] == b'PK':  # DOCX/XLSX/ZIP files start with PK
            logger.info("📄 Detected DOCX/ZIP by magic bytes")
            return extract_docx_text(content)
        elif content[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':  # Old .doc format (OLE)
            logger.warning("⚠️ Old .doc (OLE) format - not supported, try converting to DOCX")
            return ""

        # Fallback: try by content-type header
        if 'pdf' in content_type:
            return extract_pdf_text(content)
        elif 'wordprocessingml' in content_type or 'msword' in content_type:
            return extract_docx_text(content)

        # Last resort: try by URL extension
        file_url_lower = file_url.lower()
        if '.pdf' in file_url_lower:
            return extract_pdf_text(content)
        elif '.docx' in file_url_lower:
            return extract_docx_text(content)

        logger.warning(f"⚠️ Could not determine file type. Content starts with: {content[:20]}")
        return ""

    except Exception as e:
        logger.error(f"❌ File extraction error: {e}")
        return ""


def extract_pdf_text(content):
    """Extract text from PDF content"""
    if not PDF_AVAILABLE:
        logger.error("❌ PyPDF2 not available")
        return ""

    try:
        pdf_file = io.BytesIO(content)
        reader = PdfReader(pdf_file)

        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        full_text = "\n".join(text_parts)
        logger.info(f"✅ PDF extracted: {len(full_text)} characters from {len(reader.pages)} pages")
        return full_text.strip()

    except Exception as e:
        logger.error(f"❌ PDF extraction failed: {e}")
        return ""


def extract_docx_text(content):
    """Extract text from DOCX content"""
    if not DOCX_AVAILABLE:
        logger.error("❌ python-docx not available")
        return ""

    try:
        docx_file = io.BytesIO(content)
        doc = Document(docx_file)

        text_parts = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text)

        # Also extract text from tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        text_parts.append(cell.text)

        full_text = "\n".join(text_parts)
        logger.info(f"✅ DOCX extracted: {len(full_text)} characters")
        return full_text.strip()

    except Exception as e:
        logger.error(f"❌ DOCX extraction failed: {e}")
        return ""


def get_confirmation_email_html(voornaam, bedrijf, functie):
    return f'''<!DOCTYPE html><html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;font-family:Inter,-apple-system,sans-serif;background:#f9fafb;">
<table width="100%" style="padding:40px 20px;"><tr><td align="center">
<table width="600" style="background:#fff;border-radius:12px;box-shadow:0 8px 32px rgba(44,62,80,0.12);">
<tr><td style="background:linear-gradient(135deg,#ff6b35,#e55a2b);color:#fff;padding:40px 30px;text-align:center;">
<div style="font-size:28px;font-weight:800;">✅ Ontvangen!</div>
<div style="font-size:16px;opacity:0.95;">Je vacature-analyse aanvraag is binnen</div></td></tr>
<tr><td style="padding:35px 30px;">
<p style="font-size:19px;font-weight:700;">Hoi {voornaam},</p>
<p style="color:#374151;">Bedankt! We hebben je vacature voor <strong style="color:#ff6b35;">{functie}</strong> bij <strong style="color:#ff6b35;">{bedrijf}</strong> ontvangen.</p>
<table width="100%" style="background:#f0f4f8;border-left:5px solid #ff6b35;border-radius:0 12px 12px 0;margin:25px 0;">
<tr><td style="padding:25px;">
<div style="font-size:18px;font-weight:700;color:#2c3e50;">⏰ Wat kun je verwachten?</div>
<ul style="color:#374151;padding-left:20px;">
<li><strong>Binnen 24 uur</strong> ontvang je een uitgebreide analyse</li>
<li>Concrete verbeterpunten voor meer sollicitanten</li>
<li>Score-overzicht op 6 belangrijke gebieden</li>
<li>Direct toepasbare tips</li></ul></td></tr></table>
<p style="color:#374151;">Vragen? Reply gewoon op deze email.</p></td></tr>
<tr><td style="padding:0 30px 35px;border-top:1px solid #f1f3f4;">
<table style="padding-top:25px;"><tr><td>
<p style="margin:0 0 5px;font-weight:700;color:#2c3e50;">Wouter Arts</p>
<p style="margin:0;color:#6b7280;font-size:14px;">Founder & Recruitment Specialist</p>
<p style="margin:0;color:#ff6b35;font-size:14px;font-weight:600;">Kandidatentekort.nl</p>
</td></tr></table></td></tr>
<tr><td style="background:#2c3e50;color:#fff;padding:20px 30px;text-align:center;font-size:12px;">
© 2025 Kandidatentekort.nl | Recruitin B.V.</td></tr>
</table></td></tr></table></body></html>'''


def send_email(to_email, subject, html_body):
    logger.info(f"📧 Sending to: {to_email}")
    if not GMAIL_APP_PASSWORD:
        logger.error("❌ GMAIL_APP_PASSWORD not set!")
        return False
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"Kandidatentekort.nl <{GMAIL_USER}>"
        msg['To'] = to_email
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=30)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD.replace(" ", ""))
        server.send_message(msg)
        server.quit()
        logger.info(f"✅ Email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"❌ Email failed: {e}")
        return False


def send_confirmation_email(to_email, voornaam, bedrijf, functie):
    return send_email(to_email, f"✅ Ontvangen: Vacature-analyse voor {functie}",
                      get_confirmation_email_html(voornaam, bedrijf, functie))


def analyze_vacancy_with_claude(vacature_text, bedrijf, sector=""):
    """Analyze vacancy text with Claude AI and return structured analysis"""
    if not ANTHROPIC_API_KEY:
        logger.error("❌ ANTHROPIC_API_KEY not set!")
        return None

    prompt = f"""Je bent een expert recruitment copywriter gespecialiseerd in de Nederlandse technische arbeidsmarkt. Analyseer deze vacaturetekst en verbeter ze voor maximale kandidaat-conversie.

## VACATURETEKST OM TE ANALYSEREN:

{vacature_text}

## CONTEXT:
- Bedrijf: {bedrijf}
- Sector: {sector if sector else 'Niet opgegeven'}

## JOUW OPDRACHT:

Analyseer deze vacaturetekst en lever het volgende in EXACT dit JSON format:

{{
    "overall_score": 7.2,
    "score_section": "Aantrekkelijkheid: 7/10 - Duidelijkheid: 6/10 - USP's: 5/10 - Call-to-action: 8/10",
    "top_3_improvements": [
        "Eerste concrete verbetering",
        "Tweede concrete verbetering",
        "Derde concrete verbetering"
    ],
    "improved_text": "De volledige verbeterde vacaturetekst hier (400-600 woorden, pakkende opening, duidelijke functie-inhoud, concrete arbeidsvoorwaarden, sterke employer branding, overtuigende call-to-action)",
    "bonus_tips": [
        "Eerste bonus tip voor de recruiter",
        "Tweede bonus tip"
    ]
}}

BELANGRIJK: Antwoord ALLEEN met valid JSON, geen tekst ervoor of erna."""

    try:
        logger.info("🤖 Starting Claude analysis...")
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 4000,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=60
        )

        if r.status_code == 200:
            response_text = r.json()['content'][0]['text']
            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                analysis = json.loads(response_text[json_start:json_end])
                logger.info(f"✅ Claude analysis complete: score={analysis.get('overall_score')}")
                return analysis
            else:
                logger.error(f"❌ No JSON found in Claude response")
                return None
        else:
            logger.error(f"❌ Claude API error: {r.status_code} - {r.text[:200]}")
            return None

    except Exception as e:
        logger.error(f"❌ Claude analysis failed: {e}")
        return None


def get_analysis_email_html(voornaam, bedrijf, analysis, original_text=""):
    """
    Generate the ULTIMATE professional analysis report email HTML V4.1
    OUTLOOK COMPATIBLE - No flex, no gradients, all table-based layout
    Features: Score visualization, Before/After, Checklist, Improved text, Tips
    """
    score = analysis.get('overall_score', 'N/A')
    score_section = analysis.get('score_section', '')
    improvements = analysis.get('top_3_improvements', [])
    improved_text = analysis.get('improved_text', '')
    bonus_tips = analysis.get('bonus_tips', [])

    # Generate HTML for improvements (numbered) - OUTLOOK COMPATIBLE
    improvements_html = ''.join([
        f'''<tr>
        <td style="padding:12px 0;border-bottom:1px solid #FDE68A;">
        <table cellpadding="0" cellspacing="0" width="100%"><tr>
        <td width="40" valign="top"><table cellpadding="0" cellspacing="0"><tr><td style="width:32px;height:32px;background-color:#F59E0B;text-align:center;font-weight:bold;color:white;font-size:14px;font-family:Arial,sans-serif;mso-line-height-rule:exactly;line-height:32px;">{i+1}</td></tr></table></td>
        <td style="padding-left:12px;color:#78350F;font-size:14px;line-height:22px;font-family:Arial,sans-serif;">{imp}</td>
        </tr></table>
        </td></tr>''' for i, imp in enumerate(improvements)
    ])

    # Generate HTML for bonus tips - OUTLOOK COMPATIBLE (table-based)
    tips_html = ''.join([
        f'''<tr><td style="padding:8px 0;">
        <table cellpadding="0" cellspacing="0" width="100%" style="background-color:#ffffff;"><tr>
        <td width="40" valign="top" style="padding:12px;font-size:18px;">💡</td>
        <td style="padding:12px;color:#5B21B6;font-size:14px;line-height:22px;font-family:Arial,sans-serif;">{tip}</td>
        </tr></table>
        </td></tr>''' for tip in bonus_tips
    ])

    # Truncate original text for before/after display
    original_display = original_text[:500] + '...' if len(original_text) > 500 else original_text
    improved_preview = improved_text[:500] + '...' if len(improved_text) > 500 else improved_text

    # Escape newlines for HTML display
    original_display = original_display.replace('\n', '<br>')
    improved_preview = improved_preview.replace('\n', '<br>')
    improved_text_html = improved_text.replace('\n', '<br>')

    # Calculate score color and label based on score
    if isinstance(score, (int, float)):
        score_num = float(score)
        if score_num >= 8.0:
            score_color = "#10B981"
            score_bg = "#ECFDF5"
            score_border = "#10B981"
            score_label = "Uitstekend"
            score_emoji = "🏆"
        elif score_num >= 6.5:
            score_color = "#3B82F6"
            score_bg = "#EFF6FF"
            score_border = "#3B82F6"
            score_label = "Goed"
            score_emoji = "👍"
        elif score_num >= 5.0:
            score_color = "#F59E0B"
            score_bg = "#FFFBEB"
            score_border = "#F59E0B"
            score_label = "Kan beter"
            score_emoji = "📈"
        else:
            score_color = "#EF4444"
            score_bg = "#FEF2F2"
            score_border = "#EF4444"
            score_label = "Verbetering nodig"
            score_emoji = "⚠️"
    else:
        score_color = "#6B7280"
        score_bg = "#F9FAFB"
        score_border = "#6B7280"
        score_label = "Beoordeeld"
        score_emoji = "📊"

    # Parse score_section into categories - OUTLOOK COMPATIBLE
    categories_html = ""
    if score_section:
        import re
        score_parts = re.findall(r'([A-Za-z-]+):\s*(\d+)/10', score_section)
        if score_parts:
            categories_html = '<table width="100%" cellpadding="0" cellspacing="0" style="margin-top:20px;"><tr>'
            for name, cat_score in score_parts[:4]:
                cat_score_int = int(cat_score)
                if cat_score_int >= 7:
                    cat_color = "#10B981"
                    cat_icon = "✅"
                elif cat_score_int >= 5:
                    cat_color = "#F59E0B"
                    cat_icon = "⚡"
                else:
                    cat_color = "#EF4444"
                    cat_icon = "❗"
                categories_html += f'''<td width="25%" align="center" style="padding:10px;">
                <table cellpadding="0" cellspacing="0"><tr><td align="center" style="font-size:24px;padding-bottom:4px;">{cat_icon}</td></tr>
                <tr><td align="center" style="font-size:24px;font-weight:bold;color:{cat_color};font-family:Arial,sans-serif;">{cat_score}</td></tr>
                <tr><td align="center" style="font-size:11px;color:#6B7280;text-transform:uppercase;font-family:Arial,sans-serif;">{name}</td></tr></table>
                </td>'''
            categories_html += '</tr></table>'

    return f'''<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<!--[if mso]>
<xml>
<o:OfficeDocumentSettings>
<o:AllowPNG/>
<o:PixelsPerInch>96</o:PixelsPerInch>
</o:OfficeDocumentSettings>
</xml>
<![endif]-->
<style type="text/css">
body, table, td {{margin:0;padding:0;font-family:Arial,Helvetica,sans-serif;}}
img {{border:0;height:auto;line-height:100%;outline:none;text-decoration:none;}}
table {{border-collapse:collapse !important;}}
</style>
</head>
<body style="margin:0;padding:0;background-color:#f3f4f6;width:100%;">

<!-- OUTLOOK WRAPPER -->
<!--[if mso]>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f3f4f6;">
<tr><td align="center" style="padding:30px 0;">
<![endif]-->

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f3f4f6;">
<tr><td align="center" style="padding:30px 15px;">

<table role="presentation" width="650" cellpadding="0" cellspacing="0" border="0" style="background-color:#ffffff;max-width:650px;">

<!-- ════════════════════════════════════════════════════════════════════════ -->
<!-- HEADER -->
<!-- ════════════════════════════════════════════════════════════════════════ -->
<tr>
<td style="background-color:#1E3A8A;padding:40px 35px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
<tr>
<td width="60" valign="middle">
<table role="presentation" cellpadding="0" cellspacing="0" border="0">
<tr><td style="width:56px;height:56px;background-color:#FF6B35;text-align:center;font-size:26px;font-weight:bold;color:#ffffff;font-family:Arial,sans-serif;line-height:56px;">R</td></tr>
</table>
</td>
<td style="padding-left:16px;" valign="middle">
<p style="margin:0;color:#ffffff;font-size:20px;font-weight:bold;font-family:Arial,sans-serif;">RECRUITIN</p>
<p style="margin:4px 0 0 0;color:#E0E7FF;font-size:12px;font-family:Arial,sans-serif;">Vacature Intelligence Platform</p>
</td>
</tr>
</table>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:30px;">
<tr><td>
<p style="margin:0 0 8px 0;color:#93C5FD;font-size:12px;font-weight:bold;text-transform:uppercase;letter-spacing:1px;font-family:Arial,sans-serif;">AI-POWERED ANALYSE</p>
<p style="margin:0;color:#ffffff;font-size:28px;font-weight:bold;font-family:Arial,sans-serif;">📊 Vacature Analyse Rapport</p>
<p style="margin:10px 0 0 0;color:#E0E7FF;font-size:15px;font-family:Arial,sans-serif;">Gepersonaliseerd voor <strong style="color:#ffffff;">{bedrijf}</strong></p>
</td></tr>
</table>
</td>
</tr>

<!-- ════════════════════════════════════════════════════════════════════════ -->
<!-- SCORE SECTION -->
<!-- ════════════════════════════════════════════════════════════════════════ -->
<tr>
<td style="padding:45px 35px;background-color:#f8fafc;" align="center">
<!-- Score Box -->
<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:20px;">
<tr><td align="center" style="width:140px;height:140px;border:8px solid {score_color};background-color:#ffffff;">
<p style="margin:0;font-size:52px;font-weight:bold;color:{score_color};font-family:Arial,sans-serif;line-height:1;">{score}</p>
<p style="margin:5px 0 0 0;font-size:16px;color:#9CA3AF;font-family:Arial,sans-serif;">/10</p>
</td></tr>
</table>
<!-- Score Label -->
<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:15px;">
<tr><td style="background-color:{score_bg};border:2px solid {score_border};padding:10px 24px;">
<p style="margin:0;font-size:14px;font-weight:bold;color:{score_color};font-family:Arial,sans-serif;">{score_emoji} {score_label}</p>
</td></tr>
</table>
<!-- Score Breakdown -->
<p style="margin:0;color:#6B7280;font-size:13px;font-family:Arial,sans-serif;line-height:1.6;max-width:450px;">{score_section}</p>
{categories_html}
</td>
</tr>

<!-- ════════════════════════════════════════════════════════════════════════ -->
<!-- INTRO -->
<!-- ════════════════════════════════════════════════════════════════════════ -->
<tr>
<td style="padding:0 35px 30px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
<tr>
<td width="4" style="background-color:#FF6B35;"></td>
<td style="padding-left:20px;">
<p style="margin:0 0 12px 0;font-size:20px;font-weight:bold;color:#1F2937;font-family:Arial,sans-serif;">Hoi {voornaam}! 👋</p>
<p style="margin:0;color:#4B5563;font-size:15px;line-height:24px;font-family:Arial,sans-serif;">Bedankt voor het uploaden van je vacature via <strong style="color:#FF6B35;">kandidatentekort.nl</strong>. Onze AI heeft je tekst grondig geanalyseerd. Hieronder vind je de complete resultaten met concrete verbeteringen.</p>
</td>
</tr>
</table>
</td>
</tr>

<!-- ════════════════════════════════════════════════════════════════════════ -->
<!-- TOP 3 VERBETERPUNTEN -->
<!-- ════════════════════════════════════════════════════════════════════════ -->
<tr>
<td style="padding:0 35px 30px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#FFFBEB;border:2px solid #F59E0B;">
<tr><td style="padding:25px;">
<!-- Header -->
<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:20px;">
<tr>
<td width="48" valign="middle"><table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr><td style="width:44px;height:44px;background-color:#F59E0B;text-align:center;font-size:20px;line-height:44px;">🎯</td></tr></table></td>
<td style="padding-left:14px;" valign="middle">
<p style="margin:0 0 2px 0;font-size:11px;font-weight:bold;color:#B45309;text-transform:uppercase;font-family:Arial,sans-serif;">Prioriteit</p>
<p style="margin:0;font-size:18px;font-weight:bold;color:#92400E;font-family:Arial,sans-serif;">Top 3 Verbeterpunten</p>
</td>
</tr>
</table>
<!-- List -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{improvements_html}</table>
</td></tr>
</table>
</td>
</tr>

<!-- ════════════════════════════════════════════════════════════════════════ -->
<!-- BEFORE / AFTER -->
<!-- ════════════════════════════════════════════════════════════════════════ -->
<tr>
<td style="padding:0 35px 30px;">
<p style="margin:0 0 20px 0;text-align:center;font-size:20px;font-weight:bold;color:#1F2937;font-family:Arial,sans-serif;">📝 Voor & Na Optimalisatie</p>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
<tr>
<!-- BEFORE -->
<td width="48%" valign="top" style="background-color:#FEF2F2;border:2px solid #FECACA;padding:18px;">
<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:12px;">
<tr><td style="background-color:#EF4444;padding:5px 12px;"><p style="margin:0;font-size:11px;font-weight:bold;color:#ffffff;text-transform:uppercase;font-family:Arial,sans-serif;">❌ Origineel</p></td></tr>
</table>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#ffffff;border:1px solid #FECACA;">
<tr><td style="padding:14px;font-size:12px;color:#6B7280;line-height:20px;font-family:Arial,sans-serif;">{original_display}</td></tr>
</table>
</td>
<td width="4%"></td>
<!-- AFTER -->
<td width="48%" valign="top" style="background-color:#ECFDF5;border:2px solid #A7F3D0;padding:18px;">
<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:12px;">
<tr><td style="background-color:#10B981;padding:5px 12px;"><p style="margin:0;font-size:11px;font-weight:bold;color:#ffffff;text-transform:uppercase;font-family:Arial,sans-serif;">✅ Geoptimaliseerd</p></td></tr>
</table>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#ffffff;border:1px solid #A7F3D0;">
<tr><td style="padding:14px;font-size:12px;color:#374151;line-height:20px;font-family:Arial,sans-serif;">{improved_preview}</td></tr>
</table>
</td>
</tr>
</table>
</td>
</tr>

<!-- ════════════════════════════════════════════════════════════════════════ -->
<!-- FULL IMPROVED TEXT -->
<!-- ════════════════════════════════════════════════════════════════════════ -->
<tr>
<td style="padding:0 35px 30px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#ECFDF5;border:2px solid #10B981;">
<tr><td style="padding:25px;">
<!-- Header -->
<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:20px;">
<tr>
<td width="48" valign="middle"><table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr><td style="width:44px;height:44px;background-color:#10B981;text-align:center;font-size:20px;line-height:44px;">✍️</td></tr></table></td>
<td style="padding-left:14px;" valign="middle">
<p style="margin:0 0 2px 0;font-size:11px;font-weight:bold;color:#047857;text-transform:uppercase;font-family:Arial,sans-serif;">Direct te gebruiken</p>
<p style="margin:0;font-size:18px;font-weight:bold;color:#065F46;font-family:Arial,sans-serif;">Verbeterde Vacaturetekst</p>
</td>
</tr>
</table>
<!-- Text -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#ffffff;border:1px solid #A7F3D0;">
<tr><td style="padding:20px;font-size:14px;color:#374151;line-height:24px;font-family:Arial,sans-serif;">{improved_text_html}</td></tr>
</table>
<p style="margin:18px 0 0 0;text-align:center;font-size:13px;color:#059669;font-family:Arial,sans-serif;">💾 Kopieer deze tekst en plaats direct in je vacature</p>
</td></tr>
</table>
</td>
</tr>

<!-- ════════════════════════════════════════════════════════════════════════ -->
<!-- BONUS TIPS -->
<!-- ════════════════════════════════════════════════════════════════════════ -->
<tr>
<td style="padding:0 35px 30px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#F5F3FF;border:2px solid #8B5CF6;">
<tr><td style="padding:25px;">
<!-- Header -->
<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:20px;">
<tr>
<td width="48" valign="middle"><table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr><td style="width:44px;height:44px;background-color:#8B5CF6;text-align:center;font-size:20px;line-height:44px;">🚀</td></tr></table></td>
<td style="padding-left:14px;" valign="middle">
<p style="margin:0 0 2px 0;font-size:11px;font-weight:bold;color:#6D28D9;text-transform:uppercase;font-family:Arial,sans-serif;">Extra waarde</p>
<p style="margin:0;font-size:18px;font-weight:bold;color:#5B21B6;font-family:Arial,sans-serif;">Bonus Tips van de Expert</p>
</td>
</tr>
</table>
<!-- Tips -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{tips_html}</table>
</td></tr>
</table>
</td>
</tr>

<!-- ════════════════════════════════════════════════════════════════════════ -->
<!-- CTA SECTION -->
<!-- ════════════════════════════════════════════════════════════════════════ -->
<tr>
<td style="padding:0 35px 35px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#1E3A8A;">
<tr><td style="padding:35px;text-align:center;">
<p style="margin:0 0 10px 0;font-size:22px;font-weight:bold;color:#ffffff;font-family:Arial,sans-serif;">Wil je nog meer resultaat?</p>
<p style="margin:0 0 25px 0;font-size:15px;color:#E0E7FF;line-height:22px;font-family:Arial,sans-serif;">Plan een gratis adviesgesprek van 30 minuten.<br>Bespreek je vacature met een recruitment specialist.</p>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center">
<tr>
<td style="padding:0 6px;">
<table role="presentation" cellpadding="0" cellspacing="0" border="0">
<tr><td style="background-color:#10B981;padding:14px 24px;">
<a href="https://calendly.com/wouter-arts-/vacature-analyse-advies" style="color:#ffffff;font-size:14px;font-weight:bold;text-decoration:none;font-family:Arial,sans-serif;">📅 Plan Adviesgesprek</a>
</td></tr>
</table>
</td>
<td style="padding:0 6px;">
<table role="presentation" cellpadding="0" cellspacing="0" border="0">
<tr><td style="background-color:#25D366;padding:14px 24px;">
<a href="https://wa.me/31614314593?text=Hoi%20Wouter,%20ik%20heb%20mijn%20vacature-analyse%20ontvangen!" style="color:#ffffff;font-size:14px;font-weight:bold;text-decoration:none;font-family:Arial,sans-serif;">💬 WhatsApp</a>
</td></tr>
</table>
</td>
</tr>
</table>
</td></tr>
</table>
</td>
</tr>

<!-- ════════════════════════════════════════════════════════════════════════ -->
<!-- FOOTER -->
<!-- ════════════════════════════════════════════════════════════════════════ -->
<tr>
<td style="background-color:#111827;padding:30px 35px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
<tr>
<td valign="top">
<p style="margin:0 0 4px 0;font-size:17px;font-weight:bold;color:#ffffff;font-family:Arial,sans-serif;">Wouter Arts</p>
<p style="margin:0 0 2px 0;font-size:13px;color:#9CA3AF;font-family:Arial,sans-serif;">Founder & Recruitment Specialist</p>
<p style="margin:0;font-size:14px;font-weight:bold;color:#FF6B35;font-family:Arial,sans-serif;">Kandidatentekort.nl</p>
</td>
<td valign="top" align="right">
<p style="margin:0;font-size:12px;color:#9CA3AF;line-height:22px;font-family:Arial,sans-serif;">
📞 06-14314593<br>
📧 warts@recruitin.nl<br>
🌐 kandidatentekort.nl
</p>
</td>
</tr>
</table>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:20px;border-top:1px solid #374151;">
<tr><td style="padding-top:20px;text-align:center;">
<p style="margin:0;color:#6B7280;font-size:11px;font-family:Arial,sans-serif;">© 2025 Kandidatentekort.nl | Recruitin B.V. | Made with ❤️ in Nederland</p>
</td></tr>
</table>
</td>
</tr>

</table>
</td></tr>
</table>

<!--[if mso]>
</td></tr>
</table>
<![endif]-->

</body>
</html>'''


def send_analysis_email(to_email, voornaam, bedrijf, analysis, original_text=""):
    """Send the vacancy analysis report email"""
    return send_email(
        to_email,
        f"🎯 Jouw Vacature-Analyse voor {bedrijf} is Klaar!",
        get_analysis_email_html(voornaam, bedrijf, analysis, original_text)
    )


def parse_typeform_data(webhook_data):
    """
    Parse Typeform webhook - handles ALL field types robustly
    """
    result = {
        'email': '',
        'voornaam': 'daar',
        'contact': 'Onbekend',
        'telefoon': '',
        'bedrijf': 'Onbekend',
        'vacature': '',
        'functie': 'vacature',
        'sector': '',
        'file_url': ''
    }

    try:
        form_response = webhook_data.get('form_response', {})
        answers = form_response.get('answers', [])

        logger.info(f"📋 Parsing {len(answers)} answers")

        # Collect all values by type
        texts = []  # All short_text values

        for i, answer in enumerate(answers):
            if not isinstance(answer, dict):
                continue

            field = answer.get('field', {})
            if not isinstance(field, dict):
                continue

            field_type = field.get('type', '')
            field_id = field.get('id', '')

            logger.info(f"📋 Answer {i}: type={field_type}, id={field_id}")

            # Extract value based on field type
            if field_type == 'email':
                result['email'] = answer.get('email', '')
                logger.info(f"✅ Found email: {result['email']}")

            elif field_type == 'phone_number':
                result['telefoon'] = answer.get('phone_number', '')
                logger.info(f"✅ Found phone: {result['telefoon']}")

            elif field_type == 'short_text':
                text = answer.get('text', '')
                texts.append(text)
                logger.info(f"📝 Found text: {text[:50]}...")

            elif field_type == 'long_text':
                text = answer.get('text', '')
                result['vacature'] = text
                result['functie'] = text.split('\n')[0][:50] if text else 'vacature'
                logger.info(f"📝 Found long text (vacature)")

            elif field_type == 'multiple_choice':
                choice = answer.get('choice', {})
                if isinstance(choice, dict):
                    label = choice.get('label', '')
                    if not result['sector']:
                        result['sector'] = label
                    logger.info(f"📝 Found choice: {label}")

            elif field_type == 'file_upload':
                result['file_url'] = answer.get('file_url', '')
                logger.info(f"📎 Found file: {result['file_url'][:50]}...")

            elif field_type == 'contact_info':
                contact_info = answer.get('contact_info', {})
                if isinstance(contact_info, dict):
                    if contact_info.get('email'):
                        result['email'] = contact_info['email']
                    if contact_info.get('first_name'):
                        result['voornaam'] = contact_info['first_name']
                        result['contact'] = f"{contact_info.get('first_name', '')} {contact_info.get('last_name', '')}".strip()
                    if contact_info.get('phone_number'):
                        result['telefoon'] = contact_info['phone_number']
                    if contact_info.get('company'):
                        result['bedrijf'] = contact_info['company']
                    logger.info(f"✅ Found contact_info block")

        # Process collected texts (voornaam, achternaam, bedrijf order)
        if texts:
            if len(texts) >= 1 and (not result['voornaam'] or result['voornaam'] == 'daar'):
                result['voornaam'] = texts[0]
                result['contact'] = texts[0]
            if len(texts) >= 2:
                result['contact'] = f"{texts[0]} {texts[1]}".strip()
            if len(texts) >= 3 and (not result['bedrijf'] or result['bedrijf'] == 'Onbekend'):
                result['bedrijf'] = texts[2]  # 3rd text field is company

        logger.info(f"📋 Final: email={result['email']}, contact={result['contact']}, bedrijf={result['bedrijf']}")

    except Exception as e:
        logger.error(f"❌ Parse error: {e}", exc_info=True)

    return result


def create_pipedrive_organization(name):
    """Create organization in Pipedrive"""
    if not PIPEDRIVE_API_TOKEN or not name or name == 'Onbekend':
        return None
    try:
        r = requests.post(
            f"{PIPEDRIVE_BASE}/organizations",
            params={"api_token": PIPEDRIVE_API_TOKEN},
            json={"name": name},
            timeout=30
        )
        if r.status_code == 201:
            org_id = r.json().get('data', {}).get('id')
            logger.info(f"✅ Created organization: {name} (ID: {org_id})")
            return org_id
        else:
            logger.warning(f"Org creation failed: {r.status_code} - {r.text[:200]}")
    except Exception as e:
        logger.error(f"Pipedrive org error: {e}")
    return None


def create_pipedrive_person(contact, email, telefoon, org_id=None):
    if not PIPEDRIVE_API_TOKEN:
        return None
    try:
        data = {
            "name": contact,
            "email": [{"value": email, "primary": True}],
            "phone": [{"value": telefoon, "primary": True}] if telefoon else []
        }
        if org_id:
            data["org_id"] = org_id

        r = requests.post(
            f"{PIPEDRIVE_BASE}/persons",
            params={"api_token": PIPEDRIVE_API_TOKEN},
            json=data,
            timeout=30
        )
        if r.status_code == 201:
            person_id = r.json().get('data', {}).get('id')
            logger.info(f"✅ Created person: {contact} (ID: {person_id})")
            return person_id
        else:
            logger.warning(f"Person creation failed: {r.status_code} - {r.text[:200]}")
    except Exception as e:
        logger.error(f"Pipedrive person error: {e}")
    return None


def create_pipedrive_deal(title, person_id, org_id=None, vacature="", file_url="", analysis=""):
    if not PIPEDRIVE_API_TOKEN:
        return None
    try:
        deal_data = {
            "title": title,
            "person_id": person_id,
            "pipeline_id": PIPELINE_ID,
            "stage_id": STAGE_ID
        }
        if org_id:
            deal_data["org_id"] = org_id

        r = requests.post(
            f"{PIPEDRIVE_BASE}/deals",
            params={"api_token": PIPEDRIVE_API_TOKEN},
            json=deal_data,
            timeout=30
        )
        if r.status_code == 201:
            deal_id = r.json().get('data', {}).get('id')
            logger.info(f"✅ Created deal: {title} (ID: {deal_id})")

            # Build note content
            note_parts = []
            if vacature:
                note_parts.append(f"📋 VACATURE:\n{vacature[:2000]}")
            if file_url:
                note_parts.append(f"📎 BESTAND:\n{file_url}")
            if analysis:
                note_parts.append(f"🤖 ANALYSE:\n{analysis}")

            if note_parts:
                requests.post(
                    f"{PIPEDRIVE_BASE}/notes",
                    params={"api_token": PIPEDRIVE_API_TOKEN},
                    json={
                        "deal_id": deal_id,
                        "content": "\n\n".join(note_parts)
                    },
                    timeout=30
                )
            return deal_id
        else:
            logger.warning(f"Deal creation failed: {r.status_code} - {r.text[:200]}")
    except Exception as e:
        logger.error(f"Pipedrive deal error: {e}")
    return None


def find_person_by_email(email):
    """Search for existing person by email in Pipedrive"""
    if not PIPEDRIVE_API_TOKEN or not email:
        return None
    try:
        r = requests.get(
            f"{PIPEDRIVE_BASE}/persons/search",
            params={
                "api_token": PIPEDRIVE_API_TOKEN,
                "term": email,
                "fields": "email",
                "limit": 5
            },
            timeout=30
        )
        if r.status_code == 200:
            items = r.json().get('data', {}).get('items', [])
            for item in items:
                person = item.get('item', {})
                person_emails = person.get('emails', [])
                # Check if email matches exactly
                for pe in person_emails:
                    if isinstance(pe, str) and pe.lower() == email.lower():
                        person_id = person.get('id')
                        logger.info(f"🔍 Found existing person by email: {email} (ID: {person_id})")
                        return person_id
        logger.info(f"🔍 No existing person found for email: {email}")
    except Exception as e:
        logger.error(f"Pipedrive person search error: {e}")
    return None


def get_person_deals_in_pipeline(person_id, pipeline_id):
    """Get existing deals for a person in a specific pipeline"""
    if not PIPEDRIVE_API_TOKEN or not person_id:
        return []
    try:
        r = requests.get(
            f"{PIPEDRIVE_BASE}/persons/{person_id}/deals",
            params={
                "api_token": PIPEDRIVE_API_TOKEN,
                "status": "open",
                "limit": 50
            },
            timeout=30
        )
        if r.status_code == 200:
            deals = r.json().get('data', []) or []
            pipeline_deals = [d for d in deals if d.get('pipeline_id') == pipeline_id]
            logger.info(f"🔍 Found {len(pipeline_deals)} deals for person {person_id} in pipeline {pipeline_id}")
            return pipeline_deals
    except Exception as e:
        logger.error(f"Pipedrive person deals error: {e}")
    return []


def update_deal_with_vacancy(deal_id, title, vacancy_text, file_url, analysis):
    """Update an existing deal with vacancy info and add note"""
    if not PIPEDRIVE_API_TOKEN or not deal_id:
        return False
    try:
        # Update deal title
        r = requests.put(
            f"{PIPEDRIVE_BASE}/deals/{deal_id}",
            params={"api_token": PIPEDRIVE_API_TOKEN},
            json={"title": title},
            timeout=30
        )
        if r.status_code != 200:
            logger.warning(f"Deal update failed: {r.status_code}")

        # Add vacancy info as note
        note_parts = []
        note_parts.append("🔄 UPDATE VIA TYPEFORM FORMULIER")
        if vacancy_text:
            note_parts.append(f"📋 VACATURE:\n{vacancy_text[:2000]}")
        if file_url:
            note_parts.append(f"📎 BESTAND:\n{file_url}")
        if analysis:
            note_parts.append(f"🤖 ANALYSE:\n{analysis}")

        if note_parts:
            requests.post(
                f"{PIPEDRIVE_BASE}/notes",
                params={"api_token": PIPEDRIVE_API_TOKEN},
                json={
                    "deal_id": deal_id,
                    "content": "\n\n".join(note_parts)
                },
                timeout=30
            )
        logger.info(f"✅ Updated existing deal {deal_id} with vacancy info")
        return True
    except Exception as e:
        logger.error(f"Pipedrive deal update error: {e}")
    return False


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "healthy",
        "version": "5.0",
        "features": ["typeform", "analysis", "nurture"],
        "email": bool(GMAIL_APP_PASSWORD),
        "pipedrive": bool(PIPEDRIVE_API_TOKEN),
        "claude": bool(ANTHROPIC_API_KEY),
        "typeform": bool(TYPEFORM_API_TOKEN)
    }), 200


@app.route("/webhook/typeform", methods=["POST"])
def typeform_webhook():
    logger.info("🎯 WEBHOOK RECEIVED")

    try:
        data = request.get_json(force=True, silent=True) or {}
        logger.info(f"📥 Keys: {list(data.keys())}")

        # Parse the data
        p = parse_typeform_data(data)

        # Validate email
        if not p['email'] or '@' not in p['email']:
            logger.error(f"❌ No email found in: {p}")
            return jsonify({"error": "No email", "parsed": p}), 400

        # Send confirmation email immediately
        confirmation_sent = send_confirmation_email(
            p['email'],
            p['voornaam'],
            p['bedrijf'],
            p['functie']
        )

        # Get vacancy text - prefer file upload over text field
        vacancy_text = p['vacature']

        # Try to extract text from uploaded file (PDF, DOCX, DOC)
        if p['file_url']:
            logger.info(f"📎 File uploaded, attempting extraction...")
            extracted_text = extract_text_from_file(p['file_url'])
            if extracted_text and len(extracted_text) > 50:
                logger.info(f"✅ Using extracted file text ({len(extracted_text)} chars)")
                vacancy_text = extracted_text
            else:
                logger.info(f"⚠️ File extraction failed or empty, using text field")

        # Run Claude analysis if we have vacancy text
        analysis = None
        analysis_sent = False
        if vacancy_text and len(vacancy_text) > 50:
            analysis = analyze_vacancy_with_claude(vacancy_text, p['bedrijf'], p['sector'])
            if analysis:
                analysis_sent = send_analysis_email(p['email'], p['voornaam'], p['bedrijf'], analysis, vacancy_text)

        # Build analysis summary for Pipedrive notes
        analysis_summary = ""
        if analysis:
            analysis_summary = f"""SCORE: {analysis.get('overall_score', 'N/A')}/10
{analysis.get('score_section', '')}

TOP 3 VERBETERPUNTEN:
{chr(10).join(['- ' + imp for imp in analysis.get('top_3_improvements', [])])}

VERBETERDE TEKST:
{analysis.get('improved_text', '')[:1500]}"""

        # CHECK FOR EXISTING DEAL (from Meta Lead or previous submission)
        deal_id = None
        person_id = None
        org_id = None
        updated_existing = False

        # First, check if person already exists by email
        existing_person_id = find_person_by_email(p['email'])

        if existing_person_id:
            logger.info(f"🔍 Found existing person {existing_person_id}, checking for deals in Pipeline {PIPELINE_ID}")
            # Check if they have an existing deal in Pipeline 4
            existing_deals = get_person_deals_in_pipeline(existing_person_id, PIPELINE_ID)

            if existing_deals:
                # Update the most recent existing deal
                existing_deal = existing_deals[0]  # Most recent
                deal_id = existing_deal.get('id')
                person_id = existing_person_id
                org_id = existing_deal.get('org_id')

                new_title = f"Vacature Analyse - {p['functie']} - {p['bedrijf']}"
                update_deal_with_vacancy(deal_id, new_title, vacancy_text, p['file_url'], analysis_summary)
                updated_existing = True
                logger.info(f"✅ Updated EXISTING deal {deal_id} with vacancy info (Meta Lead flow)")

        # If no existing deal found, create new records
        if not deal_id:
            org_id = create_pipedrive_organization(p['bedrijf'])
            person_id = existing_person_id or create_pipedrive_person(p['contact'], p['email'], p['telefoon'], org_id)
            deal_id = create_pipedrive_deal(
                f"Vacature Analyse - {p['functie']} - {p['bedrijf']}",
                person_id,
                org_id,
                vacancy_text,  # Use extracted text if available
                p['file_url'],
                analysis_summary
            )
            logger.info(f"✅ Created NEW deal {deal_id} (no existing deal found)")

        logger.info(f"✅ Done: confirmation={confirmation_sent}, analysis={analysis_sent}, org={org_id}, person={person_id}, deal={deal_id}, updated_existing={updated_existing}")

        return jsonify({
            "success": True,
            "confirmation_sent": confirmation_sent,
            "analysis_sent": analysis_sent,
            "org_id": org_id,
            "person_id": person_id,
            "deal_id": deal_id
        }), 200

    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/test-email", methods=["GET"])
def test_email():
    to = request.args.get('to', 'artsrecruitin@gmail.com')
    ok = send_confirmation_email(to, "Test", "Test Bedrijf", "Test Vacature")
    return jsonify({"success": ok, "to": to}), 200 if ok else 500


@app.route("/debug", methods=["POST"])
def debug_webhook():
    """Debug endpoint - returns what was received"""
    data = request.get_json(force=True, silent=True) or {}
    parsed = parse_typeform_data(data)
    return jsonify({
        "received_keys": list(data.keys()),
        "parsed": parsed,
        "raw_answers": data.get('form_response', {}).get('answers', [])
    }), 200


# =============================================================================
# TRUST-FIRST EMAIL NURTURE SYSTEM V5.0
# =============================================================================

def get_nurture_email_html(email_num, voornaam, functie_titel):
    """Generate HTML content for nurture emails"""

    templates = {
        1: f"""<div style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #333333;">
<p>Hoi {voornaam},</p>
<p>Gisteren stuurde ik je de geoptimaliseerde versie van je vacature voor <strong>{functie_titel}</strong>.</p>
<p>Even een snelle check: is alles goed aangekomen?</p>
<p>Als je vragen hebt over de analyse of tips - reply gerust op deze mail. Ik help je graag verder.</p>
<p>Groeten,<br><strong>Wouter</strong><br><span style="color: #666666;">kandidatentekort.nl</span></p>
<p style="color: #999999; font-size: 12px; margin-top: 30px; padding-top: 15px; border-top: 1px solid #eeeeee;">
PS: Geen verkooppraatje vandaag - gewoon even checken of alles werkt.</p>
</div>""",

        2: f"""<div style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #333333;">
<p>Hoi {voornaam},</p>
<p>Even nieuwsgierig: is het gelukt om de verbeterde vacaturetekst te plaatsen?</p>
<p>Ik hoor het graag als je ergens tegenaan loopt, bijvoorbeeld:</p>
<ul style="margin: 15px 0; padding-left: 20px;">
<li>Intern akkoord nodig voor de nieuwe tekst?</li>
<li>Technische problemen met het platform?</li>
<li>Twijfels over bepaalde aanpassingen?</li>
</ul>
<p>Geen probleem - reply gewoon en ik denk met je mee.</p>
<p>Groeten,<br><strong>Wouter</strong></p>
<p style="color: #999999; font-size: 12px; margin-top: 30px; padding-top: 15px; border-top: 1px solid #eeeeee;">
Tip: De meeste recruiters zien binnen 48 uur na plaatsing al verschil in response.</p>
</div>""",

        3: f"""<div style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #333333;">
<p>Hoi {voornaam},</p>
<p>Het is nu een paar dagen geleden sinds je de verbeterde vacature voor <strong>{functie_titel}</strong> hebt ontvangen.</p>
<p>Ik ben oprecht benieuwd: merk je al verschil in de reacties?</p>
<div style="background-color: #f8f9fa; border-left: 4px solid #EF7D00; padding: 15px 20px; margin: 20px 0;">
<p style="margin: 0 0 10px 0;"><strong>Mag ik je iets vragen?</strong></p>
<p style="margin: 0;">Als je 2 minuten hebt, zou je me kunnen vertellen:</p>
<ol style="margin: 10px 0; padding-left: 20px;">
<li>Heb je de nieuwe tekst al live gezet?</li>
<li>Zo ja, zie je verschil in aantal/kwaliteit reacties?</li>
<li>Wat vond je het meest nuttig aan de analyse?</li>
</ol>
<p style="margin: 0; font-size: 13px; color: #666;">Jouw feedback helpt me om de service te verbeteren.</p>
</div>
<p>Reply gewoon op deze mail - ik lees alles persoonlijk.</p>
<p>Alvast bedankt,<br><strong>Wouter</strong></p>
</div>""",

        4: f"""<div style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #333333;">
<p>Hoi {voornaam},</p>
<p>Deze week deel ik een tip die veel recruiters over het hoofd zien:</p>
<div style="background-color: #FEF3C7; border-left: 4px solid #F59E0B; padding: 15px 20px; margin: 20px 0;">
<p style="margin: 0 0 10px 0; font-size: 16px;"><strong>De functietitel bepaalt 70% van je zichtbaarheid</strong></p>
<p style="margin: 0 0 15px 0;">Kandidaten zoeken op specifieke termen. Een creatieve titel als "Teamspeler Extraordinaire" klinkt leuk, maar niemand zoekt daarop.</p>
<p style="margin: 0 0 10px 0;"><strong>Wat werkt:</strong></p>
<ul style="margin: 0 0 15px 0; padding-left: 20px;">
<li>Gebruik de exacte term die kandidaten googlen</li>
<li>Voeg niveau toe (Junior/Medior/Senior)</li>
<li>Houd het onder 60 karakters</li>
</ul>
<p style="margin: 0;"><strong>Voorbeeld:</strong><br>"Commerciele Binnendienst Medewerker" krijgt 3x meer views dan "Sales Ninja"</p>
</div>
<p>Heb je al gedacht aan het A/B testen van je functietitels?</p>
<p>Succes deze week,<br><strong>Wouter</strong></p>
</div>""",

        5: f"""<div style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #333333;">
<p>Hoi {voornaam},</p>
<p>"Salaris: marktconform" - de meest waardeloze zin in recruitment.</p>
<p>Hier is wat de data zegt:</p>
<div style="background-color: #D1FAE5; border-left: 4px solid #10B981; padding: 15px 20px; margin: 20px 0;">
<p style="margin: 0 0 10px 0;"><strong>Vacatures met salarisindicatie krijgen:</strong></p>
<ul style="margin: 0 0 10px 0; padding-left: 20px; list-style: none;">
<li>✅ +35% meer sollicitaties</li>
<li>✅ +27% hogere kwaliteit kandidaten</li>
<li>✅ +40% snellere time-to-hire</li>
</ul>
<p style="margin: 0; font-size: 12px; color: #666; font-style: italic;">Bron: Indeed Hiring Lab 2024</p>
</div>
<p><strong>Maar wat als je het niet mag vermelden?</strong></p>
<p>Alternatieven die ook werken:</p>
<ul style="margin: 15px 0; padding-left: 20px;">
<li>"Salarisindicatie: vanaf EUR 3.500 bruto/maand"</li>
<li>"Indicatie: schaal 8-10 CAO [naam]"</li>
<li>"Budget: EUR 45.000 - 55.000 op jaarbasis"</li>
</ul>
<p>Zelfs een range is beter dan niets.</p>
<p>Groeten,<br><strong>Wouter</strong></p>
</div>""",

        6: f"""<div style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #333333;">
<p>Hoi {voornaam},</p>
<p>Wist je dat kandidaten gemiddeld <strong>6 seconden</strong> besteden aan de eerste scan van een vacature?</p>
<p>In die 6 seconden beslissen ze of ze doorlezen of wegklikken.</p>
<div style="background-color: #EDE9FE; border-left: 4px solid #7C3AED; padding: 15px 20px; margin: 20px 0;">
<p style="margin: 0 0 10px 0;"><strong>Wat ze scannen:</strong></p>
<ol style="margin: 0 0 15px 0; padding-left: 20px;">
<li>Functietitel</li>
<li>Salaris (als het er staat)</li>
<li>De eerste 2-3 zinnen</li>
<li>Locatie</li>
<li>Logo/bedrijfsnaam</li>
</ol>
<p style="margin: 0 0 10px 0;"><strong>Het probleem:</strong> 90% begint met "Wij zoeken een enthousiaste..."</p>
<p style="margin: 0;"><strong>De oplossing:</strong> Start met een vraag of bold statement.</p>
</div>
<p>Pak eens een van je huidige vacatures erbij. Hoe is de opening?</p>
<p>Tot volgende week,<br><strong>Wouter</strong></p>
<p style="color: #999999; font-size: 12px; margin-top: 30px; padding-top: 15px; border-top: 1px solid #eeeeee;">
Dit was de laatste tip in deze serie. Vond je ze nuttig? Laat het me weten.</p>
</div>""",

        7: f"""<div style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #333333;">
<p>Hoi {voornaam},</p>
<p>Het is nu drie weken geleden dat je de vacature-analyse ontving.</p>
<p>Ik ben benieuwd hoe het gaat met je werving. Heb je de kandidaat al gevonden? Of loop je nog ergens tegenaan?</p>
<div style="background-color: #f8f9fa; border-left: 4px solid #EF7D00; padding: 15px 20px; margin: 20px 0;">
<p style="margin: 0 0 10px 0; font-size: 16px;"><strong>Zullen we even bellen?</strong></p>
<p style="margin: 0 0 15px 0;">Geen verkooppraatje, gewoon een kort gesprek (15 min) om te kijken of ik je ergens mee kan helpen.</p>
<p style="margin: 0 0 10px 0;"><strong>We kunnen het hebben over:</strong></p>
<ul style="margin: 0 0 15px 0; padding-left: 20px;">
<li>De resultaten van je huidige vacature</li>
<li>Andere openstaande posities</li>
<li>Recruitment uitdagingen waar je tegenaan loopt</li>
</ul>
<p style="margin: 0;">
<a href="https://calendly.com/wouter-arts-/vacature-analyse-advies" style="display: inline-block; background-color: #EF7D00; color: #ffffff; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">Plan een moment dat jou uitkomt</a>
</p>
</div>
<p>Geen zin of geen tijd? Reply dan gewoon even met een update.</p>
<p>Groeten,<br><strong>Wouter</strong></p>
</div>""",

        8: f"""<div style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #333333;">
<p>Hoi {voornaam},</p>
<p>Een maand geleden verstuurde ik de analyse voor je <strong>{functie_titel}</strong> vacature.</p>
<p>Dit is mijn laatste mail in deze serie - daarna laat ik je met rust.</p>
<p>Maar voor ik ga, ben ik nieuwsgierig:</p>
<div style="background-color: #f8f9fa; border: 1px solid #e0e0e0; padding: 15px 20px; margin: 20px 0; border-radius: 5px;">
<p style="margin: 0 0 10px 0;"><strong>Hoe is het gegaan?</strong></p>
<table style="width: 100%; border-collapse: collapse;">
<tr><td style="padding: 5px 0;"><strong>A.</strong> Kandidaat gevonden - top!</td></tr>
<tr><td style="padding: 5px 0;"><strong>B.</strong> Nog bezig - maar gaat goed</td></tr>
<tr><td style="padding: 5px 0;"><strong>C.</strong> Vacature on hold gezet</td></tr>
<tr><td style="padding: 5px 0;"><strong>D.</strong> Hulp nodig - laten we bellen</td></tr>
</table>
<p style="margin: 10px 0 0 0; font-size: 13px; color: #666;">Reply met A, B, C of D (of vertel gewoon je verhaal)</p>
</div>
<p>Hoe dan ook - succes met je recruitment!</p>
<p>Groeten,<br><strong>Wouter</strong><br><span style="color: #666666;">kandidatentekort.nl</span></p>
<p style="color: #999999; font-size: 12px; margin-top: 30px; padding-top: 15px; border-top: 1px solid #eeeeee;">
Contact: warts@recruitin.nl | Nieuwe vacature? <a href="https://kandidatentekort.nl" style="color: #EF7D00;">kandidatentekort.nl</a></p>
</div>"""
    }

    return templates.get(email_num, "")


def get_nurture_email_subject(email_num):
    """Get subject line for nurture email"""
    subjects = {
        1: "Even checken - alles goed ontvangen?",
        2: "Is het gelukt om de aanpassingen door te voeren?",
        3: "Benieuwd - merk je al verschil?",
        4: "Recruitment tip: De kracht van de juiste functietitel",
        5: "Recruitment tip: Het salarisvraagstuk",
        6: "Recruitment tip: De eerste 6 seconden",
        7: "Zullen we eens bellen?",
        8: "Laatste check - hoe staat het ervoor?"
    }
    return subjects.get(email_num, "Follow-up van kandidatentekort.nl")


def send_nurture_email(to_email, email_num, voornaam, functie_titel):
    """Send a nurture sequence email"""
    if not GMAIL_APP_PASSWORD:
        logger.warning("No Gmail password configured")
        return False

    try:
        subject = get_nurture_email_subject(email_num)
        html_content = get_nurture_email_html(email_num, voornaam, functie_titel)

        if not html_content:
            logger.error(f"No template for email {email_num}")
            return False

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"Wouter van kandidatentekort.nl <{GMAIL_USER}>"
        msg['To'] = to_email
        msg['Reply-To'] = "warts@recruitin.nl"

        msg.attach(MIMEText(html_content, 'html'))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)

        logger.info(f"✅ Sent nurture email {email_num} to {to_email}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to send nurture email: {e}")
        return False


def update_deal_nurture_status(deal_id, email_num):
    """Update deal fields after sending nurture email"""
    if not PIPEDRIVE_API_TOKEN:
        return False

    try:
        # Map email number to option ID (Pipedrive enum options)
        email_options = {
            1: "Email 1", 2: "Email 2", 3: "Email 3", 4: "Email 4",
            5: "Email 5", 6: "Email 6", 7: "Email 7", 8: "Email 8"
        }

        update_data = {
            FIELD_LAATSTE_EMAIL: email_options.get(email_num, "Email 1")
        }

        # If email 8, mark sequence as complete
        if email_num == 8:
            update_data[FIELD_EMAIL_SEQUENCE_STATUS] = "Completed"

        response = requests.put(
            f"{PIPEDRIVE_BASE}/deals/{deal_id}",
            params={"api_token": PIPEDRIVE_API_TOKEN},
            json=update_data,
            timeout=30
        )

        if response.status_code == 200:
            logger.info(f"✅ Updated deal {deal_id} nurture status to Email {email_num}")
            return True
        else:
            logger.warning(f"Failed to update deal: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"Error updating deal: {e}")
        return False


def get_deals_for_nurture():
    """Get all deals that need nurture emails today"""
    if not PIPEDRIVE_API_TOKEN:
        return []

    try:
        # Get all deals from pipeline
        response = requests.get(
            f"{PIPEDRIVE_BASE}/deals",
            params={
                "api_token": PIPEDRIVE_API_TOKEN,
                "pipeline_id": PIPELINE_ID,
                "status": "open",
                "limit": 500
            },
            timeout=30
        )

        if response.status_code != 200:
            logger.error(f"Failed to get deals: {response.status_code}")
            return []

        deals = response.json().get('data', []) or []
        deals_to_email = []
        today = datetime.now().date()

        for deal in deals:
            # Only process deals in Gekwalificeerd stage (21)
            stage_id = deal.get('stage_id')
            if stage_id != NURTURE_ACTIVE_STAGE:
                continue

            # Get custom field values
            rapport_date_str = deal.get(FIELD_RAPPORT_VERZONDEN)
            sequence_status = deal.get(FIELD_EMAIL_SEQUENCE_STATUS, '')
            laatste_email = deal.get(FIELD_LAATSTE_EMAIL, '')

            # Skip if no rapport date or sequence not active
            if not rapport_date_str:
                continue

            # Skip if sequence is completed, paused, or responded
            if sequence_status in ['Completed', 'Gepauzeerd', 'Voltooid', 'Responded', 'Unsubscribed']:
                continue

            # Parse rapport date
            try:
                rapport_date = datetime.strptime(rapport_date_str, '%Y-%m-%d').date()
            except:
                continue

            days_since_rapport = (today - rapport_date).days

            # Determine which email to send
            current_email = 0
            if laatste_email:
                try:
                    current_email = int(laatste_email.replace('Email ', ''))
                except:
                    pass

            next_email = current_email + 1

            # Check if it's time to send the next email
            if next_email <= 8:
                scheduled_day = EMAIL_SCHEDULE.get(next_email, {}).get('day', 999)
                if days_since_rapport >= scheduled_day:
                    # Get person info for email
                    person_id = deal.get('person_id', {})
                    if isinstance(person_id, dict):
                        person_id = person_id.get('value')

                    deals_to_email.append({
                        'deal_id': deal.get('id'),
                        'deal_title': deal.get('title', ''),
                        'person_id': person_id,
                        'next_email': next_email,
                        'days_since': days_since_rapport
                    })

        logger.info(f"📧 Found {len(deals_to_email)} deals in stage {NURTURE_ACTIVE_STAGE} (Gekwalificeerd) ready for nurture emails")
        return deals_to_email

    except Exception as e:
        logger.error(f"Error getting deals for nurture: {e}")
        return []


def get_person_email(person_id):
    """Get person's email and name from Pipedrive"""
    if not PIPEDRIVE_API_TOKEN or not person_id:
        return None, None

    try:
        response = requests.get(
            f"{PIPEDRIVE_BASE}/persons/{person_id}",
            params={"api_token": PIPEDRIVE_API_TOKEN},
            timeout=30
        )

        if response.status_code == 200:
            person = response.json().get('data', {})
            emails = person.get('email', [])
            email = emails[0].get('value') if emails else None
            name = person.get('first_name', 'daar')
            return email, name
    except Exception as e:
        logger.error(f"Error getting person: {e}")

    return None, None


def process_nurture_emails():
    """Process all pending nurture emails"""
    logger.info("🔄 Starting nurture email processing...")

    deals = get_deals_for_nurture()
    sent_count = 0

    for deal in deals:
        try:
            email, voornaam = get_person_email(deal['person_id'])

            if not email:
                logger.warning(f"No email for deal {deal['deal_id']}")
                continue

            # Extract functie from deal title
            functie_titel = deal['deal_title'].replace('Vacature Analyse - ', '').split(' - ')[0]

            # Send the email
            success = send_nurture_email(
                email,
                deal['next_email'],
                voornaam or 'daar',
                functie_titel
            )

            if success:
                # Update Pipedrive
                update_deal_nurture_status(deal['deal_id'], deal['next_email'])
                sent_count += 1

            # Small delay between emails
            time.sleep(2)

        except Exception as e:
            logger.error(f"Error processing deal {deal.get('deal_id')}: {e}")

    logger.info(f"✅ Nurture processing complete: {sent_count}/{len(deals)} emails sent")
    return sent_count


def start_nurture_deal(deal_id):
    """Start nurture sequence for a specific deal"""
    if not PIPEDRIVE_API_TOKEN:
        return False

    try:
        today = datetime.now().strftime('%Y-%m-%d')

        response = requests.put(
            f"{PIPEDRIVE_BASE}/deals/{deal_id}",
            params={"api_token": PIPEDRIVE_API_TOKEN},
            json={
                FIELD_RAPPORT_VERZONDEN: today,
                FIELD_EMAIL_SEQUENCE_STATUS: "Actief"
            },
            timeout=30
        )

        if response.status_code == 200:
            logger.info(f"✅ Started nurture sequence for deal {deal_id}")
            return True
        else:
            logger.warning(f"Failed to start nurture: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"Error starting nurture: {e}")
        return False


# Background scheduler for nurture emails
def nurture_scheduler():
    """Background thread that checks for nurture emails every hour"""
    while True:
        try:
            # Run at specific times (9 AM, 2 PM Dutch time)
            now = datetime.now()
            if now.hour in [9, 14]:
                logger.info("⏰ Scheduled nurture check running...")
                process_nurture_emails()
        except Exception as e:
            logger.error(f"Scheduler error: {e}")

        # Sleep for 1 hour
        time.sleep(3600)


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "version": "5.0",
        "features": ["typeform", "analysis", "nurture"],
        "email": bool(GMAIL_APP_PASSWORD),
        "pipedrive": bool(PIPEDRIVE_API_TOKEN),
        "claude": bool(ANTHROPIC_API_KEY)
    }), 200


@app.route("/nurture/process", methods=["POST"])
def trigger_nurture_processing():
    """Manually trigger nurture email processing"""
    count = process_nurture_emails()
    return jsonify({
        "success": True,
        "emails_sent": count
    }), 200


@app.route("/nurture/start/<int:deal_id>", methods=["POST"])
def start_nurture_for_deal(deal_id):
    """Start nurture sequence for a specific deal"""
    success = start_nurture_deal(deal_id)
    return jsonify({"success": success, "deal_id": deal_id}), 200 if success else 500


@app.route("/nurture/status", methods=["GET"])
def nurture_status():
    """Get status of nurture sequences"""
    deals = get_deals_for_nurture()
    return jsonify({
        "pending_emails": len(deals),
        "deals": deals[:20]  # Limit response
    }), 200


@app.route("/nurture/test/<int:email_num>", methods=["GET"])
def test_nurture_email(email_num):
    """Send a test nurture email"""
    to = request.args.get('to', 'warts@recruitin.nl')
    voornaam = request.args.get('name', 'Test')
    functie = request.args.get('functie', 'Senior Developer')

    success = send_nurture_email(to, email_num, voornaam, functie)
    return jsonify({
        "success": success,
        "email_num": email_num,
        "to": to
    }), 200 if success else 500


if __name__ == "__main__":
    # Start background scheduler for nurture emails
    scheduler_thread = threading.Thread(target=nurture_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("🚀 Nurture scheduler started")

    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
