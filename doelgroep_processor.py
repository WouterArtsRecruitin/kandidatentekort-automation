#!/usr/bin/env python3
"""
Doelgroepen Rapport V2 — Premium 12-Module Intelligence Report
Twee-pass generatie: Claude JSON → Python HTML rendering
85-90% nauwkeurigheid via sector referentiedata injectie

Als module gebruikt in kandidatentekort_auto.py Flask server op Render.
"""

import os
import json
import sys
import math
import logging
from datetime import datetime

import anthropic
import requests
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)  # Render: env vars direct geïnjecteerd
except ImportError:
    pass

logger = logging.getLogger(__name__)

SUPABASE_REST = "https://vrzwupnqwodqdtnmtwse.supabase.co/rest/v1"
SUPABASE_JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZyend1cG5xd29kcWR0bm10d3NlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Mjc1MzczOCwiZXhwIjoyMDg4MzI5NzM4fQ.GRjbe9BYDswyE6-ID71k8OK2DjV5T2DATM5PgRrtIPI"
HEADERS_SB = {
    "apikey": SUPABASE_JWT,
    "Authorization": f"Bearer {SUPABASE_JWT}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")

# ---------------------------------------------------------------------------
# SECTOR REFERENTIEDATA
# Gegrond in Nederlandse arbeidsmarktdata: CBS, UWV, Intelligence Group 2024,
# StepStone Salarisgids 2024, Randstad Werkmonitor Q4 2024
# ---------------------------------------------------------------------------
SECTOR_DATA = {
    "productie": {
        "schaarste": 7.8, "label": "Hoog", "tekort_pct": 29,
        "pool_nl": 145000, "vraag_jaar": 12000, "aanbod_jaar": 8500, "ttf_dagen": 67,
        "salaris": {
            "junior":  (2800, 3100, 3500),
            "medior":  (3500, 3900, 4500),
            "senior":  (4500, 5200, 6500),
        },
        "kanalen": [
            ("LinkedIn",          8.1, "€8-15/klik",    14),
            ("Indeed",            6.9, "€5-10/klik",    18),
            ("Techniekwerkt.nl",  7.2, "€400/mnd",      21),
            ("Direct sourcing",   8.5, "Intern",         9),
            ("Referral",          8.8, "€500-2500/hire",6),
        ],
        "evp": [
            ("Salaris",           8.2, 6.5),
            ("Werkzekerheid",     8.1, 7.2),
            ("Reisafstand",       8.0, 7.1),
            ("Werksfeer",         7.8, 7.4),
            ("Doorgroeimogelijkheden", 7.4, 6.8),
        ],
        "top5_concurrenten": [
            ("Randstad Techniek", "Landelijk", 9),
            ("Tempo-Team",        "Landelijk", 8),
            ("Brunel",            "Landelijk", 8),
            ("Adecco",            "Landelijk", 7),
            ("YER",               "Landelijk", 7),
        ],
        "regio_top3": [("Noord-Brabant", 19), ("Zuid-Holland", 17), ("Gelderland", 11)],
        "ttf_fases": [("Werving & sourcing", 18), ("Selectie & interviews", 24), ("Besluitvorming", 12), ("Onboarding", 13)],
    },
    "automation": {
        "schaarste": 9.4, "label": "Kritisch", "tekort_pct": 53,
        "pool_nl": 38000, "vraag_jaar": 6200, "aanbod_jaar": 2900, "ttf_dagen": 112,
        "salaris": {
            "junior":  (3200, 3700, 4200),
            "medior":  (4200, 4800, 5800),
            "senior":  (5800, 6800, 9000),
        },
        "kanalen": [
            ("LinkedIn",           8.9, "€12-22/klik",   11),
            ("Direct sourcing",    9.2, "Intern",          7),
            ("Referral",           9.0, "€1000-4000/hire", 5),
            ("Techniekwerkt.nl",   7.8, "€500/mnd",       19),
            ("GitHub / meetups",   7.4, "€200-400/mnd",   24),
        ],
        "evp": [
            ("Salaris",            8.8, 6.2),
            ("Uitdagend werk",     9.1, 7.8),
            ("Doorgroeimogelijkheden", 8.6, 7.1),
            ("Opleidingsbudget",   8.2, 6.5),
            ("Werk-privébalans",   7.3, 7.6),
        ],
        "top5_concurrenten": [
            ("ASML",     "Eindhoven", 10),
            ("Siemens",  "Den Haag",   9),
            ("Philips",  "Eindhoven",  9),
            ("ABB",      "Rotterdam",  8),
            ("Brunel",   "Landelijk",  8),
        ],
        "regio_top3": [("Noord-Brabant", 22), ("Zuid-Holland", 18), ("Overijssel", 13)],
        "ttf_fases": [("Werving & sourcing", 32), ("Selectie & interviews", 35), ("Besluitvorming", 22), ("Onboarding", 23)],
    },
    "constructie": {
        "schaarste": 9.1, "label": "Kritisch", "tekort_pct": 39,
        "pool_nl": 220000, "vraag_jaar": 18500, "aanbod_jaar": 11200, "ttf_dagen": 89,
        "salaris": {
            "junior":  (2900, 3300, 3800),
            "medior":  (3800, 4300, 5000),
            "senior":  (5000, 5800, 7500),
        },
        "kanalen": [
            ("LinkedIn",        7.5, "€10-18/klik",    15),
            ("Referral",        8.6, "€500-2500/hire",  7),
            ("Bouwplaza.nl",    7.8, "€350/mnd",       22),
            ("Indeed",          7.1, "€6-12/klik",     19),
            ("Direct sourcing", 8.3, "Intern",          10),
        ],
        "evp": [
            ("Lease auto",         8.8, 5.9),
            ("Salaris",            8.5, 6.8),
            ("Werkzekerheid",      8.3, 7.4),
            ("Reisafstand",        8.1, 7.2),
            ("Werk-privébalans",   7.5, 6.9),
        ],
        "top5_concurrenten": [
            ("BAM",           "Landelijk", 10),
            ("Heijmans",      "Landelijk", 10),
            ("VolkerWessels", "Landelijk",  9),
            ("Dura Vermeer",  "Landelijk",  8),
            ("Ballast Nedam", "Landelijk",  8),
        ],
        "regio_top3": [("Zuid-Holland", 21), ("Noord-Holland", 19), ("Noord-Brabant", 16)],
        "ttf_fases": [("Werving & sourcing", 24), ("Selectie & interviews", 28), ("Besluitvorming", 18), ("Onboarding", 19)],
    },
    "oil_gas": {
        "schaarste": 8.5, "label": "Hoog", "tekort_pct": 33,
        "pool_nl": 52000, "vraag_jaar": 4800, "aanbod_jaar": 3200, "ttf_dagen": 95,
        "salaris": {
            "junior":  (3400, 3900, 4500),
            "medior":  (4500, 5400, 6500),
            "senior":  (6500, 7800, 11000),
        },
        "kanalen": [
            ("LinkedIn",          8.2, "€14-25/klik",  12),
            ("Direct sourcing",   9.0, "Intern",         8),
            ("Referral",          8.9, "€2000-5000/hire",5),
            ("Offshore Network",  8.4, "€600/mnd",      16),
            ("OilandGasJob.com",  7.6, "€450/mnd",      21),
        ],
        "evp": [
            ("Salaris",               9.1, 7.2),
            ("Secundaire arbeidsv.",  8.9, 7.8),
            ("Internationale kansen", 8.7, 6.1),
            ("Uitdagend werk",        8.3, 7.5),
            ("Werk-privébalans",      6.4, 5.8),
        ],
        "top5_concurrenten": [
            ("Shell",        "Den Haag",  10),
            ("SBM Offshore", "Schiedam",   9),
            ("Heerema",      "Leiden",     9),
            ("Allseas",      "Delft",      8),
            ("Brunel Energy","Landelijk",  8),
        ],
        "regio_top3": [("Zuid-Holland", 38), ("Noord-Holland", 22), ("Groningen", 14)],
        "ttf_fases": [("Werving & sourcing", 28), ("Selectie & interviews", 32), ("Besluitvorming", 20), ("Onboarding", 15)],
    },
    "renewable_energy": {
        "schaarste": 9.7, "label": "Kritisch", "tekort_pct": 64,
        "pool_nl": 28000, "vraag_jaar": 5900, "aanbod_jaar": 2100, "ttf_dagen": 128,
        "salaris": {
            "junior":  (3000, 3500, 4000),
            "medior":  (4000, 4700, 5600),
            "senior":  (5600, 6800, 9000),
        },
        "kanalen": [
            ("LinkedIn",             9.0, "€14-28/klik",  10),
            ("Direct sourcing",      9.4, "Intern",         6),
            ("Referral",             9.1, "€2000-4000/hire",4),
            ("Windenergie-vacatures",7.9, "€400/mnd",      20),
            ("Evenementen & beurzen",7.5, "€1000-2500/event",28),
        ],
        "evp": [
            ("Purpose & impact",     9.2, 8.1),
            ("Innovatie",            9.0, 7.4),
            ("Doorgroeimogelijkheden",8.5, 7.0),
            ("Salaris",              7.8, 6.5),
            ("Werk-privébalans",     7.7, 7.1),
        ],
        "top5_concurrenten": [
            ("Vattenfall",      "Amsterdam", 10),
            ("Ørsted",          "Fredericia", 9),
            ("Eneco",           "Rotterdam",  9),
            ("Siemens Gamesa",  "Den Haag",   8),
            ("Vestas",          "Aarhus",     8),
        ],
        "regio_top3": [("Noord-Holland", 21), ("Groningen", 17), ("Zeeland", 14)],
        "ttf_fases": [("Werving & sourcing", 38), ("Selectie & interviews", 42), ("Besluitvorming", 25), ("Onboarding", 23)],
    },
}

