import os
import hmac
import hashlib
import secrets
import httpx
import uvicorn

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from billing import create_recurring_charge, activate_charge, verify_webhook_hmac
import json

load_dotenv()

app = FastAPI(title="Sentiment Sniper")

# ── Config ────────────────────────────────────────────────────────────────────
SHOPIFY_API_KEY    = os.getenv("SHOPIFY_API_KEY", "")
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET", "")
APP_URL            = os.getenv("APP_URL", "http://localhost:8000")
WEBHOOK_SECRET     = os.environ.get("SHOPIFY_WEBHOOK_SECRET", "")
BACKEND_URL        = os.environ.get("BACKEND_URL", "https://web-production-1cd3c.up.railway.app")
FRONTEND_URL       = os.environ.get("FRONTEND_URL", "https://sentiment-sniper-production.up.railway.app")
SCOPES             ="read_products,read_orders,read_all_orders"

# In-memory nonce store (replace with Redis / DB for production)
_pending_nonces: set[str] = set()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _verify_hmac(params: dict) -> bool:
    received_hmac = params.get("hmac", "")
    filtered = {k: v for k, v in params.items() if k != "hmac"}
    sorted_params = "&".join(f"{k}={v}" for k, v in sorted(filtered.items()))
    digest = hmac.new(
        SHOPIFY_API_SECRET.encode("utf-8"),
        sorted_params.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(digest, received_hmac)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"status": "Sentiment Sniper is running 🎯"}


@app.get("/debug")
async def debug():
    return {
        "api_key": SHOPIFY_API_KEY,
        "app_url": APP_URL,
    }


@app.get("/login")
async def login(shop: str | None = None):
    if not shop:
        raise HTTPException(status_code=400, detail="Missing 'shop' query parameter.")

    if not shop.endswith(".myshopify.com"):
        raise HTTPException(status_code=400, detail="Invalid shop domain.")

    nonce = secrets.token_urlsafe(16)
    _pending_nonces.add(nonce)

    redirect_uri = f"{APP_URL}/callback"
    auth_url = (
        f"https://{shop}/admin/oauth/authorize"
        f"?client_id={SHOPIFY_API_KEY}"
        f"&scope={SCOPES}"
        f"&redirect_uri={redirect_uri}"
        f"&state={nonce}"
    )
    return RedirectResponse(url=auth_url)


@app.get("/callback")
async def callback(request: Request):
    params = dict(request.query_params)

    # 1. Validate HMAC
    if not _verify_hmac(params):
        raise HTTPException(status_code=403, detail="HMAC validation failed.")

    # 2. Validate nonce (state)
    state = params.get("state", "")
    if state not in _pending_nonces:
        raise HTTPException(status_code=403, detail="Invalid or expired state nonce.")
    _pending_nonces.discard(state)

    # 3. Validate shop domain
    shop = params.get("shop", "")
    if not shop.endswith(".myshopify.com"):
        raise HTTPException(status_code=400, detail="Invalid shop domain.")

    # 4. Exchange code for access token
    code = params.get("code", "")
    token_url = f"https://{shop}/admin/oauth/access_token"
    payload = {
        "client_id":     SHOPIFY_API_KEY,
        "client_secret": SHOPIFY_API_SECRET,
        "code":          code,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, json=payload)

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Token exchange failed: {response.text}",
        )

    token_data = response.json()
    access_token = token_data.get("access_token")

    if not access_token:
        raise HTTPException(status_code=502, detail="No access token in Shopify response.")

    print(f"\n✅  OAuth complete!")
    print(f"    Shop:  {shop}")
    print(f"    Token: {access_token}\n")

    return RedirectResponse(
        url=f"{BACKEND_URL}/billing/initiate?shop={shop}&token={access_token}"
    )


@app.get("/billing/initiate")
async def billing_initiate(shop: str, token: str):
    return_url = f"{BACKEND_URL}/billing/callback?shop={shop}&token={token}"
    try:
        charge = await create_recurring_charge(shop=shop, access_token=token, return_url=return_url)
    except Exception as e:
        return {"error": str(e)}
    return RedirectResponse(url=charge["confirmation_url"])


@app.get("/billing/callback")
async def billing_callback(shop: str, token: str, charge_id: int):
    try:
        result = await activate_charge(shop=shop, access_token=token, charge_id=charge_id)
    except Exception as e:
        return RedirectResponse(url=f"{FRONTEND_URL}?billing_error=true&shop={shop}")
    if result["status"] == "active":
        print(f"[BILLING] ✅ {shop} attivato — charge_id={result['charge_id']}, trial_ends={result['trial_ends_on']}")
        return RedirectResponse(url=f"{FRONTEND_URL}?shop={shop}&billing=active")
    else:
        return RedirectResponse(url=f"{FRONTEND_URL}?billing_error=true&shop={shop}")


@app.post("/webhooks/app-uninstalled")
async def webhook_app_uninstalled(request: Request):
    from fastapi.responses import JSONResponse
    body = await request.body()
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256", "")
    if not verify_webhook_hmac(body, hmac_header, WEBHOOK_SECRET):
        return JSONResponse(status_code=401, content={"error": "HMAC non valido"})
    try:
        data = json.loads(body)
        shop = data.get("myshopify_domain", "unknown")
        print(f"[WEBHOOK] 🗑️ App disinstallata da: {shop}")
    except Exception as e:
        print(f"[WEBHOOK] Errore parsing: {e}")
    return JSONResponse(status_code=200, content={"ok": True})


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)