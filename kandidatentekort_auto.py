#!/usr/bin/env python3
"""
KANDIDATENTEKORT.NL - WEBHOOK AUTOMATION
Deploy: Render.com | Updated: 2025-11-27
"""

import os, json, logging, smtplib, requests
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

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
    return send_email(to_email, f"✅ Ontvangen: Vacature-analyse voor {functie}", get_confirmation_email_html(voornaam, bedrijf, functie))

def parse_typeform_data(webhook_data):
    """Parse Typeform webhook data - handles both regular fields and contact_info blocks"""
    result = {'bedrijf':'Onbekend','contact':'Onbekend','voornaam':'daar','email':'','telefoon':'','vacature':'','functie':'vacature'}
    try:
        for answer in webhook_data.get('form_response',{}).get('answers',[]):
            field_type = answer.get('field',{}).get('type','')
            ref = (answer.get('field',{}).get('ref','') or '').lower()

            # Handle contact_info block (contains email, first_name, last_name, phone, company)
            if field_type == 'contact_info' or 'contact_info' in answer:
                contact_info = answer.get('contact_info', {})
                if contact_info:
                    if contact_info.get('email'):
                        result['email'] = contact_info['email']
                    if contact_info.get('first_name'):
                        first_name = contact_info.get('first_name', '')
                        last_name = contact_info.get('last_name', '')
                        full_name = f"{first_name} {last_name}".strip()
                        result['contact'] = full_name
                        result['voornaam'] = first_name or 'daar'
                    if contact_info.get('phone_number'):
                        result['telefoon'] = contact_info['phone_number']
                    if contact_info.get('company'):
                        result['bedrijf'] = contact_info['company']
                continue

            # Handle regular fields
            v = answer.get('text','') or answer.get('email','') or answer.get('phone_number','') or answer.get('choice',{}).get('label','')

            # Handle multiple choice with multiple selections
            if 'choices' in answer:
                v = ', '.join([c.get('label','') for c in answer.get('choices',[])])

            # Handle file uploads
            if field_type == 'file_upload':
                v = answer.get('file_url','')

            if any(x in ref for x in ['bedrijf','company']): result['bedrijf'] = v
            elif any(x in ref for x in ['naam','name','contact']): result['contact'] = v; result['voornaam'] = v.split()[0] if v else 'daar'
            elif 'email' in ref: result['email'] = v
            elif any(x in ref for x in ['telefoon','phone']): result['telefoon'] = v
            elif any(x in ref for x in ['vacature','vacancy','tekst']): result['vacature'] = v; result['functie'] = v.split('\n')[0][:50] if v else 'vacature'
    except Exception as e:
        logger.error(f"Parse error: {e}")

    logger.info(f"📋 Parsed data: email={result['email']}, contact={result['contact']}, bedrijf={result['bedrijf']}")
    return result

def create_pipedrive_person(contact, email, telefoon):
    try:
        r = requests.post(f"{PIPEDRIVE_BASE}/persons", params={"api_token":PIPEDRIVE_API_TOKEN}, json={"name":contact,"email":[{"value":email,"primary":True}],"phone":[{"value":telefoon,"primary":True}] if telefoon else []}, timeout=30)
        return r.json().get('data',{}).get('id') if r.status_code==201 else None
    except: return None

def create_pipedrive_deal(title, person_id, vacature, analysis=""):
    try:
        r = requests.post(f"{PIPEDRIVE_BASE}/deals", params={"api_token":PIPEDRIVE_API_TOKEN}, json={"title":title,"person_id":person_id,"pipeline_id":PIPELINE_ID,"stage_id":STAGE_ID}, timeout=30)
        if r.status_code==201:
            deal_id = r.json().get('data',{}).get('id')
            if vacature: requests.post(f"{PIPEDRIVE_BASE}/notes", params={"api_token":PIPEDRIVE_API_TOKEN}, json={"deal_id":deal_id,"content":f"📋 VACATURE:\n{vacature[:2000]}\n\n🤖 ANALYSE:\n{analysis}"}, timeout=30)
            return deal_id
    except: pass
    return None

def analyze_vacancy(vacature, bedrijf, functie):
    if not ANTHROPIC_API_KEY or len(vacature)<50: return ""
    try:
        r = requests.post("https://api.anthropic.com/v1/messages", headers={"x-api-key":ANTHROPIC_API_KEY,"anthropic-version":"2023-06-01","content-type":"application/json"}, json={"model":"claude-sonnet-4-20250514","max_tokens":2000,"messages":[{"role":"user","content":f"Analyseer vacature {functie} bij {bedrijf}:\n{vacature[:8000]}\n\nGeef: 1.Score 0-100, 2.Top 3 verbeterpunten, 3.Samenvatting"}]}, timeout=60)
        return r.json().get('content',[{}])[0].get('text','') if r.status_code==200 else ""
    except: return ""

@app.route("/", methods=["GET"])
def health(): return jsonify({"status":"healthy","email":bool(GMAIL_APP_PASSWORD),"pipedrive":bool(PIPEDRIVE_API_TOKEN),"claude":bool(ANTHROPIC_API_KEY)}), 200

@app.route("/webhook/typeform", methods=["POST"])
def typeform_webhook():
    logger.info("🎯 WEBHOOK RECEIVED")
    try:
        data = request.get_json()
        logger.info(f"📥 Raw data keys: {list(data.keys()) if data else 'None'}")

        p = parse_typeform_data(data)
        if not p['email'] or '@' not in p['email']:
            logger.error(f"❌ No valid email found. Parsed: {p}")
            return jsonify({"error":"No email"}), 400

        email_sent = send_confirmation_email(p['email'], p['voornaam'], p['bedrijf'], p['functie'])
        person_id = create_pipedrive_person(p['contact'], p['email'], p['telefoon'])
        analysis = analyze_vacancy(p['vacature'], p['bedrijf'], p['functie'])
        deal_id = create_pipedrive_deal(f"Vacature Analyse - {p['functie']} - {p['bedrijf']}", person_id, p['vacature'], analysis)
        logger.info(f"✅ Done: email={email_sent}, person={person_id}, deal={deal_id}")
        return jsonify({"success":True,"email_sent":email_sent,"person_id":person_id,"deal_id":deal_id}), 200
    except Exception as e:
        logger.error(f"❌ {e}")
        return jsonify({"error":str(e)}), 500

@app.route("/test-email", methods=["GET"])
def test_email():
    to = request.args.get('to','artsrecruitin@gmail.com')
    ok = send_confirmation_email(to, "Test", "Test Bedrijf", "Test Vacature")
    return jsonify({"success":ok,"to":to}), 200 if ok else 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",8080)))