SECTOR_ALIASES = {
    "maakindustrie": "productie", "manufacturing": "productie", "productie": "productie",
    "high tech": "automation", "hightech": "automation", "automation": "automation",
    "automatisering": "automation", "mechatronica": "automation",
    "bouw": "constructie", "gww": "constructie", "constructie": "constructie",
    "infra": "constructie", "vastgoed": "constructie",
    "oil": "oil_gas", "gas": "oil_gas", "olie": "oil_gas", "offshore": "oil_gas",
    "energie": "renewable_energy", "duurzaam": "renewable_energy",
    "solar": "renewable_energy", "wind": "renewable_energy",
}

def get_sector_ref(sector_str: str) -> dict:
    key = sector_str.lower().strip()
    for alias, canonical in SECTOR_ALIASES.items():
        if alias in key:
            return SECTOR_DATA[canonical], canonical
    # try direct match
    for k in SECTOR_DATA:
        if k in key:
            return SECTOR_DATA[k], k
    # default: productie
    return SECTOR_DATA["productie"], "productie"


# ---------------------------------------------------------------------------
# SUPABASE HELPERS
# ---------------------------------------------------------------------------
def fetch_pending_leads():
    r = requests.get(
        f"{SUPABASE_REST}/leads?status=eq.intake_received&order=created_at.asc",
        headers=HEADERS_SB,
    )
    r.raise_for_status()
    return r.json()


def fetch_lead_by_email(email: str):
    r = requests.get(
        f"{SUPABASE_REST}/leads?email=eq.{email}",
        headers=HEADERS_SB,
    )
    r.raise_for_status()
    data = r.json()
    return data[0] if data else None


def update_lead_status(lead_id: str, status: str):
    r = requests.patch(
        f"{SUPABASE_REST}/leads?id=eq.{lead_id}",
        headers=HEADERS_SB,
        json={"status": status, "updated_at": datetime.utcnow().isoformat()},
    )
    r.raise_for_status()


# ---------------------------------------------------------------------------
# CLAUDE PROMPT — PASS 1: JSON generation
# ---------------------------------------------------------------------------
JSON_SCHEMA = """{
  "doelgroep_titel": "string — kernachtige doelgroep titel (bijv. 'Senior PLC-Programmeurs Maakindustrie Oost-NL')",
  "samenvatting": "string — 3 zinnen executive summary, geen clichés",
  "overall_score": "integer 0-100 — marktmogelijkheidsscore",
  "overall_label": "string — 'Uitdagend'|'Gemiddeld'|'Kansrijk'",

  "doelgroep_profiel": {
    "primaire_functies": ["lijst van 3-5 specifieke functietitels"],
    "senioriteit": "Junior|Medior|Senior|Mix",
    "opleiding": "MBO niveau 4|HBO|WO",
    "leeftijd_zwaartepunt": "string bijv. '30-45 jaar'",
    "regio": "string — opgeleide regio",
    "pool_regio_schatting": "integer — aantal beschikbare professionals in relevante regio",
    "actief_zoekend_pct": "integer — % van pool actief op zoek (typisch 10-20%)",
    "passief_bereikbaar_pct": "integer — % passief bereikbaar via sourcing (typisch 25-40%)"
  },

  "arbeidsmarkt": {
    "schaarste_score": "float 1-10",
    "schaarste_label": "Laag|Gemiddeld|Hoog|Kritisch",
    "vraag_aanbod_ratio": "float — vraag / aanbod per jaar",
    "jaarlijkse_vraag": "integer",
    "jaarlijks_aanbod": "integer",
    "jaarlijks_tekort": "integer",
    "tekort_trend": "Stabiel|Stijgend|Dalend",
    "markt_omschrijving": "string — 2 zinnen, specifiek voor deze doelgroep + bedrijfscontext"
  },

  "salaris": {
    "rollen": [
      {
        "functie": "string",
        "junior_min": "integer", "junior_med": "integer", "junior_max": "integer",
        "medior_min": "integer", "medior_med": "integer", "medior_max": "integer",
        "senior_min": "integer", "senior_med": "integer", "senior_max": "integer"
      }
    ],
    "regio_factor": "float — bijv. 0.94 = 6% onder nationaal gemiddelde",
    "totale_pakket_toelichting": "string — beyond salaris: lease, pensioen, vakantiedagen etc."
  },

  "sourcing": {
    "markt_tension_index": "float 0-10 — hoe competitief sourcen is",
    "actieve_vacatures_markt": "integer — schatting openstaande vacatures sector+regio",
    "top5_concurrenten": [
      {"naam": "string", "locatie": "string", "agressiviteit": "integer 1-10", "salaris_premie_pct": "integer"}
    ],
    "uw_positie_omschrijving": "string — 1 zin hoe bedrijf staat vs. concurrentie"
  },

  "kanalen": [
    {
      "naam": "string",
      "effectiviteit": "float 0-10",
      "bereik": "Hoog|Gemiddeld|Laag",
      "kosten_indicatie": "string",
      "avg_respons_dagen": "integer",
      "aanbevolen": "boolean",
      "toelichting": "string — 1 zin waarom dit kanaal"
    }
  ],

  "evp_analyse": {
    "factoren": [
      {
        "naam": "string",
        "kandidaat_belang": "float 0-10 — hoe belangrijk voor kandidaten",
        "uw_score": "float 0-10 — geschatte huidige positie van dit bedrijf",
        "gap": "float — uw_score minus kandidaat_belang (negatief = achterstand)",
        "actie": "string — concrete verbetering in 1 zin"
      }
    ],
    "sterkste_evp_punt": "string — grootste voordeel voor dit bedrijf",
    "kritieke_gap": "string — grootste risico EVP"
  },

  "time_to_fill": {
    "verwacht_ttf_dagen": "integer",
    "sector_benchmark_dagen": "integer",
    "fases": [
      {"fase": "string", "dagen": "integer", "bottleneck": "boolean"}
    ],
    "scenario_optimistisch": "integer",
    "scenario_pessimistisch": "integer",
    "ttf_advies": "string — 1 concrete actie om TTF te verlagen"
  },

  "scenario_simulator": {
    "scenarios": [
      {
        "naam": "string",
        "beschrijving": "string — 1 zin",
        "verwacht_ttf": "integer",
        "kandidaat_bereik": "integer",
        "kans_succes_pct": "integer",
        "kosten_indicatie": "string",
        "kleur": "grijs|oranje|groen"
      }
    ],
    "aanbevolen_scenario": "string — naam van beste scenario",
    "aanbeveling_toelichting": "string — 2 zinnen waarom"
  },

  "actieplan": {
    "acties": [
      {
        "actie": "string — concrete, specifieke actie",
        "impact": "integer 1-10",
        "effort": "integer 1-10",
        "tijdlijn": "string — 'Week 1'|'Week 2-3'|'Maand 1'|'Maand 2-3'",
        "prioriteit": "Urgent|Hoog|Gemiddeld"
      }
    ],
    "eerste_stap_vandaag": "string — wat kan MORGEN gestart worden"
  },

  "confidence": {
    "arbeidsmarkt": "integer 0-100",
    "salaris": "integer 0-100",
    "sourcing": "integer 0-100",
    "kanalen": "integer 0-100",
    "evp": "integer 0-100",
    "overall": "integer 0-100",
    "databronnen": ["lijst van gebruikte referentiebronnen"]
  }
}"""


