# CLAUDE CODE DEPLOYMENT INSTRUCTIONS
# ====================================
# Copy-paste deze commands in Claude Code

# ============================================================
# OPTIE 1: LOKAAL TESTEN MET NGROK
# ============================================================

# Step 1: Ga naar project folder
cd /Users/wouterarts/Projects/kandidatentekort-automation/autonomous-script

# Step 2: Maak virtual environment
python3 -m venv venv
source venv/bin/activate

# Step 3: Install dependencies
pip install -r requirements.txt

# Step 4: Maak .env file
cp .env.example .env
# EDIT .env met je API keys!

# Step 5: Run server
python kandidatentekort_auto.py

# Step 6: In NIEUWE terminal - start ngrok
ngrok http 8080

# Step 7: Kopieer ngrok URL (bijv: https://abc123.ngrok.io)
# Ga naar Typeform → kalFRTCA → Connect → Webhooks
# Voeg toe: https://abc123.ngrok.io/webhook/typeform

# Step 8: Test! Vul Typeform in, check terminal output

# ============================================================
# OPTIE 2: DEPLOY NAAR RENDER (PERMANENT)
# ============================================================

# Step 1: Maak GitHub repo
cd /Users/wouterarts/Projects/kandidatentekort-automation/autonomous-script
git init
git add .
git commit -m "Initial kandidatentekort automation"

# Step 2: Push naar GitHub
gh repo create kandidatentekort-automation --private --source=. --push

# Step 3: Ga naar https://render.com
# - Klik "New Web Service"
# - Connect GitHub repo
# - Environment: Python
# - Build: pip install -r requirements.txt
# - Start: gunicorn kandidatentekort_auto:app --bind 0.0.0.0:$PORT

# Step 4: Add Environment Variables in Render dashboard:
# - ANTHROPIC_API_KEY
# - PIPEDRIVE_API_TOKEN
# - GMAIL_USER
# - GMAIL_APP_PASSWORD

# Step 5: Deploy! Render geeft je URL (bijv: https://kandidatentekort-automation.onrender.com)

# Step 6: Ga naar Typeform → kalFRTCA → Connect → Webhooks
# Voeg toe: https://kandidatentekort-automation.onrender.com/webhook/typeform

# ============================================================
# TEST COMMANDS
# ============================================================

# Test health check:
curl http://localhost:8080/

# Test volledige flow (mock data):
curl http://localhost:8080/test

# Test met echte Typeform webhook (simulatie):
curl -X POST http://localhost:8080/webhook/typeform \
  -H "Content-Type: application/json" \
  -d '{
    "form_response": {
      "token": "test123",
      "submitted_at": "2025-11-25T04:00:00Z",
      "answers": [
        {"field": {"id": "field_rlWCM9qIDVnn"}, "text": "Wouter"},
        {"field": {"id": "field_q9xgrm7jnBIy"}, "text": "Arts"},
        {"field": {"id": "field_MnmHLBESIXfh"}, "email": "warts@recruitin.nl"},
        {"field": {"id": "field_1iZBbbmjqjEO"}, "phone_number": "+31614314593"},
        {"field": {"id": "field_oCk4xgomQr46"}, "text": "Test BV"},
        {"field": {"id": "field_MPI700TSOg7e"}, "choice": {"label": "High-tech"}},
        {"field": {"id": "field_btapXJRBLF0k"}, "choice": {"label": "Meer sollicitanten"}}
      ]
    }
  }'

# ============================================================
# TROUBLESHOOTING
# ============================================================

# Check logs:
tail -f /var/log/kandidatentekort.log

# Test Pipedrive connection:
curl "https://api.pipedrive.com/v1/users/me?api_token=57720aa8b264cb9060c9dd5af8ae0c096dbbebb5"

# Test Claude API:
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-sonnet-4-20250514","max_tokens":100,"messages":[{"role":"user","content":"Hi"}]}'
