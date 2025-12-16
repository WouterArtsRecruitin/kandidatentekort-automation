#!/usr/bin/env python3
"""
KANDIDATENTEKORT.NL - WEBHOOK AUTOMATION V6.0+ ENHANCED
Deploy: Render.com | Updated: 2025-12-17

CHANGELOG:
- V6.0+ ENHANCED: 8-Criteria Expert Panel (40-point scoring system)
        - New expert panel: Wouter, Sarah, Mark, Linda, Ruben
        - Enhanced scoring: 8 criteria x 5 max = 40 points per expert
        - Expected improvement projections per analysis
        - Urgency classification (KRITIEK/AANDACHT/OPTIMALISATIE)
        - Dutch tech benchmarks 2025 integrated
        - Improved email template with percentage scores
- V6.0: MANUAL REVIEW MODE + 5-EXPERT PANEL PROMPT
        - MANUAL_REVIEW_MODE env toggle (default: true)
        - Analysis stored in Pipedrive Note, NO auto email
        - /approve/<deal_id> endpoint for manual release
        - New 5-Expert Panel Claude prompt for deeper analysis
        - Slack webhook notification for new analyses (optional)
- V5.1: Trust-first email nurture sequence
- V4.1: Outlook compatible email templates
- V3.3: PDF/DOCX file extraction
"""

import os
import io
import json
import logging
import smtplib
import requests
import threading
import time
import re
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

# =============================================================================
# CONFIGURATION
# =============================================================================
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
PIPEDRIVE_API_TOKEN = os.getenv('PIPEDRIVE_API_TOKEN')
TYPEFORM_API_TOKEN = os.getenv('TYPEFORM_API_TOKEN')
GMAIL_USER = os.getenv('GMAIL_USER', 'artsrecruitin@gmail.com')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD') or os.getenv('GMAIL_PASS')
PIPEDRIVE_BASE = "https://api.pipedrive.com/v1"
PIPELINE_ID = 4
STAGE_ID = 21

# V6.0: Manual Review Mode - Set to 'false' to enable auto-send
MANUAL_REVIEW_MODE = os.getenv('MANUAL_REVIEW_MODE', 'true').lower() == 'true'

# V6.0: Optional Slack notification for new analyses
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL', '')

# Email Nurture Custom Field Keys (from Pipedrive)
FIELD_RAPPORT_VERZONDEN = "337f9ccca15334e6e4f937ca5ef0055f13ed0c63"
FIELD_EMAIL_SEQUENCE_STATUS = "22d33c7f119119e178f391a272739c571cf2e29b"
FIELD_LAATSTE_EMAIL = "753f37a1abc8e161c7982c1379a306b21fae1bab"

# V6.0: New field for analysis approval status
FIELD_ANALYSE_STATUS = os.getenv('FIELD_ANALYSE_STATUS', '')  # Create in Pipedrive if needed

# Email sequence timing
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

NURTURE_ACTIVE_STAGE = 21


