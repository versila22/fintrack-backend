"""
All FinTrack API endpoints in a single router.
"""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from .database import get_session
from .models import Account, Transaction, Category, Subscription, APIBudget
from .config import settings
from .insights import generate_insights
from .powens import powens_client
from .categorizer import categorize

router = APIRouter()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@router.get("/health")
def health():
    accounts = powens_client.get_accounts()
    mode = "live" if accounts is not None else "demo"
    return {"status": "ok", "mode": mode}


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------

@router.get("/accounts", response_model=list[Account])
def list_accounts(session: Session = Depends(get_session)):
    return session.exec(select(Account)).all()


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

@router.get("/transactions", response_model=list[Transaction])
def list_transactions(
    account_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    stmt = select(Transaction)
    if account_id:
        stmt = stmt.where(Transaction.account_id == account_id)
    stmt = stmt.order_by(Transaction.date.desc()).offset(offset).limit(limit)
    return session.exec(stmt).all()


@router.get("/transactions/stats")
def transaction_stats(session: Session = Depends(get_session)):
    today = date.today()
    month_str = today.strftime("%Y-%m")

    transactions = session.exec(select(Transaction)).all()
    month_txs = [
        tx for tx in transactions
        if tx.date.year == today.year and tx.date.month == today.month
    ]

    by_category: dict[str, float] = {}
    total_expenses = 0.0
    total_income = 0.0

    for tx in month_txs:
        cat = tx.category.value
        if tx.amount < 0:
            by_category[cat] = by_category.get(cat, 0.0) + abs(tx.amount)
            total_expenses += abs(tx.amount)
        else:
            total_income += tx.amount

    return {
        "by_category": by_category,
        "total_expenses": round(total_expenses, 2),
        "total_income": round(total_income, 2),
        "month": month_str,
    }


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------

@router.get("/subscriptions", response_model=list[Subscription])
def list_subscriptions(session: Session = Depends(get_session)):
    return session.exec(select(Subscription)).all()


@router.post("/subscriptions", response_model=Subscription)
def create_subscription(sub: Subscription, session: Session = Depends(get_session)):
    session.add(sub)
    session.commit()
    session.refresh(sub)
    return sub


# ---------------------------------------------------------------------------
# API Budget
# ---------------------------------------------------------------------------

@router.get("/api-budget")
def get_api_budget(session: Session = Depends(get_session)):
    budgets = session.exec(select(APIBudget)).all()
    total_budget = sum(b.monthly_budget for b in budgets)
    total_spent = sum(b.current_month_spent for b in budgets)
    percentage = round((total_spent / total_budget * 100) if total_budget > 0 else 0.0, 1)
    return {
        "budgets": [b.model_dump() for b in budgets],
        "total_budget": round(total_budget, 2),
        "total_spent": round(total_spent, 2),
        "percentage": percentage,
    }


@router.put("/api-budget/{provider}", response_model=APIBudget)
def update_api_budget(provider: str, monthly_budget: float, session: Session = Depends(get_session)):
    budget = session.exec(select(APIBudget).where(APIBudget.provider == provider)).first()
    if not budget:
        raise HTTPException(status_code=404, detail=f"Provider '{provider}' not found")
    budget.monthly_budget = monthly_budget
    session.add(budget)
    session.commit()
    session.refresh(budget)
    return budget


# ---------------------------------------------------------------------------
# Insights
# ---------------------------------------------------------------------------

@router.get("/insights")
def get_insights(session: Session = Depends(get_session)):
    transactions = session.exec(select(Transaction)).all()
    return generate_insights(transactions, settings.salary_amount)


# ---------------------------------------------------------------------------
# Sync (Powens → DB)
# ---------------------------------------------------------------------------

@router.post("/sync")
def sync_powens(session: Session = Depends(get_session)):
    accounts = powens_client.get_accounts()
    if accounts is None:
        return {"synced": 0, "mode": "demo"}

    synced = 0

    for acc in accounts:
        account = Account(
            id=str(acc["id"]),
            name=acc.get("name", "Compte"),
            type=acc.get("type", "personal"),
            balance=acc.get("balance", 0.0),
            currency=acc.get("currency", "EUR"),
        )
        existing = session.get(Account, account.id)
        if existing:
            existing.balance = account.balance
            existing.name = account.name
            session.add(existing)
        else:
            session.add(account)

        raw_txs = powens_client.get_transactions(acc["id"]) or []
        for raw in raw_txs:
            tx_id = str(raw["id"])
            if session.get(Transaction, tx_id):
                continue
            amount = float(raw.get("value", 0))
            desc = raw.get("simplified_wording") or raw.get("wording") or ""
            tx_date = date.fromisoformat(raw["date"][:10]) if "date" in raw else date.today()
            tx = Transaction(
                id=tx_id,
                account_id=str(acc["id"]),
                date=tx_date,
                amount=amount,
                description=desc,
                category=categorize(desc, amount),
            )
            session.add(tx)
            synced += 1

    session.commit()
    return {"synced": synced, "mode": "live"}
