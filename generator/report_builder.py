"""
Report Builder voor Kandidatentekort.
Genereert hosted rapport HTML en email summary via Jinja2 templates.
"""

import os
import re
import sys
from datetime import datetime

from jinja2 import Environment, FileSystemLoader

# Jinja2 environment
_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
_jinja_env = Environment(loader=FileSystemLoader(_TEMPLATE_DIR), autoescape=False)
_jinja_env.globals["enumerate"] = enumerate


def _score_color(score: int) -> str:
    """Bepaal kleur op basis van score."""
    if score >= 75:
        return "#10B981"  # Groen
    elif score >= 60:
        return "#3B82F6"  # Blauw
    elif score >= 45:
        return "#F59E0B"  # Amber
    return "#EF4444"  # Rood


def _score_label(score: int) -> str:
    """Bepaal label op basis van score."""
    if score >= 75:
        return "Sterk"
    elif score >= 60:
        return "Goed"
    elif score >= 45:
        return "Matig"
    return "Verbetering nodig"


def build_hosted_rapport(analysis: dict, bedrijf: str, functie: str) -> str:
    """Render hosted rapport HTML via Jinja2 template."""
    score = analysis.get("overall_score", 0)
    categories = analysis.get("categories", [])
    market_analysis = analysis.get("market_analysis", {})
    salary_benchmark = analysis.get("salary_benchmark", {})
    action_items = analysis.get("action_items", [])
    recommended_channels = analysis.get("recommended_channels", [])
    improved_text = analysis.get("improved_text", "")
    samenvatting = analysis.get("samenvatting", "")

    template = _jinja_env.get_template("kt_hosted_rapport.html")
    return template.render(
        bedrijf=bedrijf,
        functie=functie,
        score=score,
        score_color=_score_color(score),
        score_label=_score_label(score),
        samenvatting=samenvatting,
        categories=categories,
        market_analysis=market_analysis,
        salary_benchmark=salary_benchmark,
        improved_text=improved_text.replace("\n", "<br>") if improved_text else "",
        action_items=action_items,
        recommended_channels=recommended_channels,
        date=datetime.now().strftime("%d %B %Y"),
        year=datetime.now().year,
    )


def build_email_summary(
    analysis: dict,
    bedrijf: str,
    functie: str,
    rapport_url: str = "",
) -> str:
    """Render premium email summary via Jinja2 template."""
    score = analysis.get("overall_score", 0)
    categories = analysis.get("categories", [])
    market_analysis = analysis.get("market_analysis", {})
    action_items = analysis.get("action_items", [])[:3]

    template = _jinja_env.get_template("kt_email.html")
    return template.render(
        bedrijf=bedrijf,
        functie=functie,
        score=score,
        score_color=_score_color(score),
        score_label=_score_label(score),
        categories=categories,
        market_analysis=market_analysis,
        action_items=action_items,
        rapport_url=rapport_url,
    )