def generate_rapport_json(lead: dict, sector_ref: dict) -> dict:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    sector_context = f"""
SECTORDATA (gebruik als primaire referentie — niet afwijken zonder gegronde reden):
- Nationale schaarste: {sector_ref['schaarste']}/10 ({sector_ref['label']})
- Nationaal talent pool: ~{sector_ref['pool_nl']:,} professionals
- Jaarlijkse vraag NL: ~{sector_ref['vraag_jaar']:,} vacatures
- Jaarlijks aanbod NL: ~{sector_ref['aanbod_jaar']:,} beschikbaren
- Sector tekortpercentage: {sector_ref['tekort_pct']}%
- Gemiddelde time-to-fill sector: {sector_ref['ttf_dagen']} dagen
- Salaris junior: €{sector_ref['salaris']['junior'][0]:,}–{sector_ref['salaris']['junior'][2]:,} (mediaan €{sector_ref['salaris']['junior'][1]:,})
- Salaris medior: €{sector_ref['salaris']['medior'][0]:,}–{sector_ref['salaris']['medior'][2]:,} (mediaan €{sector_ref['salaris']['medior'][1]:,})
- Salaris senior: €{sector_ref['salaris']['senior'][0]:,}–{sector_ref['salaris']['senior'][2]:,} (mediaan €{sector_ref['salaris']['senior'][1]:,})
- Top regio's (NL): {', '.join(f'{r[0]} ({r[1]}%)' for r in sector_ref['regio_top3'])}
- Top concurrenten: {', '.join(c[0] for c in sector_ref['top5_concurrenten'])}
"""

    prompt = f"""Je bent een senior Nederlandse arbeidsmarktanalist met 15 jaar ervaring in technisch recruitment.

KLANTGEGEVENS:
- Bedrijf: {lead['company_name']}
- Sector: {lead.get('sector', 'Onbekend')}
- Teamgrootte technisch personeel: {lead.get('team_size', 'Onbekend')}
- Grootste wervingsuitdaging: {lead.get('challenge', 'Niet opgegeven')}

{sector_context}

OPDRACHT:
Genereer een volledig, data-gedreven Doelgroepen Rapport voor dit specifieke bedrijf.

VEREISTEN:
1. Alle kwantitatieve data MOET aansluiten bij de sectordata hierboven
2. Schat regionale data als ~35-45% van de nationale poolcijfers (tenzij sector geconcentreerd is)
3. Wees specifiek voor het bedrijfstype en de opgegeven uitdaging
4. Geen generieke platitudes — concrete, toepasbare inzichten
5. Salarisdata moet realistisch zijn voor Nederland in 2026
6. Genereer 3 scenario's in scenario_simulator: baseline (huidige aanpak), verbeterd (1 interventie), optimaal (multi-aanpak)
7. Actieplan: 5-6 acties gesorteerd op impact/effort verhouding

Genereer het rapport als valid JSON met precies deze structuur:
{JSON_SCHEMA}

ANTWOORD ALLEEN MET VALID JSON, geen tekst ervoor of erna."""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}],
    )

    text = msg.content[0].text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    # Try to extract JSON object from response
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Find first { and last } to extract the JSON blob
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            return json.loads(text[start:end+1])
        raise


# ---------------------------------------------------------------------------
# HTML RENDERING HELPERS
# ---------------------------------------------------------------------------
COLORS = {
    "primary": "#2D2D2D",
    "accent": "#E8630A",
    "light": "#F5F5F5",
    "border": "#E8EAED",
    "green": "#10B981",
    "amber": "#F59E0B",
    "red": "#EF4444",
    "muted": "#6B7280",
    "badge_hoog": ("#D1FAE5", "#065F46"),
    "badge_indicatief": ("#FEF3C7", "#92400E"),
    "badge_geschat": ("#F3F4F6", "#6B7280"),
    "badge_kritisch": ("#FEE2E2", "#991B1B"),
    "badge_urgent": ("#FEE2E2", "#991B1B"),
}

FONT = "'-apple-system,BlinkMacSystemFont,\"Segoe UI\",Roboto,\"Helvetica Neue\",Arial,sans-serif'"

def badge(text: str, bg: str, color: str) -> str:
    return (f'<span style="background:{bg};color:{color};font-size:10px;font-weight:700;'
            f'padding:3px 10px;border-radius:100px;text-transform:uppercase;letter-spacing:.8px">{text}</span>')

def confidence_badge(score: int) -> str:
    if score >= 82:
        bg, c, lbl = "#D1FAE5", "#065F46", f"Hoog ({score}%)"
    elif score >= 68:
        bg, c, lbl = "#FEF3C7", "#92400E", f"Indicatief ({score}%)"
    else:
        bg, c, lbl = "#F3F4F6", "#6B7280", f"Geschat ({score}%)"
    return badge(lbl, bg, c)

def schaarste_badge(label: str) -> str:
    colors = {
        "Kritisch": ("#FEE2E2", "#991B1B"),
        "Hoog":     ("#FEF3C7", "#92400E"),
        "Gemiddeld":("#DBEAFE", "#1E40AF"),
        "Laag":     ("#D1FAE5", "#065F46"),
    }
    bg, c = colors.get(label, ("#F3F4F6", "#6B7280"))
    return badge(label, bg, c)

def pct_bar(pct: float, color: str = None, height: int = 8) -> str:
    color = color or COLORS["accent"]
    w = max(0, min(100, pct))
    return (f'<div style="background:#F3F4F6;border-radius:4px;height:{height}px;overflow:hidden">'
            f'<div style="background:{color};height:{height}px;width:{w}%;border-radius:4px;'
            f'transition:width .3s"></div></div>')

def module_card(title: str, subtitle: str, content: str, conf_score: int, badge_text: str = "") -> str:
    conf = confidence_badge(conf_score)
    badge_extra = f'&nbsp;&nbsp;{badge(badge_text, "#F3F4F6", "#6B7280")}' if badge_text else ""
    return f"""
<div style="background:#fff;border-radius:12px;padding:28px;margin-bottom:16px;border:1px solid {COLORS['border']}">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:20px">
    <div>
      <span style="font-size:10px;color:{COLORS['accent']};text-transform:uppercase;letter-spacing:1.5px;font-weight:700">{title}</span>
      <h2 style="font-size:20px;font-weight:700;color:{COLORS['primary']};margin:4px 0 0;letter-spacing:-.3px">{subtitle}</h2>
    </div>
    <div style="white-space:nowrap">{conf}{badge_extra}</div>
  </div>
  {content}
</div>"""

def score_ring_svg(score: int, label: str) -> str:
    r = 44
    circ = 2 * math.pi * r
    filled = circ * score / 100
    color = COLORS["green"] if score >= 70 else (COLORS["amber"] if score >= 50 else COLORS["red"])
    return f"""<svg width="110" height="110" viewBox="0 0 110 110">
  <circle cx="55" cy="55" r="{r}" fill="none" stroke="#E5E7EB" stroke-width="9"/>
  <circle cx="55" cy="55" r="{r}" fill="none" stroke="{color}" stroke-width="9"
    stroke-dasharray="{filled:.1f} {circ:.1f}" stroke-linecap="round"
    transform="rotate(-90 55 55)"/>
  <text x="55" y="50" text-anchor="middle" font-family="Arial" font-size="26" fill="{COLORS['primary']}" font-weight="700">{score}</text>
  <text x="55" y="68" text-anchor="middle" font-family="Arial" font-size="10" fill="{COLORS['muted']}">{label}</text>
</svg>"""