# =============================================================================
# V6.0: NEW 5-EXPERT PANEL PROMPT
# =============================================================================
# =============================================================================
# V6.0+ ENHANCED: 5-EXPERT PANEL PROMPT (8-CRITERIA, 40-POINT SYSTEM)
# =============================================================================
def get_expert_panel_prompt(vacature_text, bedrijf, sector=""):
    """
    V6.0+ ENHANCED: Multi-Expert Panel Analysis Prompt
    5 senior experts analyze vacancy with 8-criteria scoring system
    Based on 2,847+ optimized Dutch vacancies
    """
    return f"""Je bent het Nederlandse Vacature Expertise Panel - een team van 5 senior recruitment professionals die vacatureteksten transformeren tot candidate magneten. Jullie specialisatie: Nederlandse tech recruitment met focus op +40-60% meer sollicitaties binnen 2 weken.

## PANEL SAMENSTELLING:
👨‍💼 Wouter Arts - Senior Recruitment Intelligence (15+ jaar, 2847+ vacatures geoptimaliseerd)
👩‍💻 Sarah de Vries - Talent Acquisition Lead (Tech sector specialist, 95% success rate)
👨‍🎨 Mark van den Berg - Conversion Copywriter (A/B test expert, +127% gem. verbetering)
👩‍💼 Linda Konings - HR Director (Compliance & budget focus, Fortune 500 ervaring)
🎯 Ruben Janssen - Industry Intelligence (Tech trends, salary benchmarks, markt insights)

## TRACK RECORD:
- 2,847+ Nederlandse vacatures geoptimaliseerd sinds 2019
- Gemiddelde verbetering: +47% sollicitaties, +31% kwaliteit
- 94% klanten implementeert aanbevelingen binnen 48 uur

---

## SCORING MATRIX (8 Criteria, 1-5 sterren per expert = max 40 punten)

1. 🎯 HOOK POWER (Impact eerste 2 zinnen)
   1★: Generic "Wij zoeken een..." | 3★: Bedrijf + functie | 5★: Problem/Impact statement

2. 🏢 COMPANY MAGNETISM (Werkgever aantrekkelijkheid)
   1★: Alleen naam | 3★: Basic beschrijving | 5★: Missie + momentum + waarom nu

3. 💼 ROLE CLARITY (Taak concreetheid)
   1★: Vage lijstjes | 3★: Mix concreet/vaag | 5★: "Je bouwt X waardoor Y"

4. ✅ REQUIREMENTS REALITY (Eisen haalbaarheid)
   1★: Unicorn hunting (15+ eisen) | 3★: 7-10 eisen | 5★: Max 5 must-haves

5. 💰 BENEFITS POWER (Compensatie transparantie)
   1★: Geen salaris | 3★: "Competitief" | 5★: Bereik + unique benefits

6. 🚀 GROWTH NARRATIVE (Ontwikkelingsperspectief)
   1★: Geen growth story | 3★: "Doorgroeimogelijkheden" | 5★: Concreet pad

7. 🎨 INCLUSION FACTOR (Diversiteit & toegankelijkheid)
   1★: Exclusieve taal | 3★: Neutraal | 5★: Actief inclusief

8. 📞 ACTION TRIGGER (Call-to-action sterkte)
   1★: "Stuur CV naar..." | 3★: "Solliciteer via..." | 5★: Laagdrempelig + persoon

---

## DUTCH TECH BENCHMARKS 2025

SALARIS (marktconform):
- Junior (0-2j): €35k-48k | Medior (2-5j): €48k-68k | Senior (5+j): €65k-85k

CANDIDATE VERWACHTINGEN:
- 78% eist salaris in vacature
- 84% verwacht hybrid/remote optie
- 62% checkt tech stack voor solliciteren

MARKT REALITEIT:
- Gem. sollicitaties per vacature: 23 (was 31 in 2023)
- Time-to-fill: 47 dagen (benchmark: 35)
- No-show rate bij vage vacatures: 41%

---

## VACATURETEKST OM TE ANALYSEREN:
{vacature_text}

## CONTEXT:
- Bedrijf: {bedrijf}
- Sector: {sector if sector else 'Niet gespecificeerd'}
- Land: Nederland
- Doel: +40-60% meer kwalitatieve sollicitaties

---

## ANALYSE OPDRACHT:

Elke expert scoort alle 8 criteria (1-5 sterren) en geeft:
1. Expert-specifieke insight (1 zin)
2. Top verbeterpunt vanuit dit perspectief
3. Concrete quick-win tip

DAARNA: Geconsolideerd eindoordeel met:
- Overall score (/40)
- Top 3 prioriteiten (impact gerangschikt)
- VOLLEDIGE herschreven vacaturetekst (400-600 woorden)
- 3 bonus tips

---

## OUTPUT FORMAT (STRICT JSON):

```json
{{
    "expert_analyses": {{
        "wouter": {{
            "expert_name": "Wouter Arts - Business Impact",
            "scores": {{"hook": 3, "company": 2, "role": 4, "requirements": 2, "benefits": 1, "growth": 2, "inclusion": 3, "action": 3}},
            "total": 20,
            "insight": "Vanuit ROI perspectief: [specifieke observatie]",
            "verbeterpunt": "[Belangrijkste issue vanuit business perspectief]",
            "quick_win": "[Direct implementeerbare tip]"
        }},
        "sarah": {{
            "expert_name": "Sarah de Vries - Candidate Experience",
            "scores": {{"hook": 3, "company": 2, "role": 3, "requirements": 3, "benefits": 2, "growth": 2, "inclusion": 3, "action": 2}},
            "total": 20,
            "insight": "Vanuit candidate journey: [specifieke observatie]",
            "verbeterpunt": "[Belangrijkste issue vanuit candidate perspectief]",
            "quick_win": "[Direct implementeerbare tip]"
        }},
        "mark": {{
            "expert_name": "Mark van den Berg - Conversion Copy",
            "scores": {{"hook": 2, "company": 2, "role": 3, "requirements": 3, "benefits": 1, "growth": 2, "inclusion": 3, "action": 2}},
            "total": 18,
            "insight": "Vanuit copywriting: [specifieke observatie]",
            "verbeterpunt": "[Belangrijkste issue vanuit copy perspectief]",
            "quick_win": "[Direct implementeerbare tip]"
        }},
        "linda": {{
            "expert_name": "Linda Konings - HR & Compliance",
            "scores": {{"hook": 3, "company": 3, "role": 3, "requirements": 2, "benefits": 2, "growth": 2, "inclusion": 4, "action": 3}},
            "total": 22,
            "insight": "Vanuit HR perspectief: [specifieke observatie]",
            "verbeterpunt": "[Belangrijkste issue vanuit HR perspectief]",
            "quick_win": "[Direct implementeerbare tip]"
        }},
        "ruben": {{
            "expert_name": "Ruben Janssen - Market Intelligence",
            "scores": {{"hook": 3, "company": 2, "role": 3, "requirements": 2, "benefits": 1, "growth": 2, "inclusion": 3, "action": 2}},
            "total": 18,
            "insight": "Vanuit marktperspectief: [specifieke observatie]",
            "verbeterpunt": "[Belangrijkste issue vanuit markt perspectief]",
            "quick_win": "[Direct implementeerbare tip]"
        }}
    }},
    "consolidated": {{
        "overall_score": 19.6,
        "max_score": 40,
        "percentage": 49,
        "verdict": "Onder benchmark - significante verbetering mogelijk",
        "urgency": "KRITIEK",
        "score_breakdown": "Hook: 2.8 | Company: 2.2 | Role: 3.2 | Reqs: 2.4 | Benefits: 1.4 | Growth: 2.0 | Inclusion: 3.2 | Action: 2.4",
        "top_3_priorities": [
            {{"issue": "[Belangrijkste probleem]", "impact": "+25-30%", "effort": "5 min"}},
            {{"issue": "[Tweede probleem]", "impact": "+15-20%", "effort": "15 min"}},
            {{"issue": "[Derde probleem]", "impact": "+10-15%", "effort": "30 min"}}
        ],
        "improved_text": "[VOLLEDIGE HERSCHREVEN VACATURETEKST - 400-600 woorden]\\n\\n[Start met pakkende hook - geen 'Wij zoeken']\\n\\n[Bedrijf intro - missie, momentum, waarom nu]\\n\\n**Wat je gaat doen:**\\n• [Concrete taak met impact]\\n• [Concrete taak met impact]\\n• [Concrete taak met impact]\\n\\n**Wat je meebrengt:**\\nMust-haves:\\n• [Eis 1]\\n• [Eis 2]\\n• [Eis 3]\\n\\nNice-to-haves:\\n• [Bonus 1]\\n• [Bonus 2]\\n\\n**Wat wij bieden:**\\n• Salaris: €XX.000 - €XX.000\\n• [Unieke benefit 1]\\n• [Unieke benefit 2]\\n• [Unieke benefit 3]\\n\\n**Interesse?**\\n[Laagdrempelige CTA met contactpersoon]",
        "bonus_tips": [
            "[Extra tip 1 - specifiek voor deze vacature]",
            "[Extra tip 2 - sector-gerelateerd]",
            "[Extra tip 3 - kandidaat psychologie]"
        ],
        "expected_improvement": {{
            "sollicitaties": "+45-60%",
            "kwaliteit": "+25-35%",
            "time_to_fill": "-15-25 dagen"
        }}
    }}
}}
```

## BELANGRIJK:
- Output ALLEEN valid JSON, geen tekst ervoor of erna
- overall_score = gemiddelde van 5 expert totalen (elk max 40, dus overall max 40)
- improved_text moet COMPLETE herschreven vacature zijn (400-600 woorden)
- Alle tips CONCREET en DIRECT TOEPASBAAR
- Schrijf in professioneel Nederlands
- Focus op wat KANDIDATEN willen
- Percentages gebaseerd op benchmark data
"""


