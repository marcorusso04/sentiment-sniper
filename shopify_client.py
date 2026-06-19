import os
import httpx
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
SHOP_DOMAIN         = os.getenv("SHOP_DOMAIN", "")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
API_VERSION         = "2026-04"

BASE_URL = f"https://{SHOP_DOMAIN}/admin/api/{API_VERSION}"

HEADERS = {
    "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
    "Content-Type": "application/json",
}


# ── Products ──────────────────────────────────────────────────────────────────

async def get_products(limit: int = 50) -> list[dict]:
    """
    Fetch products from the Shopify store.
    Returns a list of product dicts with id, title, handle, status.
    """
    url = f"{BASE_URL}/products.json?limit={limit}&fields=id,title,handle,status"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=HEADERS)

    response.raise_for_status()
    products = response.json().get("products", [])

    print(f"✅  Fetched {len(products)} products from {SHOP_DOMAIN}")
    return products


# ── Orders ────────────────────────────────────────────────────────────────────

async def get_orders(limit: int = 50, status: str = "any") -> list[dict]:
    """
    Fetch orders from the Shopify store.
    Returns a list of order dicts with id, name, email, total_price, created_at.
    """
    url = (
        f"{BASE_URL}/orders.json"
        f"?limit={limit}"
        f"&status={status}"
        f"&fields=id,name,email,total_price,created_at,line_items"
    )

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=HEADERS)

    response.raise_for_status()
    orders = response.json().get("orders", [])

    print(f"✅  Fetched {len(orders)} orders from {SHOP_DOMAIN}")
    return orders


# ── Quick test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio

    async def main():
        print("\n── Products ──────────────────────────────")
        products = await get_products()
        for p in products:
            print(f"  [{p['id']}] {p['title']} — {p['status']}")

        print("\n── Orders ────────────────────────────────")
        orders = await get_orders()
        for o in orders:
            print(f"  [{o['id']}] {o['name']} — €{o['total_price']} — {o['created_at'][:10]}")

    asyncio.run(main())