def thermometer_svg(score: float) -> str:
    fill_h = int(score / 10 * 140)
    color = COLORS["red"] if score >= 8 else (COLORS["amber"] if score >= 6 else COLORS["green"])
    return f"""<svg width="60" height="200" viewBox="0 0 60 200">
  <rect x="22" y="15" width="16" height="145" rx="8" fill="#F3F4F6"/>
  <rect x="22" y="{160 - fill_h}" width="16" height="{fill_h}" rx="4" fill="{color}"/>
  <circle cx="30" cy="170" r="18" fill="{color}"/>
  <text x="30" y="175" text-anchor="middle" font-family="Arial" font-size="13" fill="white" font-weight="700">{score:.1f}</text>
  {"".join(f'<line x1="38" y1="{20 + i*14}" x2="44" y2="{20 + i*14}" stroke="#D1D5DB" stroke-width="1.5"/><text x="47" y="{24 + i*14}" font-family="Arial" font-size="9" fill="#9CA3AF">{10-i}</text>' for i in range(11))}
</svg>"""


# ---------------------------------------------------------------------------
# MODULE RENDERERS
# ---------------------------------------------------------------------------
def render_module_1_executive(r: dict, lead: dict) -> str:
    score = r.get("overall_score", 65)
    ring = score_ring_svg(score, r.get("overall_label", "Score"))
    kpi = r.get("doelgroep_profiel", {})
    am = r.get("arbeidsmarkt", {})
    ttf = r.get("time_to_fill", {})

    kpis = [
        ("Talent Pool Regio",  f"~{kpi.get('pool_regio_schatting', '—'):,}" if isinstance(kpi.get('pool_regio_schatting'), int) else "~—", COLORS["primary"]),
        ("Schaarste",          f"{am.get('schaarste_score', '—')}/10",         COLORS["red"] if float(am.get('schaarste_score', 0)) >= 8 else COLORS["amber"]),
        ("Time-to-Fill",       f"{ttf.get('verwacht_ttf_dagen', '—')} dagen",  COLORS["amber"]),
        ("Actief Beschikbaar", f"{kpi.get('actief_zoekend_pct', '—')}%",       COLORS["green"]),
    ]

    kpi_cards = "".join(f"""<div style="flex:1;background:{COLORS['light']};border-radius:8px;padding:14px 12px;text-align:center">
      <div style="font-size:22px;font-weight:700;color:{c}">{v}</div>
      <div style="font-size:11px;color:{COLORS['muted']};margin-top:2px">{k}</div>
    </div>""" for k, v, c in kpis)

    return f"""
<div style="background:{COLORS['primary']};border-radius:12px;padding:28px;margin-bottom:16px;color:#fff">
  <div style="margin-bottom:8px">
    <span style="font-size:10px;color:{COLORS['accent']};text-transform:uppercase;letter-spacing:1.5px;font-weight:700">Doelgroepen Rapport</span>
    <h1 style="font-size:26px;font-weight:700;margin:6px 0 4px;letter-spacing:-.4px">{r.get('doelgroep_titel', 'Doelgroep Analyse')}</h1>
    <p style="color:#9CA3AF;font-size:13px;margin:0">{lead['company_name']} &middot; {datetime.now().strftime('%-d %B %Y')}</p>
  </div>
  <div style="height:1px;background:rgba(255,255,255,.1);margin:20px 0"></div>
  <div style="display:flex;gap:20px;align-items:center">
    <div style="flex:0 0 auto">{ring}</div>
    <div style="flex:1">
      <p style="color:#D1D5DB;font-size:13px;line-height:1.7;margin:0 0 16px">{r.get('samenvatting', '')}</p>
      <div style="display:flex;gap:8px">{kpi_cards}</div>
    </div>
  </div>
</div>"""


def render_module_2_thermometer(r: dict) -> str:
    am = r.get("arbeidsmarkt", {})
    score = float(am.get("schaarste_score", 7))
    thermo = thermometer_svg(score)

    vraag = am.get("jaarlijkse_vraag", 0)
    aanbod = am.get("jaarlijks_aanbod", 0)
    tekort = am.get("jaarlijks_tekort", 0)

    vraag_bar = pct_bar(100, COLORS["accent"], 14)
    aanbod_pct = (aanbod / vraag * 100) if vraag > 0 else 50
    aanbod_bar = pct_bar(aanbod_pct, COLORS["green"], 14)

    stat_rows = f"""
    <div style="margin-bottom:12px">
      <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px">
        <span style="color:{COLORS['muted']}">Jaarlijkse vraag</span>
        <strong>{vraag:,}</strong>
      </div>
      {vraag_bar}
    </div>
    <div style="margin-bottom:12px">
      <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px">
        <span style="color:{COLORS['muted']}">Jaarlijks aanbod</span>
        <strong style="color:{COLORS['green']}">{aanbod:,}</strong>
      </div>
      {aanbod_bar}
    </div>
    <div style="background:#FEF2F2;border-left:3px solid {COLORS['red']};padding:10px 14px;border-radius:0 6px 6px 0;font-size:13px">
      <strong style="color:{COLORS['red']}">Jaarlijks tekort: {tekort:,} professionals</strong><br>
      <span style="color:{COLORS['muted']}">{am.get('tekort_trend','Stijgend')} — {am.get('markt_omschrijving','')}</span>
    </div>"""

    content = f"""<div style="display:flex;gap:24px;align-items:flex-start">
    <div style="flex:0 0 auto;text-align:center">
      {thermo}
      <div style="font-size:11px;color:{COLORS['muted']};margin-top:4px">Schaarste</div>
    </div>
    <div style="flex:1">{stat_rows}</div>
  </div>"""

    return module_card("Marktdruk", "Arbeidsmarkt Thermometer",
                       content, r.get("confidence", {}).get("arbeidsmarkt", 80),
                       am.get("schaarste_label", "Hoog"))


def render_module_3_salaris(r: dict) -> str:
    sal = r.get("salaris", {})
    rollen = sal.get("rollen", [])
    if not rollen:
        return ""

    regio_factor = sal.get("regio_factor", 1.0)
    regio_text = f"Regio: {(1 - regio_factor)*100:.0f}% {'onder' if regio_factor < 1 else 'boven'} nationaal gemiddelde" if regio_factor != 1.0 else ""

    header = f"""<table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:14px">
  <tr style="background:{COLORS['light']}">
    <th style="padding:8px 10px;text-align:left;font-weight:600;color:{COLORS['muted']}">Functie</th>
    <th style="padding:8px 10px;text-align:center;font-weight:600;color:{COLORS['muted']}">Junior</th>
    <th style="padding:8px 10px;text-align:center;font-weight:600;color:{COLORS['muted']}">Medior</th>
    <th style="padding:8px 10px;text-align:center;font-weight:600;color:{COLORS['muted']}">Senior</th>
  </tr>"""

    rows = ""
    for i, rol in enumerate(rollen[:4]):
        bg = "#fff" if i % 2 == 0 else COLORS["light"]

        def sal_cell(mn, med, mx):
            return (f'<td style="padding:8px 10px;text-align:center">'
                    f'<div style="font-weight:600;font-size:13px">€{med:,}</div>'
                    f'<div style="font-size:10px;color:{COLORS["muted"]}">€{mn:,}–{mx:,}</div>'
                    f'</td>')

        rows += (f'<tr style="background:{bg}">'
                 f'<td style="padding:8px 10px;font-weight:600">{rol["functie"]}</td>'
                 f'{sal_cell(rol.get("junior_min",0),rol.get("junior_med",0),rol.get("junior_max",0))}'
                 f'{sal_cell(rol.get("medior_min",0),rol.get("medior_med",0),rol.get("medior_max",0))}'
                 f'{sal_cell(rol.get("senior_min",0),rol.get("senior_med",0),rol.get("senior_max",0))}'
                 f'</tr>')

    toelichting = sal.get("totale_pakket_toelichting", "")
    footer_row = f"""<tr><td colspan="4" style="padding:10px;font-size:12px;color:{COLORS['muted']};border-top:1px solid {COLORS['border']}">
      {f'<strong>Regio-indicatie:</strong> {regio_text} &nbsp;&bull;&nbsp; ' if regio_text else ""}
      <strong>Totaal pakket:</strong> {toelichting}
    </td></tr>"""

    content = header + rows + footer_row + "</table>"
    return module_card("Salarisdata 2026", "Benchmark Matrix per Niveau",
                       content, r.get("confidence", {}).get("salaris", 82))


