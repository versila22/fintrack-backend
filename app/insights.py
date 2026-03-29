"""
Insight generation for FinTrack.
Uses static rules by default; enriches with Gemini 2.5 Flash if API key is set.
"""
from datetime import date
from .models import Category
from .config import settings


def _expenses_by_category(transactions: list) -> dict:
    by_cat: dict[str, float] = {}
    for tx in transactions:
        # Only current month
        tx_date = tx.date if isinstance(tx.date, date) else date.fromisoformat(str(tx.date))
        today = date.today()
        if tx_date.year != today.year or tx_date.month != today.month:
            continue
        if tx.amount < 0:
            cat = tx.category.value if hasattr(tx.category, "value") else str(tx.category)
            by_cat[cat] = by_cat.get(cat, 0.0) + abs(tx.amount)
    return by_cat


def _static_insights(by_category: dict, salary: float) -> list[dict]:
    insights = []
    total_expenses = sum(by_category.values())

    # Per-category warnings
    for cat, amount in by_category.items():
        if cat == Category.REVENUS.value:
            continue
        if amount > salary * 0.30:
            insights.append({
                "type": "warning",
                "title": f"{cat} élevé",
                "message": f"Vous avez dépensé {amount:.2f}€ en {cat} ce mois-ci, soit plus de 30% de votre salaire.",
            })

    # FinOps warning for API_TECH
    api_tech = by_category.get(Category.API_TECH.value, 0.0)
    if api_tech > 80:
        insights.append({
            "type": "warning",
            "title": "Budget API Tech dépassé",
            "message": f"Vos dépenses API tech atteignent {api_tech:.2f}€ ce mois-ci. Pensez à optimiser vos appels et budgets FinOps.",
        })

    # Subscription tip
    abonnements = by_category.get(Category.ABONNEMENTS.value, 0.0)
    if abonnements > 100:
        insights.append({
            "type": "tip",
            "title": "Abonnements à auditer",
            "message": f"Vous avez {abonnements:.2f}€ d'abonnements ce mois-ci. Pensez à les auditer et à supprimer ceux inutilisés.",
        })

    # Positive insight if under budget
    if total_expenses < salary:
        savings = salary - total_expenses
        insights.append({
            "type": "info",
            "title": "Bonne gestion ce mois-ci 🎉",
            "message": f"Vous êtes en dessous de votre salaire avec {savings:.2f}€ d'épargne potentielle ce mois-ci.",
        })

    return insights


def _gemini_enrichment(static_insights: list[dict], by_category: dict, salary: float) -> list[dict]:
    """Call Gemini 2.5 Flash to add extra insights. Appends to existing list."""
    try:
        import google.genai as genai

        client = genai.Client(api_key=settings.gemini_api_key)

        summary_lines = [f"- {cat}: {amount:.2f}€" for cat, amount in by_category.items()]
        summary = "\n".join(summary_lines)
        existing = "\n".join(f"- [{i['type']}] {i['title']}: {i['message']}" for i in static_insights)

        prompt = f"""Tu es un conseiller financier personnel pour une appli de gestion de budget.
Voici les dépenses du mois courant par catégorie :
{summary}

Salaire mensuel : {salary:.2f}€

Insights déjà générés :
{existing}

Génère 1 à 2 insights supplémentaires pertinents et actionnables (en français), au format JSON liste :
[{{"type": "warning|tip|info", "title": "...", "message": "..."}}]

Réponds UNIQUEMENT avec le JSON, sans markdown ni explication."""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        text = response.text.strip()
        # Strip markdown code blocks if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        import json
        extra = json.loads(text)
        if isinstance(extra, list):
            return static_insights + extra
    except Exception:
        pass
    return static_insights


def generate_insights(transactions: list, salary: float) -> list[dict]:
    by_category = _expenses_by_category(transactions)
    insights = _static_insights(by_category, salary)

    if settings.gemini_api_key:
        insights = _gemini_enrichment(insights, by_category, salary)

    return insights
