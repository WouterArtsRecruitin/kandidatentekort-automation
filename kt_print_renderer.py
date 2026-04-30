"""
Print-PDF voorbeeld-renderer voor sample-rapporten op kandidatentekort.nl.

Bewust GEEN volledig rapport — een 3-pagina teaser die de belangrijkste
onderwerpen laat zien en visitors triggert om hun eigen vacature-analyse aan
te vragen. Conversie boven completeness.

Pagina's:
  P1 — Cover + executive (overall_score, samenvatting, 4 markt-KPIs)
  P2 — Hoogtepunten (categorie-scores · salaris benchmark · top action items + kanalen)
  P3 — "Wat zit er nog meer in?" + CTA-back

Pattern: gebaseerd op DGR's print_renderer.py (CLAUDE.md WEASYPRINT_FLEX_REGEL).
Brand: KT magenta (#FF00CC) op dark ink (#07050f).
"""
from __future__ import annotations
from datetime import datetime
import math

# ── Tokens ───────────────────────────────────────────────────────────────────
ACCENT = "#FF00CC"
INK = "#07050f"
MUTED = "#6B7280"
LIGHT = "#F5F5F5"
BORDER = "#E5E7EB"
GREEN = "#10B981"
AMBER = "#F59E0B"
RED = "#EF4444"

TOTAL_PAGES = 3


def _score_ring_svg(score: int, label: str = "Score") -> str:
    """Donut ring met score (0-100) — kleur op basis van waarde."""
    r = 44
    circ = 2 * math.pi * r
    filled = circ * score / 100
    color = GREEN if score >= 70 else (AMBER if score >= 50 else RED)
    return (
        f'<svg width="110" height="110" viewBox="0 0 110 110">'
        f'<circle cx="55" cy="55" r="{r}" fill="none" stroke="#E5E7EB" stroke-width="9"/>'
        f'<circle cx="55" cy="55" r="{r}" fill="none" stroke="{color}" stroke-width="9" '
        f'stroke-dasharray="{filled:.1f} {circ:.1f}" stroke-linecap="round" '
        f'transform="rotate(-90 55 55)"/>'
        f'<text x="55" y="50" text-anchor="middle" font-family="Arial" font-size="26" '
        f'fill="{INK}" font-weight="700">{score}</text>'
        f'<text x="55" y="68" text-anchor="middle" font-family="Arial" font-size="10" '
        f'fill="{MUTED}">{label}</text>'
        f'</svg>'
    )