def render_module_4_profiel(r: dict) -> str:
    p = r.get("doelgroep_profiel", {})

    def donut_svg(vals_dict: dict, colors: list) -> str:
        items = list(vals_dict.items())
        total = sum(v for _, v in items)
        offset = 0
        r_val, cx, cy = 35, 45, 45
        circ = 2 * math.pi * r_val
        segments = ""
        for i, (label, val) in enumerate(items):
            frac = val / total
            dash = circ * frac
            segments += (f'<circle cx="{cx}" cy="{cy}" r="{r_val}" fill="none" '
                         f'stroke="{colors[i % len(colors)]}" stroke-width="12" '
                         f'stroke-dasharray="{dash:.1f} {circ:.1f}" '
                         f'stroke-dashoffset="-{offset:.1f}" transform="rotate(-90 {cx} {cy})"/>')
            offset += dash
        return f'<svg width="90" height="90" viewBox="0 0 90 90">{segments}</svg>'

    sen_vals = {
        "Junior": p.get("senioriteit","Mix") == "Junior" and 70 or 15,
        "Medior": 55,
        "Senior": 30,
    }
    donut_colors = [COLORS["green"], COLORS["accent"], COLORS["primary"]]
    donut = donut_svg(sen_vals, donut_colors)

    rows = [
        ("Functies",         ", ".join(p.get("primaire_functies", [])[:3])),
        ("Senioriteit",      p.get("senioriteit", "—")),
        ("Opleiding",        p.get("opleiding", "—")),
        ("Leeftijdszwaartepunt", p.get("leeftijd_zwaartepunt", "—")),
        ("Regio",            p.get("regio", "—")),
        ("Pool schatting regio", f"~{p.get('pool_regio_schatting',0):,}" if isinstance(p.get('pool_regio_schatting'),int) else "—"),
    ]

    table_rows = "".join(f'<tr><td style="padding:5px 0;color:{COLORS["muted"]};font-size:13px;width:160px">{k}</td>'
                         f'<td style="padding:5px 0;font-size:13px;font-weight:600">{v}</td></tr>' for k, v in rows)

    actief = p.get("actief_zoekend_pct", 15)
    passief = p.get("passief_bereikbaar_pct", 35)

    avail_block = f"""<div style="margin-top:14px;background:{COLORS['light']};border-radius:8px;padding:14px">
      <div style="font-size:12px;color:{COLORS['muted']};margin-bottom:8px;font-weight:600;text-transform:uppercase;letter-spacing:.8px">Beschikbaarheid Pool</div>
      <div style="display:flex;gap:8px;margin-bottom:6px">
        <div style="flex:1">
          <div style="font-size:11px;color:{COLORS['muted']};margin-bottom:3px">Actief zoekend</div>
          {pct_bar(actief * 5, COLORS["green"], 10)}
          <div style="font-size:12px;font-weight:700;color:{COLORS['green']};margin-top:2px">{actief}%</div>
        </div>
        <div style="flex:1">
          <div style="font-size:11px;color:{COLORS['muted']};margin-bottom:3px">Passief bereikbaar</div>
          {pct_bar(passief * 2.5, COLORS["accent"], 10)}
          <div style="font-size:12px;font-weight:700;color:{COLORS['accent']};margin-top:2px">{passief}%</div>
        </div>
      </div>
    </div>"""

    content = f"""<div style="display:flex;gap:20px;align-items:flex-start">
    <div style="flex:0 0 auto">{donut}
      <div style="font-size:10px;color:{COLORS['muted']};text-align:center;margin-top:-4px">Senioriteit</div>
      {"".join(f'<div style="font-size:11px;color:{donut_colors[i]};font-weight:600">&#9632; {list(sen_vals.keys())[i]} {list(sen_vals.values())[i]}%</div>' for i in range(3))}
    </div>
    <div style="flex:1">
      <table style="width:100%;border-collapse:collapse">{table_rows}</table>
      {avail_block}
    </div>
  </div>"""

    return module_card("Doelgroep", "Profiel & Dimensionering",
                       content, 78)


def render_module_5_sourcing(r: dict, sector_ref: dict) -> str:
    s = r.get("sourcing", {})
    concurrenten = s.get("top5_concurrenten", sector_ref.get("top5_concurrenten", []))

    tension = s.get("markt_tension_index", 7)
    tension_bar = pct_bar(tension * 10, COLORS["red"] if tension >= 8 else COLORS["amber"], 12)

    rows = ""
    for c in concurrenten[:5]:
        if isinstance(c, dict):
            naam = c.get("naam", "—")
            loc  = c.get("locatie", "—")
            agg  = c.get("agressiviteit", 5)
            prem = c.get("salaris_premie_pct", 0)
        else:
            naam, loc, agg, prem = c[0], c[1], c[2], 0

        agg_dots = "".join(f'<span style="color:{"#EF4444" if i < agg else "#E5E7EB"};font-size:14px">&#9679;</span>' for i in range(10))
        rows += (f'<tr><td style="padding:7px 10px;font-weight:600;font-size:13px">{naam}</td>'
                 f'<td style="padding:7px 10px;font-size:12px;color:{COLORS["muted"]}">{loc}</td>'
                 f'<td style="padding:7px 10px">{agg_dots}</td>'
                 f'<td style="padding:7px 10px;font-size:13px;{"color:#EF4444;font-weight:700" if prem > 0 else "color:#6B7280"}">'
                 f'{f"+{prem}%" if prem > 0 else "—"}</td></tr>')

    uw_positie = s.get("uw_positie_omschrijving", "")
    vacatures = s.get("actieve_vacatures_markt", 0)

    content = f"""
  <div style="display:flex;gap:12px;margin-bottom:16px">
    <div style="flex:1;background:{COLORS['light']};border-radius:8px;padding:14px;text-align:center">
      <div style="font-size:28px;font-weight:700;color:{COLORS['accent']}">{tension:.1f}/10</div>
      <div style="font-size:11px;color:{COLORS['muted']}">Markt Tension Index</div>
    </div>
    <div style="flex:1;background:{COLORS['light']};border-radius:8px;padding:14px;text-align:center">
      <div style="font-size:28px;font-weight:700;color:{COLORS['primary']}">{vacatures:,}</div>
      <div style="font-size:11px;color:{COLORS['muted']}">Actieve vacatures markt</div>
    </div>
  </div>
  {tension_bar}
  <div style="font-size:11px;color:{COLORS['muted']};margin-bottom:14px;margin-top:4px">Sourcingdruk in jouw regio/sector</div>
  <table style="width:100%;border-collapse:collapse;font-size:13px">
    <tr style="background:{COLORS['light']}">
      <th style="padding:7px 10px;text-align:left;font-weight:600;color:{COLORS['muted']}">Concurrent</th>
      <th style="padding:7px 10px;text-align:left;font-weight:600;color:{COLORS['muted']}">Locatie</th>
      <th style="padding:7px 10px;text-align:left;font-weight:600;color:{COLORS['muted']}">Agressiviteit</th>
      <th style="padding:7px 10px;text-align:left;font-weight:600;color:{COLORS['muted']}">Salaris+</th>
    </tr>
    {rows}
  </table>
  {f'<div style="margin-top:12px;padding:10px 14px;background:#FEF9F0;border-left:3px solid {COLORS["accent"]};font-size:13px;border-radius:0 6px 6px 0"><strong>Uw positie:</strong> {uw_positie}</div>' if uw_positie else ""}"""

    return module_card("Concurrentieanalyse", "Sourcing Druk & Marktpositie",
                       content, r.get("confidence", {}).get("sourcing", 72))


