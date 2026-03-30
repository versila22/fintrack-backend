"""
Seed script — populates fintrack.db with 90 days of realistic demo data.
Creates a demo user (demo@fintrack.dev / demo1234) if none exists.

Run from the fintrack-backend/ directory:
    python seed_data.py
"""
import os
import sys
import random
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from app.config import settings
from sqlmodel import SQLModel, create_engine, Session, select

engine = create_engine(settings.database_url, echo=False)

from app.models import Account, Transaction, Category, Subscription, APIBudget, User  # noqa: E402
from app.auth import hash_password  # noqa: E402

SQLModel.metadata.create_all(engine)

random.seed(42)

TODAY = date.today()
START = TODAY - timedelta(days=90)

DEMO_EMAIL = "demo@fintrack.dev"
DEMO_PASSWORD = "demo1234"


def date_range(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def build_transactions(user_id: int) -> list[Transaction]:
    txs: list[Transaction] = []
    tx_id = 1

    groceries_stores = ["Carrefour", "Leclerc", "Lidl", "Monoprix", "Franprix"]
    transport_stores = ["SNCF", "Uber"]
    grocery_days_by_week: dict[tuple, list] = {}

    for d in date_range(START, TODAY):
        week_key = (d.year, d.isocalendar()[1])

        if d.day == 28:
            txs.append(Transaction(id=f"tx_{tx_id:04d}", user_id=user_id, account_id="boursorama-courant", date=d, amount=3500.0, description="Virement salaire employeur", category=Category.REVENUS, is_recurring=True))
            tx_id += 1

        if d.day == 1:
            txs.append(Transaction(id=f"tx_{tx_id:04d}", user_id=user_id, account_id="boursorama-courant", date=d, amount=-950.0, description="Loyer mensuel", category=Category.LOGEMENT, is_recurring=True))
            tx_id += 1

        if d.day == 15:
            txs.append(Transaction(id=f"tx_{tx_id:04d}", user_id=user_id, account_id="boursorama-courant", date=d, amount=-13.99, description="Netflix abonnement", category=Category.ABONNEMENTS, is_recurring=True))
            tx_id += 1

        if d.day == 8:
            txs.append(Transaction(id=f"tx_{tx_id:04d}", user_id=user_id, account_id="boursorama-courant", date=d, amount=-9.99, description="Spotify Premium", category=Category.ABONNEMENTS, is_recurring=True))
            tx_id += 1

        if d.day == 5:
            for provider, amount in [("Anthropic", -35.0), ("Google Cloud", -18.0), ("ElevenLabs", -22.0)]:
                txs.append(Transaction(id=f"tx_{tx_id:04d}", user_id=user_id, account_id="boursorama-courant", date=d, amount=amount, description=provider, category=Category.API_TECH, is_recurring=True))
                tx_id += 1

        if week_key not in grocery_days_by_week:
            grocery_days_by_week[week_key] = []
        week_grocery_days = grocery_days_by_week[week_key]
        if len(week_grocery_days) < 3 and d.weekday() not in week_grocery_days:
            if random.random() < 0.45 or (6 - d.weekday()) <= (3 - len(week_grocery_days)):
                store = random.choice(groceries_stores)
                amount = round(-random.uniform(40, 120), 2)
                txs.append(Transaction(id=f"tx_{tx_id:04d}", user_id=user_id, account_id="boursorama-courant", date=d, amount=amount, description=f"Courses {store}", category=Category.ALIMENTATION))
                tx_id += 1
                week_grocery_days.append(d.weekday())

    for month_offset in range(3):
        month_start = date(TODAY.year, TODAY.month, 1) - timedelta(days=30 * month_offset)
        for _ in range(2):
            day = random.randint(1, 28)
            d = date(month_start.year, month_start.month, min(day, 28))
            if d < START or d > TODAY:
                continue
            store = random.choice(transport_stores)
            amount = round(-random.uniform(15, 45), 2)
            txs.append(Transaction(id=f"tx_{tx_id:04d}", user_id=user_id, account_id="boursorama-courant", date=d, amount=amount, description=f"{store} trajet", category=Category.TRANSPORT))
            tx_id += 1

    return txs


def main():
    with Session(engine) as session:
        # --- Get or create demo user ---
        user = session.exec(select(User).where(User.email == DEMO_EMAIL)).first()
        if not user:
            user = User(email=DEMO_EMAIL, hashed_password=hash_password(DEMO_PASSWORD))
            session.add(user)
            session.commit()
            session.refresh(user)
            print(f"✅ Demo user created: {DEMO_EMAIL} / {DEMO_PASSWORD}")
        else:
            print(f"ℹ️  Demo user already exists: {DEMO_EMAIL}")

        uid = user.id

        # Clear existing data for this user
        for model in [Transaction, Subscription, APIBudget, Account]:
            existing = session.exec(select(model).where(model.user_id == uid)).all()
            for item in existing:
                session.delete(item)
        session.commit()

        # --- Accounts ---
        accounts = [
            Account(id=f"boursorama-courant-{uid}", user_id=uid, name="Boursorama Courant", type="personal", balance=4250.0, currency="EUR"),
            Account(id=f"fortuneo-livret-{uid}", user_id=uid, name="Fortuneo Livret", type="personal", balance=8500.0, currency="EUR"),
        ]
        for acc in accounts:
            session.add(acc)

        # Patch account_id in transactions to match user-scoped IDs
        transactions = build_transactions(uid)
        for tx in transactions:
            tx.account_id = f"boursorama-courant-{uid}"
            session.add(tx)

        # --- Subscriptions ---
        next_month = date(TODAY.year, TODAY.month + 1 if TODAY.month < 12 else 1, 1)
        subscriptions = [
            Subscription(user_id=uid, name="Netflix", amount=13.99, frequency="monthly", next_date=date(TODAY.year, TODAY.month, 15) if TODAY.day < 15 else date(next_month.year, next_month.month, 15), account_id=f"boursorama-courant-{uid}"),
            Subscription(user_id=uid, name="Spotify Premium", amount=9.99, frequency="monthly", next_date=date(TODAY.year, TODAY.month, 8) if TODAY.day < 8 else date(next_month.year, next_month.month, 8), account_id=f"boursorama-courant-{uid}"),
            Subscription(user_id=uid, name="Anthropic API", amount=35.0, frequency="monthly", next_date=date(TODAY.year, TODAY.month, 5) if TODAY.day < 5 else date(next_month.year, next_month.month, 5), account_id=f"boursorama-courant-{uid}"),
            Subscription(user_id=uid, name="Google Cloud", amount=18.0, frequency="monthly", next_date=date(TODAY.year, TODAY.month, 5) if TODAY.day < 5 else date(next_month.year, next_month.month, 5), account_id=f"boursorama-courant-{uid}"),
            Subscription(user_id=uid, name="ElevenLabs", amount=22.0, frequency="monthly", next_date=date(TODAY.year, TODAY.month, 5) if TODAY.day < 5 else date(next_month.year, next_month.month, 5), account_id=f"boursorama-courant-{uid}"),
        ]
        for sub in subscriptions:
            session.add(sub)

        # --- API Budgets ---
        api_budgets = [
            APIBudget(user_id=uid, provider="Anthropic", monthly_budget=40.0, current_month_spent=35.0),
            APIBudget(user_id=uid, provider="Google Cloud", monthly_budget=25.0, current_month_spent=18.0),
            APIBudget(user_id=uid, provider="ElevenLabs", monthly_budget=20.0, current_month_spent=22.0),
            APIBudget(user_id=uid, provider="OpenAI", monthly_budget=10.0, current_month_spent=0.0),
            APIBudget(user_id=uid, provider="Autres", monthly_budget=5.0, current_month_spent=0.0),
        ]
        for budget in api_budgets:
            session.add(budget)

        session.commit()

    print(f"✅ Seed complete: {len(transactions)} transactions, {len(subscriptions)} subscriptions, {len(api_budgets)} API budgets.")


if __name__ == "__main__":
    main()
