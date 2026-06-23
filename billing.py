import hmac
import hashlib
import base64
import httpx
from typing import Optional

PLAN_NAME = "Sentiment Sniper Pro"
PLAN_PRICE = "14.99"
PLAN_TRIAL_DAYS = 7


async def create_recurring_charge(shop: str, access_token: str, return_url: str) -> dict:
    url = f"https://{shop}/admin/api/2024-01/recurring_application_charges.json"
    payload = {
        "recurring_application_charge": {
            "name": PLAN_NAME,
            "price": PLAN_PRICE,
            "return_url": return_url,
            "trial_days": PLAN_TRIAL_DAYS,
            "test": True,
        }
    }
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    charge = data["recurring_application_charge"]
    return {
        "charge_id": charge["id"],
        "confirmation_url": charge["confirmation_url"],
        "status": charge["status"],
    }


async def activate_charge(shop: str, access_token: str, charge_id: int) -> dict:
    url = f"https://{shop}/admin/api/2024-01/recurring_application_charges/{charge_id}/activate.json"
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
    }
    payload = {
        "recurring_application_charge": {
            "id": charge_id,
        }
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    charge = data["recurring_application_charge"]
    return {
        "charge_id": charge["id"],
        "status": charge["status"],
        "trial_ends_on": charge.get("trial_ends_on"),
        "billing_on": charge.get("billing_on"),
    }


async def get_charge_status(shop: str, access_token: str, charge_id: int) -> Optional[str]:
    url = f"https://{shop}/admin/api/2024-01/recurring_application_charges/{charge_id}.json"
    headers = {"X-Shopify-Access-Token": access_token}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
    return data["recurring_application_charge"]["status"]


def verify_webhook_hmac(body: bytes, hmac_header: str, secret: str) -> bool:
    digest = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).digest()
    computed = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(computed, hmac_header)