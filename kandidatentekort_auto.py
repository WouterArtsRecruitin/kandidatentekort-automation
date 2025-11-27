#!/usr/bin/env python3
"""
KANDIDATENTEKORT.NL - WEBHOOK AUTOMATION V4.0
Deploy: Render.com | Updated: 2025-11-27
- V2: Pipedrive organization, person, deal creation
- V3: Claude AI vacancy analysis + report email
- V3.1: Professional report template with Before/After comparison
- V3.2: PDF, DOCX and Word file extraction for vacancy analysis
- V3.3: Fixed Typeform file download with authentication
- V4.0: ULTIMATE email template - Score visualization, Category breakdown,
        Before/After comparison, Full improved text, Numbered checklist, Bonus tips
"""

import os
import io
import json
import logging
import smtplib
import requests
from datetime import datetime
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
    Generate the ULTIMATE professional analysis report email HTML V4.0
    Features: Score visualization, Before/After, Checklist, Improved text, Tips
    """
    score = analysis.get('overall_score', 'N/A')
    score_section = analysis.get('score_section', '')
    improvements = analysis.get('top_3_improvements', [])
    improved_text = analysis.get('improved_text', '')
    bonus_tips = analysis.get('bonus_tips', [])

    # Generate HTML for improvements (numbered)
    improvements_html = ''.join([
        f'''<tr><td style="padding:12px 0;border-bottom:1px solid rgba(245,158,11,0.2);">
        <table cellpadding="0" cellspacing="0"><tr>
        <td style="width:32px;height:32px;background:linear-gradient(135deg,#F59E0B,#FBBF24);border-radius:50%;text-align:center;line-height:32px;font-weight:700;color:white;font-size:14px;">{i+1}</td>
        <td style="padding-left:15px;color:#78350F;font-size:14px;line-height:1.6;">{imp}</td>
        </tr></table></td></tr>''' for i, imp in enumerate(improvements)
    ])

    # Generate HTML for bonus tips (with icons)
    tips_html = ''.join([
        f'''<div style="display:flex;align-items:flex-start;margin-bottom:12px;padding:12px;background:white;border-radius:8px;">
        <span style="margin-right:12px;font-size:18px;">💡</span>
        <span style="color:#4C1D95;font-size:14px;line-height:1.6;">{tip}</span>
        </div>''' for tip in bonus_tips
    ])

    # Truncate original text for before/after display
    original_display = original_text[:600] + '...' if len(original_text) > 600 else original_text
    improved_preview = improved_text[:600] + '...' if len(improved_text) > 600 else improved_text

    # Calculate score color and label based on score
    if isinstance(score, (int, float)):
        score_num = float(score)
        if score_num >= 8.0:
            score_color = "#10B981"  # Green
            score_bg = "#ECFDF5"
            score_label = "Uitstekend"
            score_emoji = "🏆"
        elif score_num >= 6.5:
            score_color = "#3B82F6"  # Blue
            score_bg = "#EFF6FF"
            score_label = "Goed"
            score_emoji = "👍"
        elif score_num >= 5.0:
            score_color = "#F59E0B"  # Amber
            score_bg = "#FFFBEB"
            score_label = "Kan beter"
            score_emoji = "📈"
        else:
            score_color = "#EF4444"  # Red
            score_bg = "#FEF2F2"
            score_label = "Verbetering nodig"
            score_emoji = "⚠️"
        score_degrees = score_num * 36
    else:
        score_color = "#6B7280"
        score_bg = "#F9FAFB"
        score_label = "Beoordeeld"
        score_emoji = "📊"
        score_degrees = 180

    # Parse score_section into categories if available
    categories_html = ""
    if score_section:
        # Try to extract individual scores from score_section
        import re
        score_parts = re.findall(r'([A-Za-z-]+):\s*(\d+)/10', score_section)
        if score_parts:
            categories_html = '<table width="100%" cellpadding="0" cellspacing="0" style="margin-top:20px;"><tr>'
            for name, cat_score in score_parts[:4]:  # Max 4 categories
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
                categories_html += f'''<td width="25%" style="text-align:center;padding:10px;">
                <div style="font-size:24px;margin-bottom:4px;">{cat_icon}</div>
                <div style="font-size:24px;font-weight:800;color:{cat_color};">{cat_score}</div>
                <div style="font-size:11px;color:#6B7280;text-transform:uppercase;letter-spacing:0.5px;">{name}</div>
                </td>'''
            categories_html += '</tr></table>'

    return f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f3f4f6;">

<!-- EMAIL WRAPPER -->
<table width="100%" cellpadding="0" cellspacing="0" style="padding:30px 15px;"><tr><td align="center">
<table width="680" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:24px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.15);overflow:hidden;">

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<!-- HEADER SECTION -->
<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<tr><td style="background:linear-gradient(135deg,#1E3A8A 0%,#3B82F6 50%,#1E3A8A 100%);padding:45px 40px;position:relative;">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td>
<!-- Logo & Brand -->
<table cellpadding="0" cellspacing="0"><tr>
<td style="width:56px;height:56px;background:linear-gradient(135deg,#FF6B35 0%,#FF8F65 100%);border-radius:14px;text-align:center;line-height:56px;box-shadow:0 8px 25px rgba(255,107,53,0.4);">
<span style="font-size:26px;font-weight:800;color:white;">R</span>
</td>
<td style="padding-left:16px;vertical-align:middle;">
<div style="color:white;font-size:20px;font-weight:700;letter-spacing:-0.5px;">RECRUITIN</div>
<div style="color:rgba(255,255,255,0.85);font-size:12px;font-weight:500;">Vacature Intelligence Platform</div>
</td>
</tr></table>
</td></tr>
<tr><td style="padding-top:35px;">
<div style="color:white;font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:1.5px;opacity:0.9;margin-bottom:8px;">AI-POWERED ANALYSE</div>
<div style="color:white;font-size:32px;font-weight:800;letter-spacing:-1px;line-height:1.2;">📊 Vacature Analyse Rapport</div>
<div style="color:rgba(255,255,255,0.9);font-size:15px;margin-top:10px;">Gepersonaliseerd voor <strong>{bedrijf}</strong></div>
</td></tr>
</table>
</td></tr>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<!-- SCORE HERO SECTION -->
<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<tr><td style="padding:50px 40px;text-align:center;background:linear-gradient(180deg,#f8fafc 0%,#ffffff 100%);">
<!-- Score Circle -->
<div style="display:inline-block;position:relative;margin-bottom:25px;">
<div style="width:180px;height:180px;border-radius:50%;background:conic-gradient({score_color} 0deg {score_degrees}deg,#E5E7EB {score_degrees}deg 360deg);padding:12px;display:inline-block;">
<div style="width:100%;height:100%;background:white;border-radius:50%;display:flex;flex-direction:column;align-items:center;justify-content:center;box-shadow:inset 0 2px 10px rgba(0,0,0,0.05);">
<div style="font-size:52px;font-weight:800;color:{score_color};line-height:1;">{score}</div>
<div style="font-size:16px;color:#9CA3AF;font-weight:500;margin-top:2px;">/10</div>
</div>
</div>
</div>
<!-- Score Label -->
<div style="margin-bottom:8px;">
<span style="display:inline-block;background:{score_bg};color:{score_color};padding:8px 20px;border-radius:25px;font-size:14px;font-weight:700;border:2px solid {score_color};">
{score_emoji} {score_label}
</span>
</div>
<!-- Score Breakdown -->
<div style="color:#6B7280;font-size:13px;max-width:450px;margin:15px auto 0;line-height:1.6;">{score_section}</div>
{categories_html}
</td></tr>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<!-- INTRO & GREETING -->
<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<tr><td style="padding:0 40px 35px;">
<div style="border-left:4px solid #FF6B35;padding-left:20px;">
<p style="font-size:20px;font-weight:700;color:#1F2937;margin:0 0 12px 0;">Hoi {voornaam}! 👋</p>
<p style="color:#4B5563;line-height:1.7;margin:0;font-size:15px;">Bedankt voor het uploaden van je vacature via <strong style="color:#FF6B35;">kandidatentekort.nl</strong>. Onze AI heeft je tekst grondig geanalyseerd op 6 belangrijke criteria. Hieronder vind je de complete resultaten met concrete verbeteringen.</p>
</div>
</td></tr>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<!-- TOP 3 VERBETERPUNTEN (CHECKLIST STYLE) -->
<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<tr><td style="padding:0 40px 35px;">
<div style="background:linear-gradient(135deg,#FFFBEB 0%,#FEF3C7 100%);border-radius:20px;padding:30px;border:2px solid #F59E0B;box-shadow:0 4px 15px rgba(245,158,11,0.15);">
<!-- Section Header -->
<table cellpadding="0" cellspacing="0" style="margin-bottom:20px;"><tr>
<td style="width:48px;height:48px;background:linear-gradient(135deg,#F59E0B 0%,#FBBF24 100%);border-radius:14px;text-align:center;line-height:48px;box-shadow:0 4px 12px rgba(245,158,11,0.3);">
<span style="font-size:22px;">🎯</span>
</td>
<td style="padding-left:16px;">
<div style="font-size:11px;font-weight:600;color:#B45309;text-transform:uppercase;letter-spacing:1px;">Prioriteit</div>
<div style="font-size:20px;font-weight:700;color:#92400E;">Top 3 Verbeterpunten</div>
</td>
</tr></table>
<!-- Improvements List -->
<table width="100%" cellpadding="0" cellspacing="0">{improvements_html}</table>
</div>
</td></tr>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<!-- BEFORE / AFTER COMPARISON -->
<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<tr><td style="padding:0 40px 35px;">
<div style="text-align:center;margin-bottom:25px;">
<div style="font-size:11px;font-weight:600;color:#6B7280;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:6px;">Vergelijking</div>
<div style="font-size:22px;font-weight:700;color:#1F2937;">📝 Voor & Na Optimalisatie</div>
</div>
<table width="100%" cellpadding="0" cellspacing="0"><tr>
<!-- BEFORE Column -->
<td width="48%" style="vertical-align:top;">
<div style="background:#FEF2F2;border-radius:16px;padding:20px;border:2px solid #FECACA;height:100%;">
<div style="display:flex;align-items:center;margin-bottom:15px;">
<span style="display:inline-block;background:#EF4444;color:white;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;">❌ Origineel</span>
</div>
<div style="background:white;padding:16px;border-radius:10px;font-size:13px;color:#6B7280;line-height:1.7;max-height:220px;overflow:hidden;border:1px solid #FECACA;">{original_display}</div>
</div>
</td>
<td width="4%"></td>
<!-- AFTER Column -->
<td width="48%" style="vertical-align:top;">
<div style="background:#ECFDF5;border-radius:16px;padding:20px;border:2px solid #A7F3D0;height:100%;">
<div style="display:flex;align-items:center;margin-bottom:15px;">
<span style="display:inline-block;background:#10B981;color:white;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;">✅ Geoptimaliseerd</span>
</div>
<div style="background:white;padding:16px;border-radius:10px;font-size:13px;color:#374151;line-height:1.7;max-height:220px;overflow:hidden;border:1px solid #A7F3D0;">{improved_preview}</div>
</div>
</td>
</tr></table>
</td></tr>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<!-- FULL IMPROVED VACANCY TEXT -->
<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<tr><td style="padding:0 40px 35px;">
<div style="background:linear-gradient(135deg,#ECFDF5 0%,#D1FAE5 100%);border-radius:20px;padding:30px;border:2px solid #10B981;box-shadow:0 4px 15px rgba(16,185,129,0.15);">
<!-- Section Header -->
<table cellpadding="0" cellspacing="0" style="margin-bottom:20px;"><tr>
<td style="width:48px;height:48px;background:linear-gradient(135deg,#10B981 0%,#34D399 100%);border-radius:14px;text-align:center;line-height:48px;box-shadow:0 4px 12px rgba(16,185,129,0.3);">
<span style="font-size:22px;">✍️</span>
</td>
<td style="padding-left:16px;">
<div style="font-size:11px;font-weight:600;color:#047857;text-transform:uppercase;letter-spacing:1px;">Direct te gebruiken</div>
<div style="font-size:20px;font-weight:700;color:#065F46;">Verbeterde Vacaturetekst</div>
</td>
</tr></table>
<!-- Full Text -->
<div style="background:white;padding:25px;border-radius:14px;font-size:14px;color:#374151;line-height:1.85;white-space:pre-wrap;border:1px solid #A7F3D0;box-shadow:inset 0 2px 4px rgba(0,0,0,0.02);">{improved_text}</div>
<div style="text-align:center;margin-top:20px;">
<span style="display:inline-block;background:white;color:#059669;padding:10px 20px;border-radius:8px;font-size:13px;font-weight:600;border:1px solid #A7F3D0;">💾 Kopieer deze tekst en plaats direct in je vacature</span>
</div>
</div>
</td></tr>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<!-- BONUS TIPS SECTION -->
<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<tr><td style="padding:0 40px 35px;">
<div style="background:linear-gradient(135deg,#F5F3FF 0%,#EDE9FE 100%);border-radius:20px;padding:30px;border:2px solid #8B5CF6;box-shadow:0 4px 15px rgba(139,92,246,0.15);">
<!-- Section Header -->
<table cellpadding="0" cellspacing="0" style="margin-bottom:20px;"><tr>
<td style="width:48px;height:48px;background:linear-gradient(135deg,#8B5CF6 0%,#A78BFA 100%);border-radius:14px;text-align:center;line-height:48px;box-shadow:0 4px 12px rgba(139,92,246,0.3);">
<span style="font-size:22px;">🚀</span>
</td>
<td style="padding-left:16px;">
<div style="font-size:11px;font-weight:600;color:#6D28D9;text-transform:uppercase;letter-spacing:1px;">Extra waarde</div>
<div style="font-size:20px;font-weight:700;color:#5B21B6;">Bonus Tips van de Expert</div>
</td>
</tr></table>
<!-- Tips -->
{tips_html}
</div>
</td></tr>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<!-- CTA SECTION -->
<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<tr><td style="padding:0 40px 45px;">
<div style="background:linear-gradient(135deg,#1E3A8A 0%,#3B82F6 100%);border-radius:20px;padding:40px;text-align:center;box-shadow:0 10px 30px rgba(30,58,138,0.3);">
<div style="font-size:24px;font-weight:800;color:white;margin-bottom:10px;letter-spacing:-0.5px;">Wil je nog meer resultaat?</div>
<p style="color:rgba(255,255,255,0.9);margin:0 0 30px 0;font-size:15px;line-height:1.6;">Plan een gratis adviesgesprek van 30 minuten.<br>Bespreek je vacature met een recruitment specialist.</p>
<table cellpadding="0" cellspacing="0" style="margin:0 auto;"><tr>
<td style="padding:0 8px;">
<a href="https://calendly.com/wouter-arts-/vacature-analyse-advies" style="display:inline-block;background:#10B981;color:white;padding:16px 28px;text-decoration:none;border-radius:12px;font-weight:700;font-size:15px;box-shadow:0 4px 15px rgba(16,185,129,0.4);transition:all 0.3s;">📅 Plan Adviesgesprek</a>
</td>
<td style="padding:0 8px;">
<a href="https://wa.me/31614314593?text=Hoi%20Wouter,%20ik%20heb%20mijn%20vacature-analyse%20ontvangen!" style="display:inline-block;background:#25D366;color:white;padding:16px 28px;text-decoration:none;border-radius:12px;font-weight:700;font-size:15px;box-shadow:0 4px 15px rgba(37,211,102,0.4);">💬 WhatsApp</a>
</td>
</tr></table>
</div>
</td></tr>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<!-- FOOTER -->
<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<tr><td style="background:#111827;padding:35px 40px;">
<table width="100%" cellpadding="0" cellspacing="0"><tr>
<td style="vertical-align:top;">
<div style="font-size:18px;font-weight:700;color:white;margin-bottom:4px;">Wouter Arts</div>
<div style="color:rgba(255,255,255,0.7);font-size:13px;margin-bottom:2px;">Founder & Recruitment Specialist</div>
<div style="color:#FF6B35;font-size:14px;font-weight:600;">Kandidatentekort.nl</div>
</td>
<td style="text-align:right;vertical-align:top;">
<div style="color:rgba(255,255,255,0.6);font-size:12px;line-height:1.8;">
📞 06-14314593<br>
📧 wouter@recruitin.nl<br>
🌐 kandidatentekort.nl
</div>
</td>
</tr></table>
<div style="border-top:1px solid rgba(255,255,255,0.1);margin-top:25px;padding-top:20px;text-align:center;">
<p style="margin:0;color:rgba(255,255,255,0.4);font-size:11px;">© 2025 Kandidatentekort.nl | Recruitin B.V. | Made with ❤️ in Nederland</p>
</div>
</td></tr>

</table></td></tr></table></body></html>'''


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


@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "version": "4.0",
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

        # Create Pipedrive records (organization first, then person, then deal)
        org_id = create_pipedrive_organization(p['bedrijf'])
        person_id = create_pipedrive_person(p['contact'], p['email'], p['telefoon'], org_id)
        deal_id = create_pipedrive_deal(
            f"Vacature Analyse - {p['functie']} - {p['bedrijf']}",
            person_id,
            org_id,
            vacancy_text,  # Use extracted text if available
            p['file_url'],
            analysis_summary
        )

        logger.info(f"✅ Done: confirmation={confirmation_sent}, analysis={analysis_sent}, org={org_id}, person={person_id}, deal={deal_id}")

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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
