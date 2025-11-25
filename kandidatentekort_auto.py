#!/usr/bin/env python3
"""
KANDIDATENTEKORT.NL - AUTONOMOUS AUTOMATION
============================================
Volledige flow zonder Zapier - direct API calls

Deploy: Render, Railway, of lokaal met ngrok
Run: python kandidatentekort_auto.py

Environment variables:
- ANTHROPIC_API_KEY
- PIPEDRIVE_API_TOKEN  
- GMAIL_APP_PASSWORD
"""

import os
import json
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from datetime import datetime

# Load .env file
load_dotenv()

# ============================================================
# CONFIG
# ============================================================

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
PIPEDRIVE_API_TOKEN = os.getenv("PIPEDRIVE_API_TOKEN", "57720aa8b264cb9060c9dd5af8ae0c096dbbebb5")
GMAIL_USER = os.getenv("GMAIL_USER", "wouter@recruitin.nl")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
PORT = int(os.getenv("PORT", 8080))

# Pipedrive
PIPEDRIVE_BASE = "https://api.pipedrive.com/v1"
PIPELINE_ID = 4  # vacature analyse pipeline

# Typeform field IDs
FIELDS = {
    "first_name": "field_rlWCM9qIDVnn",
    "last_name": "field_q9xgrm7jnBIy", 
    "phone": "field_1iZBbbmjqjEO",
    "email": "field_MnmHLBESIXfh",
    "company": "field_oCk4xgomQr46",
    "sector": "field_MPI700TSOg7e",
    "goal": "field_btapXJRBLF0k",
    "file": "field_4RwV7AZV5PIY"
}

app = Flask(__name__)

# ============================================================
# TYPEFORM PARSER
# ============================================================

def parse_typeform(data: dict) -> dict:
    """Extract fields from Typeform webhook"""
    answers = {}
    for answer in data.get("form_response", {}).get("answers", []):
        field_id = answer.get("field", {}).get("id", "")
        
        # Get value based on type
        if "text" in answer:
            value = answer["text"]
        elif "email" in answer:
            value = answer["email"]
        elif "phone_number" in answer:
            value = answer["phone_number"]
        elif "choice" in answer:
            value = answer["choice"].get("label", "")
        elif "file_url" in answer:
            value = answer["file_url"]
        elif "url" in answer:
            value = answer["url"]
        else:
            value = str(answer)
        
        answers[field_id] = value
    
    return {
        "first_name": answers.get(FIELDS["first_name"], ""),
        "last_name": answers.get(FIELDS["last_name"], ""),
        "email": answers.get(FIELDS["email"], ""),
        "phone": answers.get(FIELDS["phone"], ""),
        "company": answers.get(FIELDS["company"], ""),
        "sector": answers.get(FIELDS["sector"], ""),
        "goal": answers.get(FIELDS["goal"], ""),
        "file_url": answers.get(FIELDS["file"], ""),
        "submission_id": data.get("form_response", {}).get("token", ""),
        "submitted_at": data.get("form_response", {}).get("submitted_at", "")
    }

# ============================================================
# PIPEDRIVE API
# ============================================================

def pipedrive_request(method: str, endpoint: str, data: dict = None) -> dict:
    """Make Pipedrive API request"""
    url = f"{PIPEDRIVE_BASE}/{endpoint}"
    params = {"api_token": PIPEDRIVE_API_TOKEN}
    
    if method == "GET":
        resp = requests.get(url, params=params)
    elif method == "POST":
        resp = requests.post(url, params=params, json=data)
    elif method == "PUT":
        resp = requests.put(url, params=params, json=data)
    else:
        raise ValueError(f"Unknown method: {method}")
    
    return resp.json()

def create_person(name: str, email: str, phone: str, org_name: str) -> int:
    """Create person in Pipedrive, return ID"""
    data = {
        "name": name,
        "email": email,
        "phone": phone,
        "org_id": None
    }
    
    # First create org if provided
    if org_name:
        org_resp = pipedrive_request("POST", "organizations", {"name": org_name})
        if org_resp.get("success"):
            data["org_id"] = org_resp["data"]["id"]
    
    resp = pipedrive_request("POST", "persons", data)
    if resp.get("success"):
        return resp["data"]["id"]
    return None

def create_deal(title: str, person_id: int, sector: str = "", goal: str = "") -> int:
    """Create deal in Pipedrive, return ID"""
    data = {
        "title": title,
        "person_id": person_id,
        "pipeline_id": PIPELINE_ID,
        "status": "open"
    }
    
    resp = pipedrive_request("POST", "deals", data)
    if resp.get("success"):
        return resp["data"]["id"]
    return None

def update_deal(deal_id: int, updates: dict) -> bool:
    """Update deal in Pipedrive"""
    resp = pipedrive_request("PUT", f"deals/{deal_id}", updates)
    return resp.get("success", False)