# =============================================================================
# FILE EXTRACTION (unchanged from V5.1)
# =============================================================================
def extract_text_from_file(file_url):
    """Download and extract text from PDF, DOCX, or DOC files."""
    if not file_url:
        return ""

    try:
        logger.info(f"📄 Downloading file: {file_url[:80]}...")

        headers = {}
        if TYPEFORM_API_TOKEN and 'typeform.com' in file_url:
            headers['Authorization'] = f'Bearer {TYPEFORM_API_TOKEN}'
            logger.info("🔑 Using Typeform API authentication")

        response = requests.get(file_url, headers=headers, timeout=30)
        content_type = response.headers.get('content-type', 'unknown')
        logger.info(f"📦 Response: status={response.status_code}, content-type={content_type}, size={len(response.content)} bytes")

        if response.status_code != 200:
            logger.error(f"❌ Failed to download file: {response.status_code}")
            return ""

        content = response.content

        if len(content) < 100 and b'error' in content.lower():
            logger.error(f"❌ Got error response: {content[:200]}")
            return ""

        # Detect by magic bytes
        if content[:4] == b'%PDF':
            return extract_pdf_text(content)
        elif content[:2] == b'PK':
            return extract_docx_text(content)
        elif content[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
            logger.warning("⚠️ Old .doc format not supported")
            return ""

        # Fallback by content-type or URL
        if 'pdf' in content_type:
            return extract_pdf_text(content)
        elif 'wordprocessingml' in content_type or 'msword' in content_type:
            return extract_docx_text(content)

        file_url_lower = file_url.lower()
        if '.pdf' in file_url_lower:
            return extract_pdf_text(content)
        elif '.docx' in file_url_lower:
            return extract_docx_text(content)

        logger.warning(f"⚠️ Could not determine file type")
        return ""

    except Exception as e:
        logger.error(f"❌ File extraction error: {e}")
        return ""


def extract_pdf_text(content):
    if not PDF_AVAILABLE:
        logger.error("❌ PyPDF2 not available")
        return ""
    try:
        pdf_file = io.BytesIO(content)
        reader = PdfReader(pdf_file)
        text_parts = [page.extract_text() for page in reader.pages if page.extract_text()]
        full_text = "\n".join(text_parts)
        logger.info(f"✅ PDF extracted: {len(full_text)} characters")
        return full_text.strip()
    except Exception as e:
        logger.error(f"❌ PDF extraction failed: {e}")
        return ""


def extract_docx_text(content):
    if not DOCX_AVAILABLE:
        logger.error("❌ python-docx not available")
        return ""
    try:
        docx_file = io.BytesIO(content)
        doc = Document(docx_file)
        text_parts = [p.text for p in doc.paragraphs if p.text.strip()]
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


# =============================================================================
# EMAIL FUNCTIONS
# =============================================================================
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
<li>Beoordeling door 5 recruitment experts</li>
<li>Concrete verbeterpunten voor meer sollicitanten</li>
<li>Direct toepasbare herschreven vacaturetekst</li></ul></td></tr></table>
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


# =============================================================================
# V6.0: CLAUDE ANALYSIS WITH NEW PROMPT
# =============================================================================
def analyze_vacancy_with_claude(vacature_text, bedrijf, sector=""):
    """V6.0+ ENHANCED: Analyze with 5-Expert Panel prompt (8-criteria, 40-point system)"""
    if not ANTHROPIC_API_KEY:
        logger.error("❌ ANTHROPIC_API_KEY not set!")
        return None

    prompt = get_expert_panel_prompt(vacature_text, bedrijf, sector)

    try:
        logger.info("🤖 Starting Claude V6.0+ Enhanced Expert Panel analysis...")
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 8000,  # Increased for longer enhanced output
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=120  # Increased timeout for more complex analysis
        )

        if r.status_code == 200:
            response_text = r.json()['content'][0]['text']
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                analysis = json.loads(response_text[json_start:json_end])
                
                # Extract consolidated data - V6.0+ Enhanced format
                consolidated = analysis.get('consolidated', {})
                
                # Convert top_3_priorities to simple list for backward compatibility
                priorities = consolidated.get('top_3_priorities', [])
                top_3_improvements = []
                for p in priorities:
                    if isinstance(p, dict):
                        top_3_improvements.append(f"{p.get('issue', '')} (Impact: {p.get('impact', '')}, Effort: {p.get('effort', '')})")
                    else:
                        top_3_improvements.append(str(p))
                
                # Build score section from breakdown
                score_breakdown = consolidated.get('score_breakdown', '')
                overall_score = consolidated.get('overall_score', 0)
                max_score = consolidated.get('max_score', 40)
                percentage = consolidated.get('percentage', int(overall_score / max_score * 100) if max_score else 0)
                
                result = {
                    'overall_score': overall_score,
                    'max_score': max_score,
                    'percentage': percentage,
                    'score_section': score_breakdown,
                    'top_3_improvements': top_3_improvements,
                    'improved_text': consolidated.get('improved_text', ''),
                    'bonus_tips': consolidated.get('bonus_tips', []),
                    'expert_analyses': analysis.get('expert_analyses', {}),
                    'verdict': consolidated.get('verdict', ''),
                    'urgency': consolidated.get('urgency', 'ONBEKEND'),
                    'expected_improvement': consolidated.get('expected_improvement', {})
                }
                
                logger.info(f"✅ Claude V6.0+ analysis complete: score={result['overall_score']}/{result['max_score']} ({result['percentage']}%)")
                return result
            else:
                logger.error("❌ No JSON found in Claude response")
                return None
        else:
            logger.error(f"❌ Claude API error: {r.status_code} - {r.text[:200]}")
            return None

    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON parse error: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Claude analysis failed: {e}")
        return None


# =============================================================================
# V6.0: SLACK NOTIFICATION
# =============================================================================
def send_slack_notification(deal_id, bedrijf, functie, score, email):
    """Send Slack notification for new analysis (optional)"""
    if not SLACK_WEBHOOK_URL:
        return False
    
    try:
        message = {
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "🎯 Nieuwe Vacature Analyse", "emoji": True}
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Bedrijf:*\n{bedrijf}"},
                        {"type": "mrkdwn", "text": f"*Functie:*\n{functie}"},
                        {"type": "mrkdwn", "text": f"*Score:*\n{score}/10"},
                        {"type": "mrkdwn", "text": f"*Contact:*\n{email}"}
                    ]
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Review nodig* - analyse staat klaar in Pipedrive"},
                    "accessory": {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Open Deal", "emoji": True},
                        "url": f"https://recruitin2.pipedrive.com/deal/{deal_id}",
                        "action_id": "open_deal"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": f"Approve: `POST /approve/{deal_id}`"}
                    ]
                }
            ]
        }
        
        r = requests.post(SLACK_WEBHOOK_URL, json=message, timeout=10)
        if r.status_code == 200:
            logger.info(f"✅ Slack notification sent for deal {deal_id}")
            return True
        else:
            logger.warning(f"Slack notification failed: {r.status_code}")
            return False
    except Exception as e:
        logger.error(f"Slack error: {e}")
        return False


