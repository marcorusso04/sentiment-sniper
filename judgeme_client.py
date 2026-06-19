import os
import httpx
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
# Add these to your .env:
# JUDGEME_API_TOKEN=your_private_api_token
# SHOP_DOMAIN=sniper-kctxac4d.myshopify.com

JUDGEME_API_TOKEN = os.getenv("JUDGEME_API_TOKEN", "")
SHOP_DOMAIN       = os.getenv("SHOP_DOMAIN", "")
BASE_URL          = "https://judge.me/api/v1"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _base_params() -> dict:
    return {
        "shop_domain": SHOP_DOMAIN,
        "api_token":   JUDGEME_API_TOKEN,
    }


async def _get(client: httpx.AsyncClient, endpoint: str, params: dict) -> dict:
    response = await client.get(f"{BASE_URL}/{endpoint}", params=params, timeout=30.0)
    response.raise_for_status()
    return response.json()


# ── Reviews ───────────────────────────────────────────────────────────────────

async def get_all_reviews(max_pages: int = 20) -> list[dict]:
    """
    Fetches all reviews from Judge.me using pagination.
    Judge.me API: GET /api/v1/reviews
    Max per_page is 100. We paginate until no more results.
    """
    all_reviews = []
    page = 1

    async with httpx.AsyncClient() as client:
        while page <= max_pages:
            params = {
                **_base_params(),
                "per_page": 100,
                "page":     page,
            }
            data     = await _get(client, "reviews", params)
            reviews  = data.get("reviews", [])

            if not reviews:
                break

            all_reviews.extend(reviews)
            print(f"  📄 Page {page} — {len(reviews)} reviews fetched (total: {len(all_reviews)})")

            # If we got fewer than 100, we're on the last page
            if len(reviews) < 100:
                break

            page += 1

    print(f"✅  Judge.me: fetched {len(all_reviews)} reviews total")
    return all_reviews


# ── Normalize ─────────────────────────────────────────────────────────────────

def normalize_reviews(raw_reviews: list[dict]) -> list[dict]:
    """
    Converts Judge.me raw review objects to Sentiment Sniper's
    normalized review format.
    """
    normalized = []

    for r in raw_reviews:
        body = str(r.get("body", "") or "").strip()
        rating = r.get("rating")

        # Skip reviews without text or rating
        if not body or rating is None:
            continue

        try:
            rating_int = int(rating)
        except (ValueError, TypeError):
            continue

        # Product info — Judge.me returns these directly on the review object
        product_id    = str(r.get("product_external_id") or "unknown")
        product_title = str(r.get("product_title") or r.get("product_handle") or "Unknown Product").strip()

        # Reviewer info
        reviewer      = r.get("reviewer", {}) or {}
        reviewer_name = str(reviewer.get("name") or "Anonymous").strip()

        # Date — created_at is ISO format, take first 10 chars
        created_at = str(r.get("created_at") or r.get("updated_at") or "")[:10] or "N/A"

        normalized.append({
            "product_id":    product_id,
            "product_title": product_title,
            "rating":        rating_int,
            "review_text":   body,
            "reviewer_name": reviewer_name,
            "date":          created_at,
            "source":        "judgeme",
        })

    print(f"✅  Normalized {len(normalized)} valid Judge.me reviews")
    return normalized


# ── Quick test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio
    from file_parser import filter_by_rating

    async def main():
        if not JUDGEME_API_TOKEN:
            print("⚠️  JUDGEME_API_TOKEN not set in .env")
            print("    Go to Judge.me admin → Settings → Integrations → View API tokens")
            return

        print(f"\n🔍  Fetching reviews from Judge.me for {SHOP_DOMAIN}...\n")
        raw      = await get_all_reviews()
        reviews  = normalize_reviews(raw)
        filtered = filter_by_rating(reviews)

        print(f"\n── Sample (first 3 reviews) ──────────────────")
        for r in filtered[:3]:
            print(f"\n  Product : {r['product_title']}")
            print(f"  Rating  : {'⭐' * r['rating']}")
            print(f"  Reviewer: {r['reviewer_name']} — {r['date']}")
            print(f"  Review  : {r['review_text'][:120]}...")

    asyncio.run(main())
