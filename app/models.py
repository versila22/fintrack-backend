from enum import Enum
from datetime import date, datetime, timezone
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


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True


class UserCreate(SQLModel):
    email: str
    password: str


class UserRead(SQLModel):
    id: int
    email: str
    created_at: datetime
    is_active: bool


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Financial models (user-scoped)
# ---------------------------------------------------------------------------

class Account(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    name: str
    type: str  # "personal" | "business"
    balance: float = 0.0
    currency: str = "EUR"
    last_synced: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Transaction(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    account_id: str
    date: date
    amount: float
    description: str
    category: Category = Category.AUTRES
    is_recurring: bool = False


class Subscription(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    name: str
    amount: float
    frequency: str  # "monthly" | "annual"
    next_date: date
    account_id: str
    is_active: bool = True


class APIBudget(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    provider: str  # "Anthropic", "Google Cloud", "ElevenLabs", "OpenAI", "Autres"
    monthly_budget: float
    current_month_spent: float = 0.0