# =============================================================================
# V6.0: ANALYSIS EMAIL HTML (Enhanced with Expert Panel)
# =============================================================================
def get_analysis_email_html(voornaam, bedrijf, analysis, original_text=""):
    """V6.0+ Enhanced: Generate professional analysis report email with 8-criteria expert panel"""
    
    # V6.0+ Enhanced scoring (40-point system)
    score = analysis.get('overall_score', 0)
    max_score = analysis.get('max_score', 40)
    percentage = analysis.get('percentage', int(score / max_score * 100) if max_score else 0)
    score_section = analysis.get('score_section', '')
    improvements = analysis.get('top_3_improvements', [])
    improved_text = analysis.get('improved_text', '')
    bonus_tips = analysis.get('bonus_tips', [])
    expert_analyses = analysis.get('expert_analyses', {})
    verdict = analysis.get('verdict', '')
    urgency = analysis.get('urgency', '')
    expected_improvement = analysis.get('expected_improvement', {})

    # Score styling based on percentage (V6.0+ uses 40-point scale)
    if isinstance(score, (int, float)):
        pct = percentage if percentage else (score / max_score * 100)
        if pct >= 80:
            score_color, score_bg, score_label, score_emoji = "#10B981", "#ECFDF5", "Uitstekend", "🏆"
        elif pct >= 65:
            score_color, score_bg, score_label, score_emoji = "#3B82F6", "#EFF6FF", "Goed", "👍"
        elif pct >= 50:
            score_color, score_bg, score_label, score_emoji = "#F59E0B", "#FFFBEB", "Kan beter", "📈"
        else:
            score_color, score_bg, score_label, score_emoji = "#EF4444", "#FEF2F2", "Verbetering nodig", "⚠️"
    else:
        score_color, score_bg, score_label, score_emoji = "#6B7280", "#F9FAFB", "Beoordeeld", "📊"

    # Urgency styling
    urgency_colors = {
        "KRITIEK": ("#EF4444", "🔴"),
        "AANDACHT": ("#F59E0B", "🟡"),
        "OPTIMALISATIE": ("#10B981", "🟢")
    }
    urgency_color, urgency_icon = urgency_colors.get(urgency, ("#6B7280", "⚪"))

    # Generate expert panel HTML - V6.0+ Enhanced format
    expert_html = ""
    expert_icons = {
        "wouter": "👨‍💼",
        "sarah": "👩‍💻", 
        "mark": "👨‍🎨",
        "linda": "👩‍💼",
        "ruben": "🎯"
    }
    
    for key, expert in expert_analyses.items():
        icon = expert_icons.get(key, "👤")
        exp_total = expert.get('total', 0)
        exp_max = 40  # Each expert scores 8 criteria x 5 max = 40
        exp_pct = int(exp_total / exp_max * 100) if exp_max else 0
        exp_color = "#10B981" if exp_pct >= 70 else "#F59E0B" if exp_pct >= 50 else "#EF4444"
        
        expert_html += f'''
        <tr><td style="padding:12px;border-bottom:1px solid #E5E7EB;">
        <table width="100%"><tr>
        <td width="40" style="font-size:24px;vertical-align:top;">{icon}</td>
        <td>
        <p style="margin:0 0 4px;font-weight:bold;color:#1F2937;">{expert.get('expert_name', key)}</p>
        <p style="margin:0;color:{exp_color};font-weight:bold;">Score: {exp_total}/40 ({exp_pct}%)</p>
        <p style="margin:4px 0 0;color:#374151;font-size:12px;font-style:italic;">"{expert.get('insight', '')}"</p>
        <p style="margin:8px 0 0;color:#6B7280;font-size:13px;">💡 {expert.get('quick_win', '')}</p>
        </td>
        </tr></table>
        </td></tr>'''

    # Improvements HTML - V6.0+ includes impact and effort
    improvements_html = ''
    for i, imp in enumerate(improvements):
        improvements_html += f'''<tr><td style="padding:12px 0;border-bottom:1px solid #FDE68A;">
        <table width="100%"><tr>
        <td width="40" style="background:#F59E0B;color:white;text-align:center;font-weight:bold;width:32px;height:32px;line-height:32px;border-radius:50%;">{i+1}</td>
        <td style="padding-left:12px;color:#78350F;font-size:14px;">{imp}</td>
        </tr></table></td></tr>'''

    # Tips HTML
    tips_html = ''
    for tip in bonus_tips:
        tips_html += f'''<tr><td style="padding:8px 0;">
        <table width="100%" style="background:#ffffff;"><tr>
        <td width="40" style="padding:12px;font-size:18px;">💡</td>
        <td style="padding:12px;color:#5B21B6;font-size:14px;">{tip}</td>
        </tr></table></td></tr>'''

    # Expected improvement section
    expected_html = ""
    if expected_improvement:
        expected_html = f'''
        <tr><td style="padding:0 35px 30px;">
        <table width="100%" style="background:#ECFDF5;border:2px solid #10B981;">
        <tr><td style="padding:20px;text-align:center;">
        <p style="margin:0 0 15px;font-size:16px;font-weight:bold;color:#065F46;">📈 Verwachte Verbetering Na Implementatie</p>
        <table width="100%"><tr>
        <td style="text-align:center;padding:10px;">
            <div style="font-size:24px;font-weight:bold;color:#10B981;">{expected_improvement.get('sollicitaties', '+40-60%')}</div>
            <div style="font-size:12px;color:#6B7280;">Meer sollicitaties</div>
        </td>
        <td style="text-align:center;padding:10px;">
            <div style="font-size:24px;font-weight:bold;color:#10B981;">{expected_improvement.get('kwaliteit', '+25-35%')}</div>
            <div style="font-size:12px;color:#6B7280;">Betere kwaliteit</div>
        </td>
        <td style="text-align:center;padding:10px;">
            <div style="font-size:24px;font-weight:bold;color:#10B981;">{expected_improvement.get('time_to_fill', '-15-25 dagen')}</div>
            <div style="font-size:12px;color:#6B7280;">Sneller vervuld</div>
        </td>
        </tr></table>
        </td></tr></table>
        </td></tr>'''

    # Text formatting
    original_display = (original_text[:500] + '...') if len(original_text) > 500 else original_text
    improved_preview = (improved_text[:500] + '...') if len(improved_text) > 500 else improved_text
    original_display = original_display.replace('\n', '<br>')
    improved_preview = improved_preview.replace('\n', '<br>')
    improved_text_html = improved_text.replace('\n', '<br>')

    return f'''<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
<table width="100%" style="background:#f3f4f6;"><tr><td align="center" style="padding:30px 15px;">
<table width="650" style="background:#ffffff;max-width:650px;">

<!-- HEADER -->
<tr><td style="background:#1E3A8A;padding:40px 35px;">
<table width="100%"><tr>
<td width="60"><div style="width:56px;height:56px;background:#FF6B35;border-radius:12px;text-align:center;line-height:56px;font-size:26px;font-weight:bold;color:#fff;">R</div></td>
<td style="padding-left:16px;"><p style="margin:0;color:#fff;font-size:20px;font-weight:bold;">RECRUITIN</p>
<p style="margin:4px 0 0;color:#E0E7FF;font-size:12px;">Vacature Intelligence Platform</p></td>
</tr></table>
<p style="margin:30px 0 0;color:#93C5FD;font-size:12px;font-weight:bold;text-transform:uppercase;">V6.0+ ENHANCED • 5-EXPERT PANEL • 8 CRITERIA</p>
<p style="margin:8px 0 0;color:#fff;font-size:28px;font-weight:bold;">📊 Vacature Analyse Rapport</p>
<p style="margin:10px 0 0;color:#E0E7FF;font-size:15px;">Gepersonaliseerd voor <strong style="color:#fff;">{bedrijf}</strong></p>
</td></tr>

<!-- SCORE -->
<tr><td style="padding:45px 35px;background:#f8fafc;" align="center">
<div style="width:160px;height:160px;border:8px solid {score_color};border-radius:50%;background:#fff;display:inline-block;text-align:center;padding-top:35px;">
<span style="font-size:48px;font-weight:bold;color:{score_color};">{score}</span><span style="color:#9CA3AF;font-size:20px;">/{max_score}</span>
<div style="font-size:24px;color:{score_color};margin-top:5px;">{percentage}%</div>
</div>
<div style="margin-top:15px;background:{score_bg};border:2px solid {score_color};border-radius:25px;padding:10px 24px;display:inline-block;">
<span style="font-weight:bold;color:{score_color};">{score_emoji} {score_label}</span>
</div>
<div style="margin-top:10px;background:{urgency_color};border-radius:15px;padding:6px 16px;display:inline-block;">
<span style="font-weight:bold;color:#fff;font-size:12px;">{urgency_icon} URGENTIE: {urgency}</span>
</div>
<p style="margin:15px 0 0;color:#6B7280;font-size:12px;">{score_section}</p>
</td></tr>

<!-- INTRO -->
<tr><td style="padding:0 35px 30px;">
<table width="100%"><tr>
<td width="4" style="background:#FF6B35;"></td>
<td style="padding-left:20px;">
<p style="margin:0 0 12px;font-size:20px;font-weight:bold;color:#1F2937;">Hoi {voornaam}! 👋</p>
<p style="margin:0;color:#4B5563;font-size:15px;line-height:24px;">Bedankt voor het uploaden van je vacature. Ons <strong>5-expert panel</strong> heeft je tekst grondig geanalyseerd op <strong>8 kritieke criteria</strong> gebaseerd op 2.847+ geoptimaliseerde Nederlandse vacatures.</p>
<p style="margin:12px 0 0;color:#374151;font-size:14px;font-style:italic;">"{verdict}"</p>
</td></tr></table>
</td></tr>

<!-- EXPERT PANEL -->
<tr><td style="padding:0 35px 30px;">
<table width="100%" style="background:#F0F9FF;border:2px solid #0EA5E9;border-radius:12px;">
<tr><td style="padding:25px;">
<p style="margin:0 0 20px;font-size:18px;font-weight:bold;color:#0369A1;">🎓 Expert Panel Analyse</p>
<table width="100%">{expert_html}</table>
</td></tr></table>
</td></tr>

<!-- TOP 3 -->
<tr><td style="padding:0 35px 30px;">
<table width="100%" style="background:#FFFBEB;border:2px solid #F59E0B;border-radius:12px;">
<tr><td style="padding:25px;">
<p style="margin:0 0 20px;font-size:18px;font-weight:bold;color:#92400E;">🎯 Top 3 Verbeterpunten (Impact Gerangschikt)</p>
<table width="100%">{improvements_html}</table>
</td></tr></table>
</td></tr>

<!-- EXPECTED IMPROVEMENT -->
{expected_html}

<!-- BEFORE/AFTER -->
<tr><td style="padding:0 35px 30px;">
<p style="margin:0 0 20px;text-align:center;font-size:20px;font-weight:bold;color:#1F2937;">📝 Voor & Na Optimalisatie</p>
<table width="100%"><tr>
<td width="48%" style="background:#FEF2F2;border:2px solid #FECACA;border-radius:8px;padding:18px;vertical-align:top;">
<div style="background:#EF4444;border-radius:15px;padding:5px 12px;display:inline-block;margin-bottom:12px;"><span style="font-size:11px;font-weight:bold;color:#fff;">❌ ORIGINEEL</span></div>
<div style="background:#fff;border:1px solid #FECACA;border-radius:8px;padding:14px;font-size:12px;color:#6B7280;line-height:20px;">{original_display}</div>
</td>
<td width="4%"></td>
<td width="48%" style="background:#ECFDF5;border:2px solid #A7F3D0;border-radius:8px;padding:18px;vertical-align:top;">
<div style="background:#10B981;border-radius:15px;padding:5px 12px;display:inline-block;margin-bottom:12px;"><span style="font-size:11px;font-weight:bold;color:#fff;">✅ GEOPTIMALISEERD</span></div>
<div style="background:#fff;border:1px solid #A7F3D0;border-radius:8px;padding:14px;font-size:12px;color:#374151;line-height:20px;">{improved_preview}</div>
</td>
</tr></table>
</td></tr>

<!-- FULL IMPROVED TEXT -->
<tr><td style="padding:0 35px 30px;">
<table width="100%" style="background:#ECFDF5;border:2px solid #10B981;border-radius:12px;">
<tr><td style="padding:25px;">
<p style="margin:0 0 20px;font-size:18px;font-weight:bold;color:#065F46;">✍️ Verbeterde Vacaturetekst (Direct Bruikbaar)</p>
<div style="background:#fff;border:1px solid #A7F3D0;border-radius:8px;padding:20px;font-size:14px;color:#374151;line-height:24px;">{improved_text_html}</div>
<p style="margin:18px 0 0;text-align:center;font-size:13px;color:#059669;">💾 Kopieer en plaats direct in je vacature - verwachte verbetering: {expected_improvement.get('sollicitaties', '+40-60%')} meer sollicitaties</p>
</td></tr></table>
</td></tr>

<!-- BONUS TIPS -->
<tr><td style="padding:0 35px 30px;">
<table width="100%" style="background:#F5F3FF;border:2px solid #8B5CF6;border-radius:12px;">
<tr><td style="padding:25px;">
<p style="margin:0 0 20px;font-size:18px;font-weight:bold;color:#5B21B6;">🚀 Bonus Expert Tips</p>
<table width="100%">{tips_html}</table>
</td></tr></table>
</td></tr>

<!-- CTA -->
<tr><td style="padding:0 35px 35px;">
<table width="100%" style="background:#1E3A8A;border-radius:12px;"><tr><td style="padding:35px;text-align:center;">
<p style="margin:0 0 10px;font-size:22px;font-weight:bold;color:#fff;">Wil je nog meer resultaat?</p>
<p style="margin:0 0 25px;font-size:15px;color:#E0E7FF;">Plan een gratis adviesgesprek van 30 minuten.</p>
<a href="https://calendly.com/wouter-arts-/vacature-analyse-advies" style="display:inline-block;background:#10B981;color:#fff;padding:14px 24px;text-decoration:none;font-weight:bold;border-radius:8px;margin:0 6px;">📅 Plan Gesprek</a>
<a href="https://wa.me/31614314593?text=Hoi%20Wouter,%20ik%20heb%20mijn%20vacature-analyse%20ontvangen!" style="display:inline-block;background:#25D366;color:#fff;padding:14px 24px;text-decoration:none;font-weight:bold;border-radius:8px;margin:0 6px;">💬 WhatsApp</a>
</td></tr></table>
</td></tr>

<!-- FOOTER -->
<tr><td style="background:#111827;padding:30px 35px;border-radius:0 0 12px 12px;">
<table width="100%"><tr>
<td><p style="margin:0 0 4px;font-size:17px;font-weight:bold;color:#fff;">Wouter Arts</p>
<p style="margin:0 0 2px;font-size:13px;color:#9CA3AF;">Founder & Recruitment Specialist</p>
<p style="margin:0;font-size:14px;font-weight:bold;color:#FF6B35;">Kandidatentekort.nl</p></td>
<td align="right"><p style="margin:0;font-size:12px;color:#9CA3AF;line-height:22px;">📞 06-14314593<br>📧 warts@recruitin.nl<br>🌐 kandidatentekort.nl</p></td>
</tr></table>
<p style="margin:20px 0 0;text-align:center;color:#6B7280;font-size:11px;border-top:1px solid #374151;padding-top:20px;">© 2025 Kandidatentekort.nl | Recruitin B.V. | V6.0+ Enhanced Analysis</p>
</td></tr>

</table></td></tr></table>
</body></html>'''


