"""
────────────────────────────────────────────────────────────────
SNIPPET DA AGGIUNGERE A main.py
────────────────────────────────────────────────────────────────
Incolla questi import in cima al file (dopo gli import esistenti)
e poi i 3 endpoint nel corpo dell'app FastAPI.
────────────────────────────────────────────────────────────────
"""

# ─── AGGIUNGERE AGLI IMPORT ESISTENTI ───────────────────────────────────────

from billing import create_recurring_charge, activate_charge, verify_webhook_hmac
import os
import json

# Aggiungi questa variabile d'ambiente su Railway:
# SHOPIFY_WEBHOOK_SECRET = <il secret che Shopify ti darà quando registri il webhook>
WEBHOOK_SECRET = os.environ.get("SHOPIFY_WEBHOOK_SECRET", "")

# URL base del tuo backend Railway (già ce l'hai come env var o hardcoded)
BACKEND_URL = os.environ.get("BACKEND_URL", "https://web-production-1cd3c.up.railway.app")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://sentiment-sniper-production.up.railway.app")


# ─── ENDPOINT 1: Avvia il flusso di billing dopo OAuth ──────────────────────
# Questo endpoint va chiamato DOPO che hai ottenuto l'access_token nell'OAuth callback.
# Invece di redirigere subito alla dashboard Streamlit, redirigi prima qui.

@app.get("/billing/initiate")
async def billing_initiate(shop: str, token: str):
    """
    Crea il RecurringApplicationCharge e redirigi il merchant
    alla pagina di conferma Shopify.

    Parametri:
        shop  — es. my-store.myshopify.com
        token — access token del merchant (passato come query param temporaneo)
    """
    return_url = f"{BACKEND_URL}/billing/callback?shop={shop}&token={token}"

    try:
        charge = await create_recurring_charge(
            shop=shop,
            access_token=token,
            return_url=return_url,
        )
    except Exception as e:
        return {"error": str(e)}

    # Redirige il merchant alla pagina Shopify dove accetta il piano
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=charge["confirmation_url"])


# ─── ENDPOINT 2: Callback dopo che il merchant accetta il piano ─────────────

@app.get("/billing/callback")
async def billing_callback(shop: str, token: str, charge_id: int):
    """
    Shopify chiama questo URL dopo che il merchant ha accettato (o rifiutato).
    Se accettato → attiva il charge → redirigi alla dashboard.
    Se rifiutato (charge_id mancante o status declined) → mostra errore.
    """
    from fastapi.responses import RedirectResponse

    try:
        result = await activate_charge(
            shop=shop,
            access_token=token,
            charge_id=charge_id,
        )
    except Exception as e:
        # Il merchant ha rifiutato o c'è stato un errore
        return RedirectResponse(url=f"{FRONTEND_URL}?billing_error=true&shop={shop}")

    if result["status"] == "active":
        # ✅ Tutto ok — qui idealmente salvi charge_id + shop su DB
        # Per ora logga e redirigi alla dashboard
        print(f"[BILLING] ✅ {shop} attivato — charge_id={result['charge_id']}, trial_ends={result['trial_ends_on']}")
        return RedirectResponse(url=f"{FRONTEND_URL}?shop={shop}&billing=active")
    else:
        print(f"[BILLING] ❌ {shop} — status={result['status']}")
        return RedirectResponse(url=f"{FRONTEND_URL}?billing_error=true&shop={shop}")


# ─── ENDPOINT 3: Webhook app/uninstalled ────────────────────────────────────

@app.post("/webhooks/app-uninstalled")
async def webhook_app_uninstalled(request: Request):
    """
    Shopify chiama questo webhook quando un merchant disinstalla l'app.
    Obbligatorio per la submission all'App Store.

    Cosa fa:
    - Verifica la firma HMAC
    - Logga la disinstallazione (in futuro: cancella i dati del merchant dal DB)
    """
    from fastapi.responses import JSONResponse

    body = await request.body()
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256", "")

    if not verify_webhook_hmac(body, hmac_header, WEBHOOK_SECRET):
        return JSONResponse(status_code=401, content={"error": "HMAC non valido"})

    try:
        data = json.loads(body)
        shop = data.get("myshopify_domain", "unknown")
        print(f"[WEBHOOK] 🗑️ App disinstallata da: {shop}")
        # TODO: quando avrai il DB → cancella token e dati del merchant
    except Exception as e:
        print(f"[WEBHOOK] Errore parsing: {e}")

    # Shopify si aspetta sempre 200 OK
    return JSONResponse(status_code=200, content={"ok": True})


# ─── MODIFICA AL CALLBACK OAUTH ESISTENTE ────────────────────────────────────
# Nel tuo callback OAuth esistente (es. /auth/callback), dopo aver ottenuto
# l'access_token, invece di redirigere a Streamlit redirigi così:
#
#   return RedirectResponse(
#       url=f"{BACKEND_URL}/billing/initiate?shop={shop}&token={access_token}"
#   )
#
# Questo fa partire il flusso di billing subito dopo il login.