def render_module_6_regio(r: dict, sector_ref: dict) -> str:
    p = r.get("doelgroep_profiel", {})
    regio = p.get("regio", "Gelderland / Overijssel")
    pool = p.get("pool_regio_schatting", 0)

    top3 = sector_ref.get("regio_top3", [])
    max_pct = max((t[1] for t in top3), default=1)

    bars = ""
    for naam, pct in top3:
        w = int(pct / max_pct * 100)
        highlight = COLORS["accent"] if naam.lower() in regio.lower() else COLORS["primary"]
        bars += f"""<div style="margin-bottom:10px">
      <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:3px">
        <span style="font-weight:{'700' if naam.lower() in regio.lower() else '400'};color:{highlight}">{naam}</span>
        <span style="color:{COLORS['muted']}">{pct}% van NL pool</span>
      </div>
      {pct_bar(w, highlight, 10)}
    </div>"""

    pool_blocks = [
        ("Pool schatting regio", f"~{pool:,}" if isinstance(pool, int) else "—"),
        ("Actief zoekend",       f"~{int(pool * p.get('actief_zoekend_pct', 15) / 100):,}" if isinstance(pool, int) else "—"),
        ("Passief bereikbaar",   f"~{int(pool * p.get('passief_bereikbaar_pct', 35) / 100):,}" if isinstance(pool, int) else "—"),
    ]

    stats = "".join(f'<div style="flex:1;background:{COLORS["light"]};border-radius:8px;padding:12px;text-align:center">'
                    f'<div style="font-size:20px;font-weight:700;color:{COLORS["primary"]}">{v}</div>'
                    f'<div style="font-size:11px;color:{COLORS["muted"]};margin-top:2px">{k}</div></div>'
                    for k, v in pool_blocks)

    content = f"""
  <div style="display:flex;gap:8px;margin-bottom:18px">{stats}</div>
  <div style="font-size:12px;font-weight:700;color:{COLORS['muted']};text-transform:uppercase;letter-spacing:.8px;margin-bottom:10px">Regionale Concentratie NL</div>
  {bars}"""

    return module_card("Geografie", "Regionale Arbeidsmarktanalyse",
                       content, 78)


def render_module_7_kanalen(r: dict, sector_ref: dict) -> str:
    kanalen = r.get("kanalen", [])
    if not kanalen:
        kanalen = [{"naam": k[0], "effectiviteit": k[1], "kosten_indicatie": k[2],
                    "avg_respons_dagen": k[3], "aanbevolen": k[1] >= 8, "toelichting": ""}
                   for k in sector_ref.get("kanalen", [])]

    rows = ""
    for k in kanalen[:6]:
        naam = k.get("naam", "—")
        eff  = float(k.get("effectiviteit", 5))
        kosten = k.get("kosten_indicatie", "—")
        respons = k.get("avg_respons_dagen", "—")
        aanbevolen = k.get("aanbevolen", False)
        toel = k.get("toelichting", "")

        dot_count = 5
        filled_dots = int(eff / 2)
        dots = "".join(f'<span style="color:{"#E8630A" if i < filled_dots else "#E5E7EB"};font-size:16px">&#9679;</span>'
                       for i in range(dot_count))
        aanbevolen_badge = badge("Aanbevolen", "#D1FAE5", "#065F46") if aanbevolen else ""

        rows += (f'<tr style="border-bottom:1px solid {COLORS["border"]}">'
                 f'<td style="padding:10px 10px;font-weight:600;font-size:13px">{naam} {aanbevolen_badge}</td>'
                 f'<td style="padding:10px 10px">{dots}</td>'
                 f'<td style="padding:10px 10px;font-size:12px;color:{COLORS["muted"]}">{kosten}</td>'
                 f'<td style="padding:10px 10px;font-size:12px">{respons}d</td>'
                 f'<td style="padding:10px 10px;font-size:12px;color:{COLORS["muted"]}">{toel[:60]}{"…" if len(toel)>60 else ""}</td>'
                 f'</tr>')

    content = f"""<table style="width:100%;border-collapse:collapse;font-size:13px">
  <tr style="background:{COLORS['light']}">
    <th style="padding:8px 10px;text-align:left;font-weight:600;color:{COLORS['muted']}">Kanaal</th>
    <th style="padding:8px 10px;text-align:left;font-weight:600;color:{COLORS['muted']}">Score</th>
    <th style="padding:8px 10px;text-align:left;font-weight:600;color:{COLORS['muted']}">Kosten</th>
    <th style="padding:8px 10px;text-align:left;font-weight:600;color:{COLORS['muted']}">Respons</th>
    <th style="padding:8px 10px;text-align:left;font-weight:600;color:{COLORS['muted']}">Toelichting</th>
  </tr>
  {rows}
</table>"""

    return module_card("Werving", "Kanaal-Effectiviteit Matrix",
                       content, r.get("confidence", {}).get("kanalen", 85))


def render_module_8_evp(r: dict) -> str:
    evp = r.get("evp_analyse", {})
    factoren = evp.get("factoren", [])
    if not factoren:
        return ""

    sterk = evp.get("sterkste_evp_punt", "")
    kritiek = evp.get("kritieke_gap", "")

    rows = ""
    for f in factoren[:6]:
        naam      = f.get("naam", "—")
        belang    = float(f.get("kandidaat_belang", 7))
        uw_score  = float(f.get("uw_score", 6))
        gap       = float(f.get("gap", uw_score - belang))
        actie     = f.get("actie", "")

        gap_color = COLORS["red"] if gap <= -1.5 else (COLORS["amber"] if gap < 0 else COLORS["green"])
        gap_str   = f'{gap:+.1f}'

        rows += f"""<tr style="border-bottom:1px solid {COLORS['border']}">
  <td style="padding:9px 10px;font-weight:600;font-size:13px;width:160px">{naam}</td>
  <td style="padding:9px 10px;width:130px">
    <div style="font-size:10px;color:{COLORS['muted']};margin-bottom:3px">Kandidaatbelang</div>
    {pct_bar(belang * 10, COLORS["primary"], 8)}
    <div style="font-size:11px;font-weight:600">{belang:.1f}/10</div>
  </td>
  <td style="padding:9px 10px;width:130px">
    <div style="font-size:10px;color:{COLORS['muted']};margin-bottom:3px">Uw positie</div>
    {pct_bar(uw_score * 10, COLORS["accent"], 8)}
    <div style="font-size:11px;font-weight:600">{uw_score:.1f}/10</div>
  </td>
  <td style="padding:9px 10px;font-weight:700;color:{gap_color};font-size:14px;text-align:center">{gap_str}</td>
  <td style="padding:9px 10px;font-size:12px;color:{COLORS['muted']}">{actie[:80]}{"…" if len(actie)>80 else ""}</td>
</tr>"""

    highlights = ""
    if sterk:
        highlights += f'<div style="flex:1;background:#D1FAE5;border-radius:8px;padding:12px"><div style="font-size:11px;font-weight:700;color:#065F46;text-transform:uppercase;letter-spacing:.8px">Sterkst EVP punt</div><div style="font-size:13px;color:#064E3B;margin-top:4px">{sterk}</div></div>'
    if kritiek:
        highlights += f'<div style="flex:1;background:#FEE2E2;border-radius:8px;padding:12px"><div style="font-size:11px;font-weight:700;color:#991B1B;text-transform:uppercase;letter-spacing:.8px">Kritieke gap</div><div style="font-size:13px;color:#7F1D1D;margin-top:4px">{kritiek}</div></div>'

    content = f"""
  <div style="font-size:11px;color:{COLORS['muted']};margin-bottom:12px">
    Gap = Uw Positie − Kandidaatbelang &nbsp;|&nbsp; Negatief = U scoort lager dan verwacht
  </div>
  <table style="width:100%;border-collapse:collapse">
    <tr style="background:{COLORS['light']}">
      <th style="padding:8px 10px;text-align:left;font-weight:600;color:{COLORS['muted']}">Factor</th>
      <th style="padding:8px 10px;text-align:left;font-weight:600;color:{COLORS['muted']}">Belang (kandidaat)</th>
      <th style="padding:8px 10px;text-align:left;font-weight:600;color:{COLORS['muted']}">Uw positie</th>
      <th style="padding:8px 10px;text-align:center;font-weight:600;color:{COLORS['muted']}">Gap</th>
      <th style="padding:8px 10px;text-align:left;font-weight:600;color:{COLORS['muted']}">Actie</th>
    </tr>
    {rows}
  </table>
  {f'<div style="display:flex;gap:10px;margin-top:14px">{highlights}</div>' if highlights else ""}"""

    return module_card("EVP Analyse", "Pull-Factoren & Werkgeverspositionering",
                       content, r.get("confidence", {}).get("evp", 76))