def add_note(deal_id: int, content: str) -> bool:
    """Add note to deal"""
    data = {
        "deal_id": deal_id,
        "content": content
    }
    resp = pipedrive_request("POST", "notes", data)
    return resp.get("success", False)

# ============================================================
# FILE DOWNLOAD
# ============================================================

def download_file(url: str) -> str:
    """Download file content from Typeform URL"""
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        
        # Try to decode as text
        try:
            return resp.text
        except:
            return resp.content.decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error downloading file: {e}")
        return ""

# ============================================================
# CLAUDE API (Direct requests - no library needed)
# ============================================================

ANALYSIS_PROMPT = """Je bent een expert recruitment copywriter gespecialiseerd in de Nederlandse technische arbeidsmarkt.

## VACATURETEKST:

{vacature}

## CONTEXT:
- Bedrijf: {company}
- Sector: {sector}
- Doel: {goal}

## OPDRACHT:

Analyseer en verbeter deze vacaturetekst. Lever:

### 1. SCORE (1-10)
Geef een score met korte onderbouwing.

### 2. TOP 3 VERBETERPUNTEN
De 3 belangrijkste verbeteringen, concreet en actionable.

### 3. VERBETERDE VACATURETEKST
Herschrijf de volledige vacaturetekst (400-600 woorden) met:
- Pakkende opening
- Duidelijke functie-inhoud
- Concrete arbeidsvoorwaarden
- Sterke employer branding
- Overtuigende call-to-action

### 4. BONUS TIPS
2-3 extra tips voor meer kandidaten.

Schrijf in het Nederlands, professioneel maar toegankelijk."""

def analyze_vacature(vacature: str, company: str, sector: str, goal: str) -> str:
    """Analyze vacature with Claude API using direct requests"""
    
    prompt = ANALYSIS_PROMPT.format(
        vacature=vacature if vacature else "Geen vacaturetekst geüpload - geef algemene tips voor een goede vacaturetekst.",
        company=company if company else "Onbekend",
        sector=sector if sector else "Algemeen",
        goal=goal if goal else "Meer gekwalificeerde sollicitanten"
    )
    
    headers = {
        "Content-Type": "application/json",
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01"
    }
    
    data = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 4096,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            timeout=120
        )
        resp.raise_for_status()
        result = resp.json()
        return result["content"][0]["text"]
    except Exception as e:
        print(f"❌ Claude API Error: {e}")
        return f"Analyse kon niet worden uitgevoerd: {str(e)}"

# ============================================================
# EMAIL
# ============================================================

EMAIL_HTML = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  
<div style="background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%); padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
  <h1 style="color: white; margin: 0;">🎯 Jouw vacature-analyse is klaar!</h1>
</div>

<div style="background: #f9f9f9; padding: 30px; border: 1px solid #ddd;">
  <p>Hoi {first_name},</p>
  <p>Bedankt voor het uploaden van je vacature voor <strong>{company}</strong>!</p>
  
  <div style="background: white; padding: 20px; margin: 20px 0; border-left: 4px solid #2d5a87; white-space: pre-wrap;">{analysis}</div>
  
  <div style="background: #1e3a5f; color: white; padding: 25px; border-radius: 8px; margin: 30px 0; text-align: center;">
    <h3 style="margin-top: 0;">Wil je meer halen uit je recruitment?</h3>
    <p>Plan een gratis adviesgesprek van 30 minuten:</p>
    
    <a href="https://calendly.com/wouter-arts-/vacature-analyse-advies" 
       style="display: inline-block; background: #27ae60; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; margin: 5px;">
      📅 Plan Adviesgesprek
    </a>
    
    <a href="https://wa.me/31614314593?text=Hoi%20Wouter,%20ik%20heb%20mijn%20vacature-analyse%20ontvangen" 
       style="display: inline-block; background: #25D366; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; margin: 5px;">
      💬 WhatsApp Direct
    </a>
  </div>
</div>

<div style="background: #1e3a5f; color: white; padding: 20px; border-radius: 0 0 10px 10px; text-align: center;">
  <p style="margin: 0;"><strong>Wouter Arts</strong> | Recruitin B.V.</p>
  <p style="margin: 5px 0; font-size: 14px;">📞 06-14314593 | 📧 wouter@recruitin.nl | 🌐 recruitin.nl</p>
</div>

