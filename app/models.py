from enum import Enum
from datetime import date, datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class Category(str, Enum):
    ALIMENTATION = "Alimentation"
    LOGEMENT = "Logement"
    TRANSPORT = "Transport"
    LOISIRS = "Loisirs"
    ABONNEMENTS = "Abonnements"
    SANTE = "Santé"
    API_TECH = "API Tech"
    REVENUS = "Revenus"
    AUTRES = "Autres"


class Account(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    type: str  # "personal" | "business"
    balance: float = 0.0
    currency: str = "EUR"
    last_synced: datetime = Field(default_factory=datetime.utcnow)


class Transaction(SQLModel, table=True):
    id: str = Field(primary_key=True)
    account_id: str
    date: date
    amount: float
    description: str
    category: Category = Category.AUTRES
    is_recurring: bool = False


class Subscription(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    amount: float
    frequency: str  # "monthly" | "annual"
    next_date: date
    account_id: str
    is_active: bool = True


class APIBudget(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    provider: str  # "Anthropic", "Google Cloud", "ElevenLabs", "OpenAI", "Autres"
    monthly_budget: float
    current_month_spent: float = 0.0
