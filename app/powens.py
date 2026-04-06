"""
Client Powens open banking (sandbox).
Returns None on any error so the backend can fall back to demo mode.
"""
from datetime import date
from typing import Optional
import httpx
from .config import settings


class PowensClient:
    def __init__(self):
        self.base_url = settings.powens_base_url
        self.client_id = settings.powens_client_id
        self.client_secret = settings.powens_client_secret
        self._token: Optional[str] = None

    def _authenticate(self) -> Optional[str]:
        if not self.client_id or not self.client_secret:
            return None
        try:
            resp = httpx.post(
                f"{self.base_url}/auth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=10,
            )
            if resp.status_code == 200:
                return resp.json().get("access_token")
        except Exception:
            pass
        return None

    def _get_token(self) -> Optional[str]:
        if not self._token:
            self._token = self._authenticate()
        return self._token

    def get_accounts(self) -> Optional[list]:
        token = self._get_token()
        if not token:
            return None
        try:
            resp = httpx.get(
                f"{self.base_url}/users/me/accounts",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            if resp.status_code == 200:
                return resp.json().get("accounts", [])
        except Exception:
            pass
        return None

    def get_transactions(self, account_id: str, min_date: Optional[date] = None) -> Optional[list]:
        token = self._get_token()
        if not token:
            return None
        params = {}
        if min_date:
            params["min_date"] = min_date.isoformat()
        try:
            resp = httpx.get(
                f"{self.base_url}/users/me/transactions",
                headers={"Authorization": f"Bearer {token}"},
                params={"id_account": account_id, **params},
                timeout=10,
            )
            if resp.status_code == 200:
                return resp.json().get("transactions", [])
        except Exception:
            pass
        return None


powens_client = PowensClient()
