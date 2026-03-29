"""
Categorize transactions using deterministic rules.
Gemini fallback is intentionally omitted in v1 for simplicity.
"""
from .models import Category

# Keyword → Category mapping (checked in order, case-insensitive)
RULES: list[tuple[list[str], Category]] = [
    (["ANTHROPIC", "OPENAI", "ELEVENLABS", "GOOGLE"], Category.API_TECH),
    (["NETFLIX", "SPOTIFY", "DISNEY", "AMAZON PRIME", "CANAL"], Category.ABONNEMENTS),
    (["CARREFOUR", "LECLERC", "LIDL", "INTERMARCHE", "MONOPRIX", "FRANPRIX", "ALDI"], Category.ALIMENTATION),
    (["SNCF", "UBER", "BOLT", "VELIB", "RATP"], Category.TRANSPORT),
    (["LOYER", "EDF", "ENGIE", "ORANGE", "FREE", "SFR", "BOUYGUES"], Category.LOGEMENT),
    (["PHARMACIE", "MEDECIN", "DOCTEUR", "SECU", "MUTUELLE"], Category.SANTE),
]


def categorize(description: str, amount: float) -> Category:
    desc_upper = description.upper()

    for keywords, category in RULES:
        for kw in keywords:
            if kw in desc_upper:
                return category

    # Large positive amounts = income
    if amount > 500 and amount > 0:
        return Category.REVENUS

    return Category.AUTRES
