#!/usr/bin/env python3
"""
KANDIDATENTEKORT.NL - WEBHOOK AUTOMATION V2.2
Deploy: Render.com | Updated: 2025-11-27
- Added Pipedrive organization creation
- Added file_url to deal notes
- Fixed org_id linking for person and deal
- Fixed bedrijf parsing (3rd text field, not 5th)
"""

import os
import json
import logging
import smtplib
import requests
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Config
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
PIPEDRIVE_API_TOKEN = os.getenv('PIPEDRIVE_API_TOKEN')
GMAIL_USER = os.getenv('GMAIL_USER', 'artsrecruitin@gmail.com')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD') or os.getenv('GMAIL_PASS')
PIPEDRIVE_BASE = "https://api.pipedrive.com/v1"
PIPELINE_ID = 4
STAGE_ID = 21


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
        "version": "2.2",
        "email": bool(GMAIL_APP_PASSWORD),
        "pipedrive": bool(PIPEDRIVE_API_TOKEN),
        "claude": bool(ANTHROPIC_API_KEY)
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

        # Send confirmation email
        email_sent = send_confirmation_email(
            p['email'],
            p['voornaam'],
            p['bedrijf'],
            p['functie']
        )

        # Create Pipedrive records (organization first, then person, then deal)
        org_id = create_pipedrive_organization(p['bedrijf'])
        person_id = create_pipedrive_person(p['contact'], p['email'], p['telefoon'], org_id)
        deal_id = create_pipedrive_deal(
            f"Vacature Analyse - {p['functie']} - {p['bedrijf']}",
            person_id,
            org_id,
            p['vacature'],
            p['file_url']
        )

        logger.info(f"✅ Done: email={email_sent}, org={org_id}, person={person_id}, deal={deal_id}")

        return jsonify({
            "success": True,
            "email_sent": email_sent,
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