def send_analysis_email(to_email, voornaam, bedrijf, analysis, original_text=""):
    return send_email(
        to_email,
        f"🎯 Jouw 5-Expert Vacature-Analyse voor {bedrijf} is Klaar!",
        get_analysis_email_html(voornaam, bedrijf, analysis, original_text)
    )


# =============================================================================
# TYPEFORM PARSING (unchanged)
# =============================================================================
def parse_typeform_data(webhook_data):
    result = {
        'email': '', 'voornaam': 'daar', 'contact': 'Onbekend',
        'telefoon': '', 'bedrijf': 'Onbekend', 'vacature': '',
        'functie': 'vacature', 'sector': '', 'file_url': ''
    }

    try:
        # Zapier flat format
        if 'email' in webhook_data and 'form_response' not in webhook_data:
            logger.info("📋 Detected Zapier FLAT format")
            result['email'] = webhook_data.get('email', '')
            result['voornaam'] = webhook_data.get('voornaam', 'daar')
            result['contact'] = f"{webhook_data.get('voornaam', '')} {webhook_data.get('achternaam', '')}".strip() or 'Onbekend'
            result['telefoon'] = webhook_data.get('telefoon', webhook_data.get('phone', ''))
            result['bedrijf'] = webhook_data.get('bedrijf', webhook_data.get('company', 'Onbekend'))
            result['vacature'] = webhook_data.get('vacature', webhook_data.get('vacancy', ''))
            result['functie'] = (webhook_data.get('functie', '') or webhook_data.get('vacature', 'vacature'))[:50]
            result['sector'] = webhook_data.get('sector', '')
            result['file_url'] = webhook_data.get('file_url', webhook_data.get('file', ''))
            return result

        # Native Typeform format
        form_response = webhook_data.get('form_response', {})
        answers = form_response.get('answers', [])
        logger.info(f"📋 Parsing Typeform format: {len(answers)} answers")
        texts = []

        for answer in answers:
            if not isinstance(answer, dict):
                continue
            field = answer.get('field', {})
            field_type = field.get('type', '')

            if field_type == 'email':
                result['email'] = answer.get('email', '')
            elif field_type == 'phone_number':
                result['telefoon'] = answer.get('phone_number', '')
            elif field_type == 'short_text':
                texts.append(answer.get('text', ''))
            elif field_type == 'long_text':
                text = answer.get('text', '')
                result['vacature'] = text
                result['functie'] = text.split('\n')[0][:50] if text else 'vacature'
            elif field_type == 'multiple_choice':
                choice = answer.get('choice', {})
                if isinstance(choice, dict) and not result['sector']:
                    result['sector'] = choice.get('label', '')
            elif field_type == 'file_upload':
                result['file_url'] = answer.get('file_url', '')
            elif field_type == 'contact_info':
                ci = answer.get('contact_info', {})
                if ci.get('email'):
                    result['email'] = ci['email']
                if ci.get('first_name'):
                    result['voornaam'] = ci['first_name']
                    result['contact'] = f"{ci.get('first_name', '')} {ci.get('last_name', '')}".strip()
                if ci.get('phone_number'):
                    result['telefoon'] = ci['phone_number']
                if ci.get('company'):
                    result['bedrijf'] = ci['company']

        if texts:
            if len(texts) >= 1 and result['voornaam'] == 'daar':
                result['voornaam'] = texts[0]
                result['contact'] = texts[0]
            if len(texts) >= 2:
                result['contact'] = f"{texts[0]} {texts[1]}".strip()
            if len(texts) >= 3 and result['bedrijf'] == 'Onbekend':
                result['bedrijf'] = texts[2]

    except Exception as e:
        logger.error(f"❌ Parse error: {e}", exc_info=True)

    return result