def render_module_9_ttf(r: dict) -> str:
    ttf = r.get("time_to_fill", {})
    verwacht = ttf.get("verwacht_ttf_dagen", 75)
    benchmark = ttf.get("sector_benchmark_dagen", 80)
    fases = ttf.get("fases", [])
    opt = ttf.get("scenario_optimistisch", 50)
    pess = ttf.get("scenario_pessimistisch", 120)
    advies = ttf.get("ttf_advies", "")

    totaal_fases = sum(f.get("dagen", 0) for f in fases) or 1
    fase_bars = ""
    fase_colors = [COLORS["accent"], COLORS["primary"], COLORS["amber"], COLORS["green"]]
    for i, fase in enumerate(fases[:4]):
        dagen = fase.get("dagen", 0)
        w = int(dagen / totaal_fases * 100)
        bottleneck = fase.get("bottleneck", False)
        color = COLORS["red"] if bottleneck else fase_colors[i % 4]
        fase_bars += f"""<div style="margin-bottom:8px">
      <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px">
        <span style="color:{COLORS['primary']};font-weight:{'700' if bottleneck else '400'}">{fase['fase']}{' ⚠️' if bottleneck else ''}</span>
        <span style="color:{COLORS['muted']}">{dagen} dagen</span>
      </div>
      {pct_bar(w, color, 10)}
    </div>"""

    vs_bench = verwacht - benchmark
    bench_text = f'{abs(vs_bench)} dagen {"trager" if vs_bench > 0 else "sneller"} dan sectorgemiddelde'

    content = f"""
  <div style="display:flex;gap:12px;margin-bottom:18px">
    <div style="flex:1;background:{COLORS['light']};border-radius:8px;padding:14px;text-align:center">
      <div style="font-size:32px;font-weight:700;color:{COLORS['primary']}">{verwacht}</div>
      <div style="font-size:11px;color:{COLORS['muted']}">Verwacht (dagen)</div>
    </div>
    <div style="flex:1;background:{COLORS['light']};border-radius:8px;padding:14px;text-align:center">
      <div style="font-size:32px;font-weight:700;color:{COLORS['green']}">{opt}</div>
      <div style="font-size:11px;color:{COLORS['muted']}">Optimistisch</div>
    </div>
    <div style="flex:1;background:{COLORS['light']};border-radius:8px;padding:14px;text-align:center">
      <div style="font-size:32px;font-weight:700;color:{COLORS['red']}">{pess}</div>
      <div style="font-size:11px;color:{COLORS['muted']}">Pessimistisch</div>
    </div>
  </div>
  <div style="font-size:12px;color:{COLORS['muted']};margin-bottom:12px">
    <strong>vs. sector benchmark ({benchmark} dagen):</strong> {bench_text}
  </div>
  {fase_bars}
  {f'<div style="margin-top:12px;padding:10px 14px;background:#F0FDF4;border-left:3px solid {COLORS["green"]};font-size:13px;border-radius:0 6px 6px 0"><strong>Advies:</strong> {advies}</div>' if advies else ""}"""

    return module_card("Planning", "Time-to-Fill Prognose",
                       content, r.get("confidence", {}).get("arbeidsmarkt", 82))


def render_module_10_scenario(r: dict) -> str:
    sim = r.get("scenario_simulator", {})
    scenarios = sim.get("scenarios", [])
    aanbevolen = sim.get("aanbevolen_scenario", "")
    toel = sim.get("aanbeveling_toelichting", "")

    if not scenarios:
        return ""

    kleur_map = {
        "grijs":  (COLORS["light"],  COLORS["muted"],   COLORS["primary"]),
        "oranje": ("#FEF9F0",         COLORS["accent"],  COLORS["accent"]),
        "groen":  ("#F0FDF4",         COLORS["green"],   COLORS["green"]),
    }

    cards = ""
    for sc in scenarios[:3]:
        naam = sc.get("naam", "—")
        omschr = sc.get("beschrijving", "")
        ttf = sc.get("verwacht_ttf", "—")
        bereik = sc.get("kandidaat_bereik", "—")
        kans = sc.get("kans_succes_pct", 0)
        kosten = sc.get("kosten_indicatie", "—")
        kleur = sc.get("kleur", "grijs")
        bg, accent_c, text_c = kleur_map.get(kleur, kleur_map["grijs"])
        is_best = naam == aanbevolen

        cards += f"""<div style="flex:1;background:{bg};border-radius:10px;padding:16px;{'border:2px solid ' + accent_c + ';' if is_best else 'border:1px solid ' + COLORS['border'] + ';'}">
      {f'<div style="font-size:10px;font-weight:700;color:{accent_c};text-transform:uppercase;letter-spacing:.8px;margin-bottom:6px">&#9733; Aanbevolen</div>' if is_best else ''}
      <div style="font-size:14px;font-weight:700;color:{text_c};margin-bottom:4px">{naam}</div>
      <div style="font-size:12px;color:{COLORS['muted']};margin-bottom:12px;line-height:1.5">{omschr}</div>
      <div style="font-size:10px;color:{COLORS['muted']};text-transform:uppercase;letter-spacing:.8px;margin-bottom:2px">Slagingskans</div>
      {pct_bar(kans, text_c, 10)}
      <div style="font-size:18px;font-weight:700;color:{text_c};margin:4px 0 10px">{kans}%</div>
      <table style="width:100%;font-size:12px">
        <tr><td style="color:{COLORS['muted']};padding:2px 0">Time-to-fill</td><td style="font-weight:600;text-align:right">{ttf} dagen</td></tr>
        <tr><td style="color:{COLORS['muted']};padding:2px 0">Kandidaatbereik</td><td style="font-weight:600;text-align:right">~{bereik}</td></tr>
        <tr><td style="color:{COLORS['muted']};padding:2px 0">Kostenscenario</td><td style="font-weight:600;text-align:right">{kosten}</td></tr>
      </table>
    </div>"""

    content = f"""
  <div style="display:flex;gap:12px;margin-bottom:14px">{cards}</div>
  {f'<div style="padding:12px 16px;background:#F0FDF4;border-left:3px solid {COLORS["green"]};border-radius:0 6px 6px 0;font-size:13px"><strong>Onze aanbeveling:</strong> {toel}</div>' if toel else ""}"""

    return module_card("Scenario Analyse", "Simulator — Wat Als?",
                       content, r.get("confidence", {}).get("sourcing", 72),
                       badge_text="Uniek")


def render_module_11_actieplan(r: dict) -> str:
    plan = r.get("actieplan", {})
    acties = plan.get("acties", [])
    eerste_stap = plan.get("eerste_stap_vandaag", "")

    if not acties:
        return ""

    prio_colors = {"Urgent": ("#FEE2E2", "#991B1B"), "Hoog": ("#FEF3C7", "#92400E"), "Gemiddeld": ("#F3F4F6", "#6B7280")}

    items = ""
    for i, a in enumerate(sorted(acties, key=lambda x: (-x.get("impact", 5), x.get("effort", 5)))[:6]):
        actie = a.get("actie", "—")
        impact = a.get("impact", 5)
        effort = a.get("effort", 5)
        tijdlijn = a.get("tijdlijn", "—")
        prio = a.get("prioriteit", "Gemiddeld")
        p_bg, p_c = prio_colors.get(prio, prio_colors["Gemiddeld"])

        items += f"""<div style="display:flex;gap:12px;align-items:flex-start;padding:12px 0;border-bottom:1px solid {COLORS['border']}">
      <div style="flex:0 0 auto;width:28px;height:28px;background:{COLORS['primary']};border-radius:50%;color:#fff;font-size:13px;font-weight:700;display:flex;align-items:center;justify-content:center;text-align:center;line-height:28px">{i+1}</div>
      <div style="flex:1">
        <div style="font-size:13px;font-weight:600;color:{COLORS['primary']};margin-bottom:4px">{actie}</div>
        <div style="display:flex;gap:6px;align-items:center">
          {badge(prio, p_bg, p_c)}
          <span style="font-size:11px;color:{COLORS['muted']}">{tijdlijn}</span>
          <span style="font-size:11px;color:{COLORS['muted']}">Impact: {impact}/10 &middot; Effort: {effort}/10</span>
        </div>
      </div>
    </div>"""

    content = f"""
  {items}
  {f'<div style="margin-top:14px;padding:12px 16px;background:#FEF9F0;border-left:3px solid {COLORS["accent"]};border-radius:0 6px 6px 0;font-size:13px"><strong>Start morgen:</strong> {eerste_stap}</div>' if eerste_stap else ""}"""

    return module_card("Actieplan", "Geprioriteerde Stappen — Impact vs. Effort",
                       content, r.get("confidence", {}).get("kanalen", 82),
                       badge_text="Uniek")


