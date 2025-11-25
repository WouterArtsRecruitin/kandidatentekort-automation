# 🤖 Kandidatentekort Autonomous Automation

**Volledig automatische vacature-analyse zonder Zapier**

```
TYPEFORM → PYTHON SCRIPT → PIPEDRIVE + CLAUDE + EMAIL
```

---

## 🚀 Quick Start (5 minuten)

### 1. Setup
```bash
cd /Users/wouterarts/Projects/kandidatentekort-automation/autonomous-script
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment
```bash
cp .env.example .env
# Edit .env met je API keys
```

### 3. Run
```bash
python kandidatentekort_auto.py
```

### 4. Test
```bash
curl http://localhost:8080/test
```

---

## 📁 Bestanden

| File | Beschrijving |
|------|--------------|
| `kandidatentekort_auto.py` | Main script |
| `requirements.txt` | Python dependencies |
| `.env.example` | Environment template |
| `render.yaml` | Render deployment config |
| `CLAUDE_CODE_COMMANDS.sh` | Copy-paste commands |

---

## 🔧 Environment Variables

| Variable | Beschrijving | Waar te vinden |
|----------|--------------|----------------|
| `ANTHROPIC_API_KEY` | Claude API | https://console.anthropic.com |
| `PIPEDRIVE_API_TOKEN` | Pipedrive API | Settings → Personal preferences → API |
| `GMAIL_USER` | Je Gmail adres | wouter@recruitin.nl |
| `GMAIL_APP_PASSWORD` | App-specifiek wachtwoord | https://myaccount.google.com/apppasswords |

---

## 🔗 Endpoints

| Route | Method | Beschrijving |
|-------|--------|--------------|
| `/` | GET | Health check |
| `/webhook/typeform` | POST | Typeform webhook receiver |
| `/test` | GET | Test met mock data |

---

## 📤 Typeform Webhook Setup

1. Ga naar https://admin.typeform.com
2. Open form `kalFRTCA`
3. Klik **Connect** → **Webhooks**
4. **Add webhook**:
   - URL: `https://jouw-server.com/webhook/typeform`
   - Enabled: ✓

---

## 🚀 Deploy Options

### Optie A: Lokaal + ngrok (Testen)
```bash
# Terminal 1
python kandidatentekort_auto.py

# Terminal 2  
ngrok http 8080
# → Geeft URL zoals https://abc123.ngrok.io
```

### Optie B: Render.com (Productie)
1. Push naar GitHub
2. Connect in Render dashboard
3. Add environment variables
4. Deploy!

### Optie C: Railway.app
```bash
railway login
railway init
railway up
```

---

## 📊 Flow

```
1. 📝 Typeform submission
         ↓
2. 🔔 Webhook → /webhook/typeform
         ↓
3. 👤 Create Pipedrive Person
         ↓
4. 💼 Create Pipedrive Deal (pipeline: vacature analyse)
         ↓
5. 📄 Download vacature file
         ↓
6. 🤖 Claude API analyse
         ↓
7. 📝 Add note to deal (analysis)
         ↓
8. 📧 Send email (HTML + Calendly + WhatsApp)
         ↓
9. ✅ Update deal stage
```

---

## 💰 Kosten

| Service | Kosten |
|---------|--------|
| Render Free Tier | €0 (750 uur/maand) |
| Claude API | ~€0.05 per analyse |
| **Per 100 leads** | **~€5** |

---

## 🔗 Links in Emails

- **Calendly:** https://calendly.com/wouter-arts-/vacature-analyse-advies
- **WhatsApp:** https://wa.me/31614314593

---

## 🆘 Troubleshooting

### Error: "ANTHROPIC_API_KEY not set"
→ Check `.env` file, restart server

### Error: "Gmail authentication failed"  
→ Maak App Password aan: https://myaccount.google.com/apppasswords

### Error: "Pipedrive 401"
→ Check API token, moet niet verlopen zijn

### Typeform webhook niet werkend
→ Check Typeform Webhooks logs voor errors

---

## 📞 Support

- WhatsApp: https://wa.me/31614314593
- Email: wouter@recruitin.nl

---

**Gemaakt:** 25 november 2025
**Status:** Production Ready 🟢