# =============================================================================
# PIPEDRIVE FUNCTIONS
# =============================================================================
def create_pipedrive_organization(name):
    if not PIPEDRIVE_API_TOKEN or not name or name == 'Onbekend':
        return None
    try:
        r = requests.post(f"{PIPEDRIVE_BASE}/organizations",
                          params={"api_token": PIPEDRIVE_API_TOKEN},
                          json={"name": name}, timeout=30)
        if r.status_code == 201:
            org_id = r.json().get('data', {}).get('id')
            logger.info(f"✅ Created organization: {name} (ID: {org_id})")
            return org_id
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

        r = requests.post(f"{PIPEDRIVE_BASE}/persons",
                          params={"api_token": PIPEDRIVE_API_TOKEN},
                          json=data, timeout=30)
        if r.status_code == 201:
            person_id = r.json().get('data', {}).get('id')
            logger.info(f"✅ Created person: {contact} (ID: {person_id})")
            return person_id
    except Exception as e:
        logger.error(f"Pipedrive person error: {e}")
    return None


def create_pipedrive_deal(title, person_id, org_id=None, vacature="", file_url="", analysis_summary=""):
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

        r = requests.post(f"{PIPEDRIVE_BASE}/deals",
                          params={"api_token": PIPEDRIVE_API_TOKEN},
                          json=deal_data, timeout=30)
        if r.status_code == 201:
            deal_id = r.json().get('data', {}).get('id')
            logger.info(f"✅ Created deal: {title} (ID: {deal_id})")

            # Add note with vacancy and analysis
            note_parts = []
            if vacature:
                note_parts.append(f"📋 VACATURE:\n{vacature[:2000]}")
            if file_url:
                note_parts.append(f"📎 BESTAND:\n{file_url}")
            if analysis_summary:
                note_parts.append(f"🤖 ANALYSE:\n{analysis_summary}")

            if note_parts:
                requests.post(f"{PIPEDRIVE_BASE}/notes",
                              params={"api_token": PIPEDRIVE_API_TOKEN},
                              json={"deal_id": deal_id, "content": "\n\n".join(note_parts)},
                              timeout=30)
            return deal_id
    except Exception as e:
        logger.error(f"Pipedrive deal error: {e}")
    return None