_BASE_CSS = """
@page { size: A4 portrait; margin: 0 }
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@500;700&display=swap');

* { box-sizing: border-box }
html, body { margin: 0; padding: 0; background: #fff; font-family: 'Inter', system-ui, sans-serif; font-size: 10pt; line-height: 1.55; color: """ + INK + """; -webkit-print-color-adjust: exact; print-color-adjust: exact }

.page {
  width: 210mm; height: 297mm;
  padding: 16mm 18mm 16mm;
  position: relative;
  overflow: hidden;
  background: #fff;
  page-break-after: always;
  break-after: page;
}
.page:last-child { page-break-after: auto; break-after: auto }

.page-header {
  display: flex; justify-content: space-between; align-items: center;
  font-family: 'JetBrains Mono', monospace; font-size: 8pt;
  letter-spacing: 0.12em; text-transform: uppercase; color: """ + MUTED + """;
  border-bottom: 1px solid """ + BORDER + """;
  padding-bottom: 8pt; margin-bottom: 18pt;
}
.page-header .brand { color: """ + INK + """; font-weight: 700 }
.page-header .brand .dot { display: inline-block; width: 6pt; height: 6pt; border-radius: 50%; background: """ + ACCENT + """; margin-right: 5pt; vertical-align: 1pt }

.page-footer {
  position: absolute; bottom: 10mm; left: 18mm; right: 18mm;
  display: flex; justify-content: space-between;
  font-family: 'JetBrains Mono', monospace; font-size: 8pt;
  letter-spacing: 0.12em; text-transform: uppercase; color: """ + MUTED + """;
  border-top: 1px solid """ + BORDER + """; padding-top: 8pt;
}

h1, h2, h3, h4 { margin: 0; font-weight: 800; letter-spacing: -0.02em; color: """ + INK + """ }
p { margin: 0 0 8pt }

.module-label { font-family: 'JetBrains Mono', monospace; font-size: 9pt; font-weight: 700; color: """ + ACCENT + """; letter-spacing: 0.18em; text-transform: uppercase; margin-bottom: 4pt }

/* KPI grid via TABLE (Chromium-PDF predictabel) */
.kpi-grid { width: 100%; border-collapse: separate; border-spacing: 8pt; table-layout: fixed; margin: 14pt 0 }
.kpi-grid td { background: """ + LIGHT + """; padding: 18pt 8pt; text-align: center; border-radius: 8pt; vertical-align: middle }
.kpi-grid .v { font-size: 22pt; font-weight: 800; color: """ + INK + """; line-height: 1.05 }
.kpi-grid .v.accent { color: """ + ACCENT + """ }
.kpi-grid .v.green { color: """ + GREEN + """ }
.kpi-grid .v.amber { color: """ + AMBER + """ }
.kpi-grid .v.red { color: """ + RED + """ }
.kpi-grid .l { font-size: 8pt; color: """ + MUTED + """; margin-top: 6pt; letter-spacing: 0.08em; text-transform: uppercase; font-weight: 600 }

.callout { padding: 12pt 16pt; border-radius: 6pt; margin: 10pt 0; font-size: 10pt; line-height: 1.55 }
.callout--accent { background: rgba(255,0,204,0.06); border-left: 3pt solid """ + ACCENT + """ }
.callout--ink { background: """ + INK + """; color: #fff }
.callout--green { background: #F0FDF4; border-left: 3pt solid """ + GREEN + """ }
.callout--red { background: #FEF2F2; border-left: 3pt solid """ + RED + """ }

/* COVER ─────────────────────────── */
.cover { position: relative; height: 100% }
.cover .magenta-strip { background: """ + ACCENT + """; color: #fff; padding: 7pt 16pt; margin: -16mm -18mm 0; font-family: 'JetBrains Mono', monospace; font-size: 8pt; font-weight: 700; letter-spacing: 0.15em; text-transform: uppercase; display: table; width: calc(100% + 36mm) }
.cover .magenta-strip > div { display: table-cell; vertical-align: middle }
.cover .magenta-strip .right { text-align: right }
.cover .top-strip { display: flex; justify-content: space-between; align-items: center; font-family: 'JetBrains Mono', monospace; font-size: 8pt; letter-spacing: 0.15em; text-transform: uppercase; color: """ + MUTED + """; margin-top: 12pt }
.cover .top-strip .brand { color: """ + INK + """; font-weight: 700; font-size: 11pt }
.cover .top-strip .brand .dot { display: inline-block; width: 8pt; height: 8pt; border-radius: 50%; background: """ + ACCENT + """; margin-right: 7pt; vertical-align: 1pt }
.cover .lead-meta { font-family: 'JetBrains Mono', monospace; font-size: 9pt; letter-spacing: 0.18em; text-transform: uppercase; color: """ + ACCENT + """; font-weight: 700; margin: 22pt 0 6pt }
.cover h1 { font-weight: 900; font-size: 60pt; line-height: 0.92; letter-spacing: -0.04em; margin: 0 0 8pt; max-width: 88% }
.cover h1 .accent { color: """ + ACCENT + """ }
.cover .deck { font-size: 12pt; line-height: 1.5; color: """ + MUTED + """; max-width: 88%; margin: 0 0 14pt }
.cover .score-row { display: table; width: 100%; margin: 8pt 0; background: """ + LIGHT + """; border-radius: 8pt; padding: 14pt }
.cover .score-row > div { display: table-cell; vertical-align: middle }
.cover .score-row .ring { width: 130pt; padding-right: 16pt }
.cover .score-row .summary { font-size: 11pt; line-height: 1.55 }
.cover .summary strong { color: """ + INK + """ }
.cover .summary .h-label { font-family: 'JetBrains Mono', monospace; font-size: 8pt; font-weight: 700; color: """ + ACCENT + """; letter-spacing: 0.18em; text-transform: uppercase; margin-bottom: 6pt; display: block }

.cover .preview-grid { display: table; width: 100%; border-collapse: separate; border-spacing: 8pt; table-layout: fixed; margin-top: 12pt }
.cover .preview-grid > div { display: table-cell; padding: 10pt 10pt 12pt; border: 1.5pt solid """ + ACCENT + """; border-radius: 8pt; vertical-align: top; background: #fff }
.cover .preview-grid .num { font-family: 'JetBrains Mono', monospace; font-size: 9pt; font-weight: 700; color: """ + ACCENT + """; letter-spacing: 0.15em; text-transform: uppercase }
.cover .preview-grid .v { font-size: 12pt; font-weight: 800; color: """ + INK + """; letter-spacing: -0.015em; line-height: 1.2; margin: 4pt 0 2pt; word-wrap: break-word }
.cover .preview-grid .l { font-size: 8.5pt; color: """ + MUTED + """; line-height: 1.4 }
.cover .preview-label { font-family: 'JetBrains Mono', monospace; font-size: 9pt; font-weight: 700; color: """ + ACCENT + """; letter-spacing: 0.15em; text-transform: uppercase; margin: 14pt 0 0; padding-top: 10pt; border-top: 1px solid """ + BORDER + """ }
.cover .footer-band { position: absolute; left: 0; right: 0; bottom: 0; border-top: 3pt solid """ + ACCENT + """; padding-top: 10pt }
.cover .footer-band .row { display: flex; justify-content: space-between; align-items: baseline; gap: 14pt }
.cover .footer-band .left { font-size: 10pt; color: """ + INK + """; white-space: nowrap }
.cover .footer-band .left strong { color: """ + ACCENT + """; font-weight: 700; letter-spacing: 0.02em }
.cover .footer-band .right { font-family: 'JetBrains Mono', monospace; font-size: 8pt; color: """ + MUTED + """; letter-spacing: 0.1em; text-transform: uppercase; white-space: nowrap }

/* HIGHLIGHTS PAGE ────────────────── */
.highlight-block { padding: 11pt 14pt; border: 1px solid """ + BORDER + """; border-radius: 8pt; margin-bottom: 8pt; break-inside: avoid; page-break-inside: avoid }
.highlight-block .h-label { font-family: 'JetBrains Mono', monospace; font-size: 8pt; font-weight: 700; color: """ + ACCENT + """; letter-spacing: 0.15em; text-transform: uppercase; margin-bottom: 3pt }
.highlight-block .h-title { font-size: 12pt; font-weight: 800; letter-spacing: -0.015em; margin-bottom: 6pt }

/* CTA BACK PAGE ──────────────────── */
.cta-page { display: flex; flex-direction: column; height: 100%; align-items: center; text-align: center; padding-top: 6mm }
.cta-page h2 { font-size: 24pt; line-height: 1.05; max-width: 80%; margin: 6pt 0 8pt; font-weight: 900; letter-spacing: -0.025em }
.cta-page h2 .accent { color: """ + ACCENT + """ }
.cta-page .deck { font-size: 11pt; color: """ + MUTED + """; max-width: 72%; line-height: 1.5; margin-bottom: 12pt }
.locked-modules { width: 84%; margin: 4pt auto 14pt; border-top: 1px solid """ + BORDER + """ }
.locked-modules .row { display: table; width: 100%; padding: 4pt 0; border-bottom: 1px solid """ + BORDER + """ }
.locked-modules .row > div { display: table-cell; vertical-align: middle }
.locked-modules .num { font-family: 'JetBrains Mono', monospace; font-size: 9pt; color: """ + ACCENT + """; font-weight: 700; width: 36pt; letter-spacing: 0.1em }
.locked-modules .name { font-size: 9.5pt; font-weight: 600; text-align: left }
.locked-modules .lock { font-family: 'JetBrains Mono', monospace; font-size: 7.5pt; color: """ + MUTED + """; text-align: right; letter-spacing: 0.1em; text-transform: uppercase; width: 80pt }

.usp-grid { display: table; width: 78%; margin: 6pt auto 14pt; border-spacing: 10pt 0 }
.usp-grid > div { display: table-cell; padding: 12pt 8pt; background: """ + LIGHT + """; border-radius: 6pt; text-align: center; vertical-align: middle }
.usp-grid .v { font-size: 22pt; font-weight: 800; color: """ + ACCENT + """; line-height: 1; letter-spacing: -0.02em }
.usp-grid .l { font-size: 8pt; color: """ + MUTED + """; margin-top: 5pt; letter-spacing: 0.08em; text-transform: uppercase; font-weight: 600 }

.cta-button { display: inline-block; background: """ + ACCENT + """; color: #fff; padding: 13pt 36pt; border-radius: 100pt; font-weight: 700; font-size: 12pt; text-decoration: none; box-shadow: 0 6pt 20pt rgba(255,0,204,0.25); margin-top: 2pt }
.cta-page .url { font-family: 'JetBrains Mono', monospace; font-size: 9pt; color: """ + MUTED + """; letter-spacing: 0.05em; margin-top: 10pt }

/* CATEGORY BAR ────────────────────── */
.cat-row { margin: 2pt 0 }
.cat-row .label-row { display: table; width: 100%; margin-bottom: 2pt }
.cat-row .name { display: table-cell; font-size: 9pt; font-weight: 600; color: """ + INK + """; vertical-align: middle }
.cat-row .score { display: table-cell; text-align: right; font-family: 'JetBrains Mono', monospace; font-size: 8.5pt; font-weight: 700; vertical-align: middle }
.cat-row .track { background: #F3F4F6; border-radius: 3pt; height: 5pt; overflow: hidden }
.cat-row .fill { height: 5pt; border-radius: 3pt }

/* ACTION ITEMS ──────────────────── */
.action-list { margin: 0; padding: 0; list-style: none }
.action-list li { display: table; width: 100%; padding: 4pt 0; border-bottom: 1px dashed """ + BORDER + """ }
.action-list li:last-child { border-bottom: 0 }
.action-list .n { display: table-cell; width: 26pt; font-family: 'JetBrains Mono', monospace; font-size: 10pt; font-weight: 700; color: """ + ACCENT + """; vertical-align: top; padding-top: 1pt }
.action-list .t { display: table-cell; font-size: 9.5pt; line-height: 1.45; color: """ + INK + """; vertical-align: top }

/* CHANNEL CHIP ───────────────────── */
.channel-row { display: table; width: 100%; margin-top: 6pt; border-top: 1px solid """ + BORDER + """; padding-top: 6pt }
.channel-row > div { display: table-cell; vertical-align: middle }
.channel-row .ch-name { font-size: 9.5pt; font-weight: 700; color: """ + INK + """ }
.channel-row .ch-desc { font-size: 8.5pt; color: """ + MUTED + """; line-height: 1.4 }
.channel-row .ch-tag { font-family: 'JetBrains Mono', monospace; font-size: 8pt; font-weight: 700; color: """ + ACCENT + """; letter-spacing: 0.1em; text-transform: uppercase; text-align: right; white-space: nowrap; padding-left: 10pt; width: 90pt }

/* SALARY VS MARKET ───────────────── */
.salary-compare { display: table; width: 100%; margin-top: 4pt }
.salary-compare > div { display: table-cell; padding: 8pt 10pt; vertical-align: top; width: 50% }
.salary-compare .sc-label { font-family: 'JetBrains Mono', monospace; font-size: 8pt; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: """ + MUTED + """; margin-bottom: 3pt }
.salary-compare .sc-val { font-size: 12.5pt; font-weight: 800; color: """ + INK + """; letter-spacing: -0.01em; line-height: 1.15 }
.salary-compare .sc-diff { font-size: 9pt; font-weight: 700; margin-top: 5pt }
.salary-compare .sc-warn { font-size: 8.5pt; color: """ + RED + """; margin-top: 5pt; line-height: 1.4 }

/* Print color forcing */
.kpi-grid td, .callout, .usp-grid > div, .cover .sample-banner, .cta-button, .highlight-block, .cat-row .fill, .salary-compare > div { -webkit-print-color-adjust: exact; print-color-adjust: exact }
"""


