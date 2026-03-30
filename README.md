# 💰 FinTrack Backend

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-latest-green?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Gemini 2.5 Flash](https://img.shields.io/badge/Gemini-2.5%20Flash-orange?logo=google)](https://deepmind.google/technologies/gemini/)
[![Open Banking](https://img.shields.io/badge/Open%20Banking-Powens-6366f1)](https://www.powens.com/)
[![License](https://img.shields.io/badge/License-Personal%20Use-lightgrey)](LICENSE)

> **API REST de gestion budgétaire personnelle avec open banking (Powens), catégorisation IA et insights Gemini 2.5 Flash.**

---

## 🎯 Compétences démontrées

| Domaine | Implémentation |
|---------|----------------|
| **Open Banking** | Intégration Powens (agrégation bancaire) — mode démo automatique si clés invalides |
| **LLM appliqué** | Gemini 2.5 Flash pour insights budgétaires enrichis + catégorisation hybride |
| **API REST** | FastAPI + SQLModel + SQLite — endpoints complets avec documentation OpenAPI |
| **FinOps IA** | Suivi des budgets API par fournisseur avec seuils configurables dans l'UI |
| **Architecture propre** | Séparation modèles / routeurs / config, mode demo/live transparent |
| **Données de démo** | Seed automatique pour une démo entretien sans dépendances externes |

---

API REST FastAPI pour l'application FinTrack — gestion budgétaire personnelle avec open banking Powens et insights Gemini.

## Architecture (5 lignes)

- **FastAPI** + **SQLModel** + **SQLite** — léger, pas de migrations
- **Powens sandbox** pour l'open banking ; mode démo automatique si clés invalides
- **Catégorisation déterministe** (règles mots-clés) + enrichissement optionnel Gemini 2.5 Flash
- **Insights statiques** ou enrichis IA selon présence de `GEMINI_API_KEY`
- Un seul fichier `routers.py` pour tous les endpoints, `models.py` pour tous les modèles

## Installation

```bash
cd fintrack-backend

# Créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt

# Copier et éditer les variables d'environnement (optionnel)
cp .env.example .env
```

## Seed (données de démo)

```bash
python seed_data.py
# ✅ Seed complete: N transactions, 5 subscriptions, 5 API budgets.
```

## Lancement

```bash
uvicorn app.main:app --reload
```

API disponible sur http://localhost:8000  
Documentation interactive : http://localhost:8000/docs

## Endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/health` | Statut + mode demo/live |
| GET | `/accounts` | Liste des comptes |
| GET | `/transactions` | Transactions (params: account_id, limit, offset) |
| GET | `/transactions/stats` | Stats du mois par catégorie |
| GET | `/subscriptions` | Liste des abonnements |
| POST | `/subscriptions` | Créer un abonnement manuel |
| GET | `/api-budget` | Budgets API + totaux |
| PUT | `/api-budget/{provider}` | Mettre à jour le budget d'un fournisseur |
| GET | `/insights` | Insights IA du mois |
| POST | `/sync` | Synchroniser depuis Powens |

## Variables d'environnement

| Variable | Défaut | Description |
|----------|--------|-------------|
| `GEMINI_API_KEY` | `` | Clé Gemini pour insights enrichis (optionnel) |
| `POWENS_CLIENT_ID` | `71972119` | ID client Powens sandbox |
| `POWENS_CLIENT_SECRET` | `znKIZM...` | Secret Powens sandbox |
| `SALARY_AMOUNT` | `3500.0` | Salaire de référence pour les insights |
| `API_BUDGET_TOTAL` | `100.0` | Budget total API mensuel |

## Mode démo vs live

- **Demo** : aucune connexion Powens, données seed uniquement
- **Live** : sync automatique depuis Powens si les clés sont valides

Le backend démarre dans les deux cas sans erreur.