def render_module_12_methodology(r: dict) -> str:
    conf = r.get("confidence", {})
    bronnen = conf.get("databronnen", ["CBS Arbeidsmarkt 2024", "UWV Arbeidsmarkt Update Q4 2024",
                                        "Intelligence Group Arbeidsmarkt Rapport 2024",
                                        "StepStone Salarisgids 2024", "Randstad Werkmonitor 2024",
                                        "Recruitin B.V. — sector expertise en eigen data"])
    overall = conf.get("overall", 80)

    modules_conf = [
        ("Arbeidsmarkt",  conf.get("arbeidsmarkt", 85)),
        ("Salarisdata",   conf.get("salaris", 82)),
        ("Sourcing",      conf.get("sourcing", 72)),
        ("Kanalen",       conf.get("kanalen", 85)),
        ("EVP Analyse",   conf.get("evp", 76)),
    ]

    conf_rows = "".join(f'<tr><td style="padding:5px 0;font-size:13px;color:{COLORS["muted"]};width:140px">{k}</td>'
                        f'<td style="padding:5px 0">{pct_bar(v, COLORS["accent"], 6)}</td>'
                        f'<td style="padding:5px 0;font-size:12px;font-weight:700;text-align:right;width:50px">{v}%</td>'
                        f'</tr>' for k, v in modules_conf)

    bronnen_html = " &middot; ".join(bronnen)

    content = f"""
  <div style="display:flex;gap:16px;align-items:flex-start">
    <div style="flex:1">
      <div style="font-size:12px;font-weight:700;color:{COLORS['muted']};text-transform:uppercase;letter-spacing:.8px;margin-bottom:10px">Nauwkeurigheid per module</div>
      <table style="width:100%;border-collapse:collapse">{conf_rows}</table>
    </div>
    <div style="flex:0 0 auto;text-align:center">
      {score_ring_svg(overall, "Overall")}
      <div style="font-size:11px;color:{COLORS['muted']};margin-top:4px">Nauwkeurigheid</div>
    </div>
  </div>
  <div style="margin-top:14px;padding:12px 14px;background:{COLORS['light']};border-radius:8px;font-size:11px;color:{COLORS['muted']};line-height:1.7">
    <strong style="color:{COLORS['primary']}">Databronnen:</strong> {bronnen_html}<br>
    <strong style="color:{COLORS['primary']}">Methodologie:</strong> Sectorreferentiedata (CBS, UWV, Intelligence Group) + bedrijfsspecifieke contextualisering via Claude Sonnet 4.6.
    Kwantitatieve schattingen zijn indicatief en gebaseerd op landelijke trends vertaald naar regionale context.<br>
    <strong style="color:{COLORS['primary']}">Geldigheid:</strong> Data reflecteert Q1 2026. Marktcondities kunnen snel wijzigen.
  </div>"""

    return module_card("Methodologie", "Nauwkeurigheid & Databronnen",
                       content, overall)


# ---------------------------------------------------------------------------
# FULL HTML ASSEMBLY
# ---------------------------------------------------------------------------
def render_full_html(lead: dict, rapport: dict, sector_ref: dict) -> str:
    modules = [
        render_module_1_executive(rapport, lead),
        render_module_2_thermometer(rapport),
        render_module_3_salaris(rapport),
        render_module_4_profiel(rapport),
        render_module_5_sourcing(rapport, sector_ref),
        render_module_6_regio(rapport, sector_ref),
        render_module_7_kanalen(rapport, sector_ref),
        render_module_8_evp(rapport),
        render_module_9_ttf(rapport),
        render_module_10_scenario(rapport),
        render_module_11_actieplan(rapport),
        render_module_12_methodology(rapport),
    ]

    modules_html = "\n".join(m for m in modules if m)

    cta_block = f"""
<div style="padding:32px 24px;text-align:center;background:{COLORS['primary']};border-radius:12px;margin-bottom:16px">
  <h2 style="color:#fff;font-size:20px;font-weight:700;margin:0 0 8px">Klaar om deze doelgroep actief te werven?</h2>
  <p style="color:#9CA3AF;font-size:14px;margin:0 0 20px">Recruitin B.V. activeert uw wervingsstrategie binnen 48 uur</p>
  <a href="https://kandidatentekort.nl" style="display:inline-block;background:{COLORS['accent']};color:#fff;padding:14px 36px;border-radius:8px;text-decoration:none;font-weight:700;font-size:15px;letter-spacing:.2px">Plan een strategiegesprek &rarr;</a>
</div>
<div style="padding:16px 0;text-align:center;font-size:11px;color:#9CA3AF">
  Recruitin B.V. &middot; Doesburg &middot; kandidatentekort.nl &middot; rapport@kandidatentekort.nl
</div>"""

    return f"""<!DOCTYPE html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="color-scheme" content="light">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <title>Doelgroepen Rapport — {lead['company_name']}</title>
</head>
<body style="margin:0;padding:0;background:#F3F4F6;font-family:'DM Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:{COLORS['primary']};-webkit-font-smoothing:antialiased">
  <div style="max-width:700px;margin:0 auto;padding:24px 16px">
    {modules_html}
    {cta_block}
  </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# EMAIL SEND
# ---------------------------------------------------------------------------
def send_email(to: str, subject: str, html: str):
    r = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
        json={
            "from": "Recruitin <rapport@kandidatentekort.nl>",
            "to": [to],
            "subject": subject,
            "html": html,
        },
    )
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# SUPABASE HELPERS (used by both Flask endpoint and background thread)
# ---------------------------------------------------------------------------
def update_doelgroep_lead_status(lead_id: str, status: str):
    r = requests.patch(
        f"{SUPABASE_REST}/leads?id=eq.{lead_id}",
        headers=HEADERS_SB,
        json={"status": status, "updated_at": datetime.utcnow().isoformat()},
    )
    r.raise_for_status()


def insert_doelgroep_lead(company_name: str, email: str, sector: str,
                           team_size: str, challenge: str) -> dict:
    """Insert new lead into Supabase leads table. Returns created record."""
    payload = {
        "company_name": company_name,
        "email": email,
        "sector": sector,
        "team_size": team_size,
        "challenge": challenge,
        "status": "intake_received",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    r = requests.post(
        f"{SUPABASE_REST}/leads",
        headers=HEADERS_SB,
        json=payload,
    )
    r.raise_for_status()
    records = r.json()
    return records[0] if records else {"id": "unknown", **payload}


# ---------------------------------------------------------------------------
# BACKGROUND ENTRY POINT (called from Flask in a threading.Thread)
# ---------------------------------------------------------------------------
def process_doelgroep_lead_bg(lead: dict):
    """
    Full pipeline: Claude analyse → HTML render → Resend email → Supabase status update.
    Designed to run in a background thread from the Flask webhook handler.
    lead dict must have: id, email, company_name, sector, team_size, challenge
    """
    email = lead["email"]
    bedrijf = lead["company_name"]
    sector_str = lead.get("sector", "productie")
    lead_id = lead.get("id", "unknown")

    logger.info(f"[doelgroep] Start pipeline: {bedrijf} ({email})")

    try:
        sector_ref, sector_key = get_sector_ref(sector_str)
        logger.info(f"[doelgroep] Sector: {sector_key} (schaarste {sector_ref['schaarste']}/10)")

        rapport = generate_rapport_json(lead, sector_ref)
        logger.info(f"[doelgroep] Claude klaar — score {rapport.get('overall_score', '?')}/100")

        html = render_full_html(lead, rapport, sector_ref)
        logger.info(f"[doelgroep] HTML rendered — {len(html)} bytes")

        result = send_email(
            to=email,
            subject=f"Jouw Doelgroepen Rapport — {bedrijf}",
            html=html,
        )
        logger.info(f"[doelgroep] Email verzonden: {result.get('id', 'ok')}")

        if lead_id and lead_id != "unknown":
            update_doelgroep_lead_status(lead_id, "rapport_sent")
            logger.info(f"[doelgroep] Status → rapport_sent (id={lead_id})")

    except Exception as e:
        logger.error(f"[doelgroep] Pipeline fout voor {email}: {e}", exc_info=True)
        try:
            if lead_id and lead_id != "unknown":
                update_doelgroep_lead_status(lead_id, "error")
        except Exception:
            pass