# ── Helpers ──────────────────────────────────────────────────────────────────
def _kpi_grid(items: list[tuple[str, str, str]]) -> str:
    """items: list of (value, label, color_class)"""
    cells = "".join(
        f'<td><div class="v {c}">{v}</div><div class="l">{l}</div></td>'
        for v, l, c in items
    )
    return f'<table class="kpi-grid"><tr>{cells}</tr></table>'


def _page_footer(page_num: int) -> str:
    return (
        f'<div class="page-footer">'
        f'<span>Voorbeeld &middot; Recruitin B.V.</span>'
        f'<span>{page_num:02d} / {TOTAL_PAGES:02d}</span>'
        f'</div>'
    )


def _page_header(label: str = "") -> str:
    return (
        f'<div class="page-header">'
        f'<span class="brand"><span class="dot"></span>kandidatentekort.nl</span>'
        f'<span>{label}</span>'
        f'</div>'
    )


def _status_color(status: str, score: int) -> str:
    """Color voor categorie-status — fallback op score."""
    if status == "ok" or score >= 65:
        return GREEN
    if status == "warning" or score >= 45:
        return AMBER
    return RED


# ── Page 01 — Cover + executive samenvatting ─────────────────────────────────
def _page_cover(lead: dict, analysis: dict) -> str:
    bedrijf = lead.get("bedrijf", "Voorbeeld B.V.")
    functie = lead.get("functie", "—")
    sector = (lead.get("sector", "—") or "—").replace("-", " ").title()
    regio = (lead.get("regio", "—") or "—").replace("-", " ").title()

    score = analysis.get("overall_score", 60)
    samenvatting = analysis.get("samenvatting", "") or ""
    if len(samenvatting) > 280:
        samenvatting = samenvatting[:280].rsplit(" ", 1)[0] + "…"

    market = analysis.get("market_analysis", {}) or {}
    competing = market.get("competing_vacancies", "—")
    candidates = market.get("potential_candidates", "—")
    median = market.get("market_median_salary", "—")
    ratio = market.get("supply_demand_ratio", "—")

    # Preview-3 inzichten ────────────────────────────────────────
    categories = analysis.get("categories", []) or []
    weakest = min(categories, key=lambda c: c.get("score", 100), default=None)
    strongest = max(categories, key=lambda c: c.get("score", 0), default=None)
    sal = analysis.get("salary_benchmark", {}) or {}
    sal_diff = sal.get("difference", "—")
    diff_class = "red" if "onder" in (sal_diff or "").lower() else ("green" if "boven" in (sal_diff or "").lower() else "")

    today = datetime.now().strftime("%-d %B %Y")
    ring = _score_ring_svg(score, "Score")

    return f"""<section class="page cover">
  <div class="magenta-strip">
    <div>Voorbeeldrapport &middot; {regio}</div>
    <div class="right">{today}</div>
  </div>
  <div class="top-strip">
    <span class="brand"><span class="dot"></span>kandidatentekort.nl</span>
    <span>01 / {TOTAL_PAGES:02d}</span>
  </div>
  <div class="lead-meta">{functie} &middot; {sector} &middot; {regio}</div>
  <h1>Vacature<br><span class="accent">Analyse.</span></h1>
  <p class="deck">Hoe presteert deze vacature in de markt? Score, salaris, kanalen — vandaag in 3 pagina's. Volledig rapport: <strong>8 modules</strong> + complete herschrijving.</p>
  <div class="score-row">
    <div class="ring">{ring}</div>
    <div class="summary"><span class="h-label">Executive samenvatting</span>{samenvatting}</div>
  </div>
  {_kpi_grid([
      (str(competing), "Concurrerende vacatures", "amber"),
      (str(candidates), "Kandidaten in pool", "green"),
      (str(median), "Mediaan markt", "accent"),
      (str(ratio), "Aanbod / vraag", "red" if isinstance(ratio, str) and ("3" in ratio or "4" in ratio or "5" in ratio) else "amber"),
  ])}
  <div class="preview-label">Hoogtepunten op pagina 02 &rarr;</div>
  <table class="preview-grid"><tr>
    <td>
      <div class="num">01 &middot; Sterkste punt</div>
      <div class="v">{strongest.get("name", "—") if strongest else "—"}</div>
      <div class="l">{strongest.get("score", "—") if strongest else "—"}/100 &middot; behoud dit</div>
    </td>
    <td>
      <div class="num">02 &middot; Zwakste punt</div>
      <div class="v">{weakest.get("name", "—") if weakest else "—"}</div>
      <div class="l">{weakest.get("score", "—") if weakest else "—"}/100 &middot; eerste prioriteit</div>
    </td>
    <td>
      <div class="num">03 &middot; Salaris</div>
      <div class="v">{sal_diff}</div>
      <div class="l">{sal.get("offered_range", "—")} aangeboden</div>
    </td>
  </tr></table>
  <div class="footer-band">
    <div class="row">
      <div class="left"><strong>{bedrijf}</strong> &middot; voorbeeld &middot; recruitin.nl</div>
      <div class="right">Volledig rapport &rarr; pag. 03</div>
    </div>
  </div>
</section>"""