</body>
</html>"""

def send_email(to_email: str, first_name: str, company: str, analysis: str) -> bool:
    """Send analysis email via Gmail SMTP"""
    if not GMAIL_APP_PASSWORD:
        print("⚠️ GMAIL_APP_PASSWORD not set, skipping email")
        return False
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🎯 Jouw verbeterde vacaturetekst voor {company} is klaar!"
    msg["From"] = GMAIL_USER
    msg["To"] = to_email
    
    html = EMAIL_HTML.format(
        first_name=first_name,
        company=company,
        analysis=analysis
    )
    
    msg.attach(MIMEText(html, "html"))
    
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

# ============================================================
# MAIN FLOW
# ============================================================

def process_submission(data: dict) -> dict:
    """Process complete Typeform submission"""
    print("=" * 60)
    print("📥 NEW SUBMISSION RECEIVED")
    print("=" * 60)
    
    # 1. Parse Typeform data
    submission = parse_typeform(data)
    print(f"✓ Parsed: {submission['first_name']} {submission['last_name']} ({submission['company']})")
    
    # 2. Create Pipedrive person
    full_name = f"{submission['first_name']} {submission['last_name']}".strip()
    person_id = create_person(
        name=full_name,
        email=submission['email'],
        phone=submission['phone'],
        org_name=submission['company']
    )
    print(f"✓ Pipedrive Person: ID {person_id}")
    
    # 3. Create Pipedrive deal
    deal_title = f"Vacature Analyse - {submission['company']}"
    deal_id = create_deal(
        title=deal_title,
        person_id=person_id,
        sector=submission['sector'],
        goal=submission['goal']
    )
    print(f"✓ Pipedrive Deal: ID {deal_id}")
    
    # 4. Download vacature file
    vacature_content = ""
    if submission['file_url']:
        vacature_content = download_file(submission['file_url'])
        print(f"✓ File downloaded: {len(vacature_content)} chars")
    else:
        vacature_content = "Geen vacaturetekst geüpload"
        print("⚠️ No file URL provided")
    
    # 5. Analyze with Claude
    print("⏳ Analyzing with Claude API...")
    analysis = analyze_vacature(
        vacature=vacature_content,
        company=submission['company'],
        sector=submission['sector'],
        goal=submission['goal']
    )
    print(f"✓ Analysis complete: {len(analysis)} chars")
    
    # 6. Add analysis as note to deal
    add_note(deal_id, f"📊 VACATURE ANALYSE\n\n{analysis}")
    print("✓ Note added to deal")
    
    # 7. Send email
    email_sent = send_email(
        to_email=submission['email'],
        first_name=submission['first_name'],
        company=submission['company'],
        analysis=analysis
    )
    print(f"✓ Email sent: {email_sent}")
    
    # 8. Update deal stage
    update_deal(deal_id, {"stage_id": 2})  # Move to next stage
    print("✓ Deal stage updated")
    
    print("=" * 60)
    print("✅ PROCESSING COMPLETE")
    print("=" * 60)
    
    return {
        "success": True,
        "person_id": person_id,
        "deal_id": deal_id,
        "email_sent": email_sent,
        "analysis_preview": analysis[:200] + "..."
    }

# ============================================================
# FLASK ROUTES
# ============================================================

@app.route("/", methods=["GET"])
def health():
    """Health check"""
    return jsonify({
        "status": "ok",
        "service": "kandidatentekort-automation",
        "timestamp": datetime.now().isoformat()
    })

@app.route("/webhook/typeform", methods=["POST"])
def typeform_webhook():
    """Receive Typeform webhook"""
    try:
        data = request.json
        result = process_submission(data)
        return jsonify(result), 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/test", methods=["GET"])
def test_flow():
    """Test with mock data"""
    mock_data = {
        "form_response": {
            "token": "test123",
            "submitted_at": datetime.now().isoformat(),
            "answers": [
                {"field": {"id": FIELDS["first_name"]}, "text": "Test"},
                {"field": {"id": FIELDS["last_name"]}, "text": "User"},
                {"field": {"id": FIELDS["email"]}, "email": "warts@recruitin.nl"},
                {"field": {"id": FIELDS["phone"]}, "phone_number": "+31614314593"},
                {"field": {"id": FIELDS["company"]}, "text": "Test BV"},
                {"field": {"id": FIELDS["sector"]}, "choice": {"label": "High-tech & Elektronica"}},
                {"field": {"id": FIELDS["goal"]}, "choice": {"label": "Meer sollicitanten"}},
                {"field": {"id": FIELDS["file"]}, "file_url": ""}
            ]
        }
    }
    
    result = process_submission(mock_data)
    return jsonify(result)

# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    print("🚀 Kandidatentekort Automation Server")
    print(f"📍 Running on port {PORT}")
    print(f"🔗 Webhook URL: http://localhost:{PORT}/webhook/typeform")
    print("")
    print("Environment:")
    print(f"  - ANTHROPIC_API_KEY: {'✓ Set' if ANTHROPIC_API_KEY else '✗ Missing'}")
    print(f"  - PIPEDRIVE_API_TOKEN: {'✓ Set' if PIPEDRIVE_API_TOKEN else '✗ Missing'}")
    print(f"  - GMAIL_APP_PASSWORD: {'✓ Set' if GMAIL_APP_PASSWORD else '✗ Missing'}")
    print("")
    
    app.run(host="0.0.0.0", port=PORT, debug=True)