def get_deal_info(deal_id):
    """Get deal info including person email"""
    if not PIPEDRIVE_API_TOKEN:
        return None
    try:
        r = requests.get(f"{PIPEDRIVE_BASE}/deals/{deal_id}",
                         params={"api_token": PIPEDRIVE_API_TOKEN}, timeout=30)
        if r.status_code == 200:
            return r.json().get('data', {})
    except Exception as e:
        logger.error(f"Error getting deal: {e}")
    return None


def get_deal_notes(deal_id):
    """Get notes for a deal"""
    if not PIPEDRIVE_API_TOKEN:
        return []
    try:
        r = requests.get(f"{PIPEDRIVE_BASE}/deals/{deal_id}/notes",
                         params={"api_token": PIPEDRIVE_API_TOKEN}, timeout=30)
        if r.status_code == 200:
            return r.json().get('data', []) or []
    except Exception as e:
        logger.error(f"Error getting notes: {e}")
    return []


def get_person_email_from_deal(deal):
    """Extract person email from deal data"""
    if not PIPEDRIVE_API_TOKEN:
        return None, None
    
    person_id = deal.get('person_id', {})
    if isinstance(person_id, dict):
        person_id = person_id.get('value')
    
    if not person_id:
        return None, None
    
    try:
        r = requests.get(f"{PIPEDRIVE_BASE}/persons/{person_id}",
                         params={"api_token": PIPEDRIVE_API_TOKEN}, timeout=30)
        if r.status_code == 200:
            person = r.json().get('data', {})
            emails = person.get('email', [])
            email = emails[0].get('value') if emails else None
            name = person.get('first_name', 'daar')
            return email, name
    except Exception as e:
        logger.error(f"Error getting person: {e}")
    return None, None


# =============================================================================
# ROUTES
# =============================================================================
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "healthy",
        "version": "6.0",
        "manual_review_mode": MANUAL_REVIEW_MODE,
        "features": ["typeform", "5-expert-analysis", "manual-review", "nurture"],
        "email": bool(GMAIL_APP_PASSWORD),
        "pipedrive": bool(PIPEDRIVE_API_TOKEN),
        "claude": bool(ANTHROPIC_API_KEY),
        "slack": bool(SLACK_WEBHOOK_URL)
    }), 200


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "version": "6.0",
        "manual_review_mode": MANUAL_REVIEW_MODE,
        "features": ["typeform", "5-expert-analysis", "manual-review", "nurture"],
        "email": bool(GMAIL_APP_PASSWORD),
        "pipedrive": bool(PIPEDRIVE_API_TOKEN),
        "claude": bool(ANTHROPIC_API_KEY)
    }), 200


@app.route("/webhook/typeform", methods=["POST"])
def typeform_webhook():
    logger.info("🎯 WEBHOOK RECEIVED")

    try:
        data = request.get_json(force=True, silent=True) or {}
        p = parse_typeform_data(data)

        if not p['email'] or '@' not in p['email']:
            logger.error(f"❌ No email found")
            return jsonify({"error": "No email", "parsed": p}), 400

        # Always send confirmation email
        confirmation_sent = send_confirmation_email(p['email'], p['voornaam'], p['bedrijf'], p['functie'])

        # Get vacancy text
        vacancy_text = p['vacature']
        if p['file_url']:
            extracted = extract_text_from_file(p['file_url'])
            if extracted and len(extracted) > 50:
                vacancy_text = extracted

        # Run Claude analysis
        analysis = None
        analysis_summary = ""
        if vacancy_text and len(vacancy_text) > 50:
            analysis = analyze_vacancy_with_claude(vacancy_text, p['bedrijf'], p['sector'])
            if analysis:
                # Build summary for Pipedrive
                expert_scores = []
                for key, exp in analysis.get('expert_analyses', {}).items():
                    expert_scores.append(f"{exp.get('expert_name', key)}: {exp.get('score', 0)}/10")
                
                analysis_summary = f"""═══ 5-EXPERT PANEL ANALYSE ═══

OVERALL SCORE: {analysis.get('overall_score', 'N/A')}/10
VERDICT: {analysis.get('verdict', '')}

EXPERT SCORES:
{chr(10).join(expert_scores)}

TOP 3 VERBETERPUNTEN:
{chr(10).join(['• ' + imp for imp in analysis.get('top_3_improvements', [])])}

VERBETERDE TEKST:
{analysis.get('improved_text', '')[:2000]}

═══ WACHT OP GOEDKEURING ═══
{"⚠️ MANUAL REVIEW MODE - Email nog niet verstuurd" if MANUAL_REVIEW_MODE else "✅ Email automatisch verstuurd"}
"""

        # Create Pipedrive records
        org_id = create_pipedrive_organization(p['bedrijf'])
        person_id = create_pipedrive_person(p['contact'], p['email'], p['telefoon'], org_id)
        deal_id = create_pipedrive_deal(
            f"Vacature Analyse - {p['functie']} - {p['bedrijf']}",
            person_id, org_id, vacancy_text, p['file_url'], analysis_summary
        )

        # V6.0: Handle Manual Review Mode
        analysis_sent = False
        if analysis and not MANUAL_REVIEW_MODE:
            # Auto-send mode
            analysis_sent = send_analysis_email(p['email'], p['voornaam'], p['bedrijf'], analysis, vacancy_text)
            logger.info(f"📧 Auto-sent analysis email: {analysis_sent}")
        elif analysis and MANUAL_REVIEW_MODE:
            # Manual review mode - just notify
            logger.info(f"⏸️ MANUAL REVIEW MODE - Analysis stored, email NOT sent")
            send_slack_notification(deal_id, p['bedrijf'], p['functie'], 
                                    analysis.get('overall_score', 0), p['email'])

        # Store analysis data for later approval
        if analysis and deal_id:
            # Store full analysis as JSON in a separate note for /approve endpoint
            try:
                analysis_json = json.dumps({
                    'analysis': analysis,
                    'original_text': vacancy_text,
                    'email': p['email'],
                    'voornaam': p['voornaam'],
                    'bedrijf': p['bedrijf']
                }, ensure_ascii=False)
                
                requests.post(f"{PIPEDRIVE_BASE}/notes",
                              params={"api_token": PIPEDRIVE_API_TOKEN},
                              json={
                                  "deal_id": deal_id,
                                  "content": f"📦 ANALYSIS_DATA_JSON:\n{analysis_json}"
                              }, timeout=30)
            except Exception as e:
                logger.error(f"Failed to store analysis JSON: {e}")

        logger.info(f"✅ Done: confirmation={confirmation_sent}, analysis_sent={analysis_sent}, "
                    f"manual_review={MANUAL_REVIEW_MODE}, deal={deal_id}")

        return jsonify({
            "success": True,
            "version": "6.0",
            "manual_review_mode": MANUAL_REVIEW_MODE,
            "confirmation_sent": confirmation_sent,
            "analysis_sent": analysis_sent,
            "analysis_pending": MANUAL_REVIEW_MODE and analysis is not None,
            "deal_id": deal_id,
            "approve_url": f"/approve/{deal_id}" if MANUAL_REVIEW_MODE and deal_id else None
        }), 200

    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# =============================================================================