# ── Page 02 — Hoogtepunten (categorie-bars · salary · top actions + kanalen) ─
def _page_highlights(analysis: dict) -> str:
    # Categorie-scores ─────────────────────────────────────────────
    categories = analysis.get("categories", []) or []
    cat_rows = ""
    for cat in categories[:8]:
        name = cat.get("name", "—")
        score = int(cat.get("score", 0) or 0)
        status = cat.get("status", "")
        color = _status_color(status, score)
        pct = max(2, min(100, score))
        cat_rows += f"""
        <div class="cat-row">
          <div class="label-row">
            <div class="name">{name}</div>
            <div class="score" style="color:{color}">{score}/100</div>
          </div>
          <div class="track"><div class="fill" style="width:{pct}%;background:{color}"></div></div>
        </div>"""

    cat_html = f"""
    <div class="highlight-block">
      <div class="h-label">01 &middot; Score per categorie</div>
      <div class="h-title">8 dimensies van je vacature</div>
      {cat_rows}
    </div>"""

    # Salary benchmark ──────────────────────────────────────────────
    sal = analysis.get("salary_benchmark", {}) or {}
    offered = sal.get("offered_range", "—")
    market_range = sal.get("market_range", "—")
    diff = sal.get("difference", "—")
    warning = sal.get("warning", "")
    diff_color = RED if "onder" in (diff or "").lower() else (GREEN if "boven" in (diff or "").lower() else MUTED)

    sal_html = f"""
    <div class="highlight-block">
      <div class="h-label">02 &middot; Salaris benchmark</div>
      <div class="h-title">Wat bied jij — wat biedt de markt</div>
      <div class="salary-compare">
        <div style="border-right:1px solid {BORDER}">
          <div class="sc-label">Jouw aanbod</div>
          <div class="sc-val">{offered}</div>
        </div>
        <div>
          <div class="sc-label">Markt</div>
          <div class="sc-val">{market_range}</div>
          <div class="sc-diff" style="color:{diff_color}">{diff}</div>
        </div>
      </div>
      {f'<div class="sc-warn">⚠ {warning}</div>' if warning else ''}
    </div>"""

    # Top action items + kanalen ────────────────────────────────────
    action_items = analysis.get("action_items", []) or []
    top_3 = action_items[:3]
    actions_html = "".join(
        f'<li><div class="n">{i+1:02d}</div><div class="t">{item}</div></li>'
        for i, item in enumerate(top_3)
    )

    channels = analysis.get("recommended_channels", []) or []
    top_2_ch = channels[:2]
    ch_html = "".join(
        f"""
        <div class="channel-row">
          <div>
            <div class="ch-name">{c.get("name", "—")}</div>
            <div class="ch-desc">{c.get("description", "")}</div>
          </div>
          <div class="ch-tag">{c.get("status", "AANBEVOLEN")}</div>
        </div>"""
        for c in top_2_ch
    )

    actions_html_block = f"""
    <div class="highlight-block">
      <div class="h-label">03 &middot; Top 3 acties &middot; Top 2 kanalen</div>
      <div class="h-title">Wat doe je als eerste</div>
      <ul class="action-list">{actions_html}</ul>
      {ch_html}
    </div>""" if (top_3 or top_2_ch) else ""

    return f"""<section class="page">
  {_page_header()}
  <div class="module-label" style="margin-bottom:2pt">Hoogtepunten</div>
  <h2 style="font-size:20pt;margin-bottom:4pt;letter-spacing:-0.025em">Drie inzichten — visueel</h2>
  <p style="font-size:9.5pt;color:{MUTED};margin-bottom:10pt">Categorie-scores, salaris-positie en eerste acties. Het volledige rapport gaat veel dieper.</p>
  {cat_html}
  {sal_html}
  {actions_html_block}
  {_page_footer(2)}
</section>"""


