"""
All FinTrack API endpoints in a single router.
"""
from datetime import date
from uuid import uuid4
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from .database import get_session
from .models import (
    Account, AccountCreate, AccountUpdate,
    Transaction, TransactionCreate, TransactionUpdate,
    Subscription, SubscriptionCreate, SubscriptionUpdate,
    APIBudget, UserCategory, UserCategoryCreate, UserCategoryUpdate,
    User, UserCreate, UserRead, Token,
)
from .config import settings
from .insights import generate_insights
from .powens import powens_client
from .categorizer import categorize
from .auth import hash_password, verify_password, create_access_token, get_current_user

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
# Auth
# ---------------------------------------------------------------------------

@router.post("/auth/register", response_model=UserRead, status_code=201)
def register(payload: UserCreate, session: Session = Depends(get_session)):
    existing = session.exec(select(User).where(User.email == payload.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email déjà utilisé")
    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.post("/auth/login", response_model=Token)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    user = session.exec(select(User).where(User.email == form.username)).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    token = create_access_token(user.id)
    return Token(access_token=token)


@router.get("/auth/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)):
    return current_user


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------

@router.get("/accounts", response_model=list[Account])
def list_accounts(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return session.exec(select(Account).where(Account.user_id == current_user.id)).all()


@router.post("/accounts", response_model=Account, status_code=201)
def create_account(
    payload: AccountCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    account = Account(
        id=f"acc_{uuid4().hex[:12]}",
        user_id=current_user.id,
        name=payload.name,
        type=payload.type,
        balance=payload.balance,
        currency=payload.currency,
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


@router.get("/accounts/{account_id}", response_model=Account)
def get_account(
    account_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    account = session.get(Account, account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Compte introuvable")
    return account


@router.put("/accounts/{account_id}", response_model=Account)
def update_account(
    account_id: str,
    payload: AccountUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    account = session.get(Account, account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Compte introuvable")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(account, key, value)

    session.add(account)
    session.commit()
    session.refresh(account)
    return account


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    account = session.get(Account, account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Compte introuvable")

    session.delete(account)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

@router.get("/transactions", response_model=list[Transaction])
def list_transactions(
    account_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Transaction).where(Transaction.user_id == current_user.id)
    if account_id:
        stmt = stmt.where(Transaction.account_id == account_id)
    stmt = stmt.order_by(Transaction.date.desc()).offset(offset).limit(limit)
    return session.exec(stmt).all()


@router.post("/transactions", response_model=Transaction, status_code=201)
def create_transaction(
    payload: TransactionCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    account = session.get(Account, payload.account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Compte introuvable")

    transaction = Transaction(
        id=f"tx_{uuid4().hex[:12]}",
        user_id=current_user.id,
        account_id=payload.account_id,
        date=payload.date,
        amount=payload.amount,
        description=payload.description,
        category=payload.category,
        is_recurring=payload.is_recurring,
    )
    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return transaction


@router.get("/transactions/{transaction_id}", response_model=Transaction)
def get_transaction(
    transaction_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    transaction = session.get(Transaction, transaction_id)
    if not transaction or transaction.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Transaction introuvable")
    return transaction


@router.put("/transactions/{transaction_id}", response_model=Transaction)
def update_transaction(
    transaction_id: str,
    payload: TransactionUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    transaction = session.get(Transaction, transaction_id)
    if not transaction or transaction.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Transaction introuvable")

    updates = payload.model_dump(exclude_unset=True)
    if "account_id" in updates:
        account = session.get(Account, updates["account_id"])
        if not account or account.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Compte introuvable")

    for key, value in updates.items():
        setattr(transaction, key, value)

    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return transaction


@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    transaction = session.get(Transaction, transaction_id)
    if not transaction or transaction.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Transaction introuvable")

    session.delete(transaction)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/transactions/stats")
def transaction_stats(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    today = date.today()
    month_str = today.strftime("%Y-%m")

    transactions = session.exec(
        select(Transaction).where(Transaction.user_id == current_user.id)
    ).all()
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
def list_subscriptions(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return session.exec(
        select(Subscription).where(Subscription.user_id == current_user.id)
    ).all()


@router.get("/subscriptions/{subscription_id}", response_model=Subscription)
def get_subscription(
    subscription_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    subscription = session.get(Subscription, subscription_id)
    if not subscription or subscription.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Abonnement introuvable")
    return subscription


@router.post("/subscriptions", response_model=Subscription, status_code=201)
def create_subscription(
    payload: SubscriptionCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    account = session.get(Account, payload.account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Compte introuvable")

    sub = Subscription(user_id=current_user.id, **payload.model_dump())
    session.add(sub)
    session.commit()
    session.refresh(sub)
    return sub


@router.put("/subscriptions/{subscription_id}", response_model=Subscription)
def update_subscription(
    subscription_id: int,
    payload: SubscriptionUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    subscription = session.get(Subscription, subscription_id)
    if not subscription or subscription.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Abonnement introuvable")

    updates = payload.model_dump(exclude_unset=True)
    if "account_id" in updates:
        account = session.get(Account, updates["account_id"])
        if not account or account.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Compte introuvable")

    for key, value in updates.items():
        setattr(subscription, key, value)

    session.add(subscription)
    session.commit()
    session.refresh(subscription)
    return subscription


@router.delete("/subscriptions/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(
    subscription_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    subscription = session.get(Subscription, subscription_id)
    if not subscription or subscription.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Abonnement introuvable")

    session.delete(subscription)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------


@router.get("/categories", response_model=list[UserCategory])
def list_categories(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return session.exec(
        select(UserCategory).where(UserCategory.user_id == current_user.id)
    ).all()


@router.post("/categories", response_model=UserCategory, status_code=201)
def create_category(
    payload: UserCategoryCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    category = UserCategory(user_id=current_user.id, **payload.model_dump())
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


@router.get("/categories/{category_id}", response_model=UserCategory)
def get_category(
    category_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    category = session.get(UserCategory, category_id)
    if not category or category.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")
    return category


@router.put("/categories/{category_id}", response_model=UserCategory)
def update_category(
    category_id: str,
    payload: UserCategoryUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    category = session.get(UserCategory, category_id)
    if not category or category.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, key, value)

    session.add(category)
    session.commit()
    session.refresh(category)
    return category


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    category = session.get(UserCategory, category_id)
    if not category or category.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")

    session.delete(category)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# API Budget
# ---------------------------------------------------------------------------

@router.get("/api-budget")
def get_api_budget(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    budgets = session.exec(
        select(APIBudget).where(APIBudget.user_id == current_user.id)
    ).all()
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
def update_api_budget(
    provider: str,
    monthly_budget: float,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    budget = session.exec(
        select(APIBudget)
        .where(APIBudget.provider == provider)
        .where(APIBudget.user_id == current_user.id)
    ).first()
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
def get_insights(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    transactions = session.exec(
        select(Transaction).where(Transaction.user_id == current_user.id)
    ).all()
    return generate_insights(transactions, settings.salary_amount)


# ---------------------------------------------------------------------------
# Sync (Powens → DB)
# ---------------------------------------------------------------------------

@router.post("/sync")
def sync_powens(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    accounts = powens_client.get_accounts()
    if accounts is None:
        return {"synced": 0, "mode": "demo"}

    synced = 0

    for acc in accounts:
        account = Account(
            id=str(acc["id"]),
            user_id=current_user.id,
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
                user_id=current_user.id,
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