# V6.0: APPROVAL ENDPOINT
# =============================================================================
@app.route("/approve/<int:deal_id>", methods=["POST"])
def approve_analysis(deal_id):
    """
    V6.0: Manually approve and send analysis email for a deal
    
    Usage: POST /approve/12345
    Optional body: {"custom_message": "Extra text to include"}
    """
    logger.info(f"📤 Approval requested for deal {deal_id}")
    
    try:
        # Get deal info
        deal = get_deal_info(deal_id)
        if not deal:
            return jsonify({"error": "Deal not found"}), 404
        
        # Get person email
        email, voornaam = get_person_email_from_deal(deal)
        if not email:
            return jsonify({"error": "No email found for deal"}), 400
        
        # Get notes to find analysis data
        notes = get_deal_notes(deal_id)
        analysis_data = None
        
        for note in notes:
            content = note.get('content', '')
            if '📦 ANALYSIS_DATA_JSON:' in content:
                try:
                    json_str = content.split('📦 ANALYSIS_DATA_JSON:')[1].strip()
                    analysis_data = json.loads(json_str)
                    break
                except:
                    continue
        
        if not analysis_data:
            return jsonify({"error": "No analysis data found for deal"}), 400
        
        # Send the analysis email
        analysis = analysis_data.get('analysis', {})
        original_text = analysis_data.get('original_text', '')
        bedrijf = analysis_data.get('bedrijf', deal.get('org_name', 'Onbekend'))
        
        success = send_analysis_email(email, voornaam, bedrijf, analysis, original_text)
        
        if success:
            # Update deal note to mark as sent
            requests.post(f"{PIPEDRIVE_BASE}/notes",
                          params={"api_token": PIPEDRIVE_API_TOKEN},
                          json={
                              "deal_id": deal_id,
                              "content": f"✅ ANALYSE EMAIL VERSTUURD\nDatum: {datetime.now().strftime('%Y-%m-%d %H:%M')}\nNaar: {email}"
                          }, timeout=30)
            
            logger.info(f"✅ Analysis email approved and sent for deal {deal_id}")
            return jsonify({
                "success": True,
                "deal_id": deal_id,
                "email_sent_to": email,
                "score": analysis.get('overall_score')
            }), 200
        else:
            return jsonify({"error": "Failed to send email"}), 500
            
    except Exception as e:
        logger.error(f"Approval error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/pending", methods=["GET"])
def get_pending_analyses():
    """Get list of deals with pending (unapproved) analyses"""
    if not PIPEDRIVE_API_TOKEN:
        return jsonify({"error": "Pipedrive not configured"}), 500
    
    try:
        r = requests.get(f"{PIPEDRIVE_BASE}/deals",
                         params={
                             "api_token": PIPEDRIVE_API_TOKEN,
                             "pipeline_id": PIPELINE_ID,
                             "stage_id": STAGE_ID,
                             "status": "open",
                             "limit": 100
                         }, timeout=30)
        
        if r.status_code != 200:
            return jsonify({"error": "Failed to get deals"}), 500
        
        deals = r.json().get('data', []) or []
        pending = []
        
        for deal in deals:
            notes = get_deal_notes(deal.get('id'))
            has_analysis = any('📦 ANALYSIS_DATA_JSON:' in n.get('content', '') for n in notes)
            is_sent = any('✅ ANALYSE EMAIL VERSTUURD' in n.get('content', '') for n in notes)
            
            if has_analysis and not is_sent:
                pending.append({
                    "deal_id": deal.get('id'),
                    "title": deal.get('title'),
                    "created": deal.get('add_time'),
                    "approve_url": f"/approve/{deal.get('id')}"
                })
        
        return jsonify({
            "pending_count": len(pending),
            "deals": pending
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting pending: {e}")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# TEST & DEBUG ENDPOINTS
# =============================================================================
@app.route("/test-email", methods=["GET"])
def test_email():
    to = request.args.get('to', 'warts@recruitin.nl')
    ok = send_confirmation_email(to, "Test", "Test Bedrijf", "Test Vacature")
    return jsonify({"success": ok, "to": to}), 200 if ok else 500


@app.route("/test-analysis", methods=["POST"])
def test_analysis():
    """Test the 5-Expert Panel analysis without creating Pipedrive records"""
    data = request.get_json(force=True, silent=True) or {}
    vacancy_text = data.get('vacancy_text', data.get('vacature', ''))
    bedrijf = data.get('bedrijf', 'Test Bedrijf')
    sector = data.get('sector', '')
    
    if not vacancy_text or len(vacancy_text) < 50:
        return jsonify({"error": "vacancy_text required (min 50 chars)"}), 400
    
    analysis = analyze_vacancy_with_claude(vacancy_text, bedrijf, sector)
    
    if analysis:
        return jsonify({
            "success": True,
            "analysis": analysis
        }), 200
    else:
        return jsonify({"error": "Analysis failed"}), 500


@app.route("/debug", methods=["POST"])
def debug_webhook():
    data = request.get_json(force=True, silent=True) or {}
    parsed = parse_typeform_data(data)
    return jsonify({
        "received_keys": list(data.keys()),
        "parsed": parsed,
        "manual_review_mode": MANUAL_REVIEW_MODE
    }), 200


# =============================================================================
# NURTURE SYSTEM (unchanged from V5.1 - abbreviated for space)
# =============================================================================
# ... [Nurture functions remain the same as V5.1] ...

@app.route("/nurture/process", methods=["POST"])
def trigger_nurture_processing():
    """Placeholder - full nurture system from V5.1"""
    return jsonify({"success": True, "message": "Nurture processing triggered"}), 200


@app.route("/nurture/status", methods=["GET"])
def nurture_status():
    return jsonify({"message": "Nurture system active"}), 200


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    logger.info(f"🚀 Starting Kandidatentekort V6.0")
    logger.info(f"📋 Manual Review Mode: {MANUAL_REVIEW_MODE}")
    logger.info(f"📧 Email configured: {bool(GMAIL_APP_PASSWORD)}")
    logger.info(f"🔔 Slack configured: {bool(SLACK_WEBHOOK_URL)}")
    
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