# ── Page 03 — CTA-back: wat zit er nog meer in + form ────────────────────────
def _page_cta_back(lead: dict, analysis: dict) -> str:
    n_actions = len(analysis.get("action_items", []) or [])
    n_competing = (analysis.get("market_analysis", {}) or {}).get("competing_vacancies", "?")
    locked_modules = [
        ("01", "Top-3 verbeteringen met verwachte impact (%)"),
        ("02", "Alle 8 categorieën met deep-dive analyse"),
        ("03", f"Volledige marktanalyse — {n_competing} concurrenten geprofileerd"),
        ("04", "Salaris benchmark per ervaring-niveau (jr/md/sr)"),
        ("05", "Top 5 concurrenten met agressie-score"),
        ("06", "Volledige kanaalstrategie + budget + ROI per kanaal"),
        ("07", f"Alle {n_actions or 5} action items met deadlines + KPI-targets"),
        ("08", "Sector-specifieke bonus tips"),
    ]
    locked_html = "".join(
        f'<div class="row">'
        f'<div class="num">{num}</div>'
        f'<div class="name">{name}</div>'
        f'<div class="lock">— in volledig rapport</div>'
        f'</div>'
        for num, name in locked_modules
    )

    return f"""<section class="page">
  {_page_header()}
  <div class="cta-page">
    <div class="module-label">Voor jouw eigen vacature</div>
    <h2>Wat krijg je in het<br><span class="accent">volledige rapport?</span></h2>
    <p class="deck">Dit voorbeeld toont 3 hoogtepunten. Het volledige rapport heeft <strong>8 modules + complete herschrijving</strong> — hieronder de complete inhoud:</p>
    <div class="locked-modules">
      {locked_html}
    </div>
    <div class="usp-grid">
      <div><div class="v">8</div><div class="l">Modules</div></div>
      <div><div class="v">&lt;2u</div><div class="l">Levertijd</div></div>
      <div><div class="v">1</div><div class="l">Gratis analyse</div></div>
    </div>
    <a class="cta-button" href="https://kandidatentekort.nl/?utm_source=sample-pdf&amp;utm_medium=pdf&amp;utm_campaign=cta_back">Krijg jouw rapport in 2u &rarr;</a>
    <div style="font-size:10pt;color:{MUTED};margin-top:14pt">Eerste analyse gratis &middot; geen creditcard &middot; rapport in je mailbox binnen 2u</div>
  </div>
  <div style="position:absolute;bottom:8mm;left:18mm;right:18mm;border-top:2pt solid {ACCENT};padding-top:8pt;display:flex;justify-content:space-between;align-items:baseline;font-size:9pt">
    <div style="color:{INK}"><strong style="color:{ACCENT};font-weight:700">Recruitin B.V.</strong> &middot; warts@recruitin.nl &middot; 06 14 31 45 93 &middot; kandidatentekort.nl</div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:8pt;color:{MUTED};letter-spacing:0.1em;text-transform:uppercase">03 / {TOTAL_PAGES:02d}</div>
  </div>
</section>"""


# ── Document assembly ────────────────────────────────────────────────────────
def render_print_html(lead: dict, analysis: dict) -> str:
    pages = [
        _page_cover(lead, analysis),
        _page_highlights(analysis),
        _page_cta_back(lead, analysis),
    ]
    body = "\n".join(pages)
    return (
        '<!doctype html><html lang="nl"><head>'
        '<meta charset="utf-8">'
        '<title>Vacature Analyse — Voorbeeld</title>'
        f'<style>{_BASE_CSS}</style>'
        '</head><body>'
        f'{body}'
        '</body></html>'
    )
