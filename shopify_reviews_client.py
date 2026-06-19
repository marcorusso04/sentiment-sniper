import os
import httpx
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
# Shopify does NOT have a native "product reviews" REST endpoint.
# Reviews are managed by third-party apps (Judge.me, Okendo, Stamped, etc.)
# or via the deprecated "Product Reviews" app which used metafields.
#
# This client uses the Shopify Admin GraphQL API to fetch reviews stored
# as metafields (compatible with Shopify's own "Product Reviews" app and
# any app that stores reviews in metafields under the "reviews" namespace).
#
# Namespace: reviews | Key: rating, body, reviewer_name, created_at
# If your store uses a different app, this client can be adapted.

SHOP_DOMAIN          = os.getenv("SHOP_DOMAIN", "")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
API_VERSION          = "2026-04"

GRAPHQL_URL = f"https://{SHOP_DOMAIN}/admin/api/{API_VERSION}/graphql.json"

HEADERS = {
    "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
    "Content-Type":           "application/json",
}

# GraphQL query: fetch products + their review metafields
REVIEWS_QUERY = """
query GetProductReviews($cursor: String) {
  products(first: 50, after: $cursor) {
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        id
        title
        metafields(namespace: "reviews", first: 100) {
          edges {
            node {
              key
              value
              type
            }
          }
        }
      }
    }
  }
}
"""


# ── Fetch ─────────────────────────────────────────────────────────────────────

async def get_all_reviews() -> list[dict]:
    """
    Fetches all products and their review metafields via GraphQL.
    Returns raw product nodes with metafields.
    """
    all_products = []
    cursor       = None

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            payload  = {"query": REVIEWS_QUERY, "variables": {"cursor": cursor}}
            response = await client.post(GRAPHQL_URL, headers=HEADERS, json=payload)
            response.raise_for_status()

            data       = response.json()
            products   = data.get("data", {}).get("products", {})
            edges      = products.get("edges", [])
            page_info  = products.get("pageInfo", {})

            all_products.extend([e["node"] for e in edges])
            print(f"  📦 Fetched {len(all_products)} products so far...")

            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")

    print(f"✅  Shopify: fetched {len(all_products)} products")
    return all_products


# ── Normalize ─────────────────────────────────────────────────────────────────

def normalize_reviews(raw_products: list[dict]) -> list[dict]:
    """
    Extracts and normalizes reviews from Shopify product metafields.
    Expects metafields under namespace "reviews" with keys:
      rating, body, reviewer_name, created_at

    Note: Shopify's native Product Reviews app stores reviews as
    JSON arrays in metafields. We handle both single and JSON array formats.
    """
    import json as _json

    normalized = []

    for product in raw_products:
        product_id    = product.get("id", "").split("/")[-1]
        product_title = product.get("title", "Unknown Product")

        metafields = {}
        for edge in product.get("metafields", {}).get("edges", []):
            node = edge["node"]
            metafields[node["key"]] = node["value"]

        # Try to parse as JSON array (Shopify Product Reviews app format)
        # e.g. metafield "rating" = "[4, 5, 3]", "body" = ["great", "ok", "bad"]
        try:
            ratings       = _json.loads(metafields.get("rating", "[]"))
            bodies        = _json.loads(metafields.get("body", "[]"))
            reviewer_names = _json.loads(metafields.get("reviewer_name", "[]"))
            dates         = _json.loads(metafields.get("created_at", "[]"))

            if isinstance(ratings, list) and isinstance(bodies, list):
                for i, (rating, body) in enumerate(zip(ratings, bodies)):
                    body_str = str(body).strip()
                    if not body_str or body_str.lower() in ("nan", "none", ""):
                        continue
                    try:
                        rating_int = int(float(rating))
                    except (ValueError, TypeError):
                        continue

                    normalized.append({
                        "product_id":    product_id,
                        "product_title": product_title,
                        "rating":        rating_int,
                        "review_text":   body_str,
                        "reviewer_name": reviewer_names[i] if i < len(reviewer_names) else "Anonymous",
                        "date":          str(dates[i])[:10] if i < len(dates) else "N/A",
                        "source":        "shopify",
                    })
                continue

        except (_json.JSONDecodeError, TypeError):
            pass

        # Fallback: single review per product (simple metafield format)
        body   = str(metafields.get("body", "")).strip()
        rating = metafields.get("rating", "")
        if not body or not rating:
            continue
        try:
            rating_int = int(float(rating))
        except (ValueError, TypeError):
            continue

        normalized.append({
            "product_id":    product_id,
            "product_title": product_title,
            "rating":        rating_int,
            "review_text":   body,
            "reviewer_name": str(metafields.get("reviewer_name", "Anonymous")).strip(),
            "date":          str(metafields.get("created_at", "N/A"))[:10],
            "source":        "shopify",
        })

    print(f"✅  Normalized {len(normalized)} Shopify reviews from metafields")
    return normalized


# ── Quick test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio
    from file_parser import filter_by_rating

    async def main():
        print(f"\n🔍  Fetching reviews from Shopify metafields for {SHOP_DOMAIN}...\n")
        raw      = await get_all_reviews()
        reviews  = normalize_reviews(raw)
        filtered = filter_by_rating(reviews)

        if not filtered:
            print("\n⚠️  No reviews found in Shopify metafields.")
            print("    This is normal if you're not using Shopify's Product Reviews app.")
            print("    Use Judge.me or the CSV upload instead.")
            return

        print(f"\n── Sample (first 3 reviews) ──────────────────")
        for r in filtered[:3]:
            print(f"\n  Product : {r['product_title']}")
            print(f"  Rating  : {'⭐' * r['rating']}")
            print(f"  Reviewer: {r['reviewer_name']} — {r['date']}")
            print(f"  Review  : {r['review_text'][:120]}...")

    asyncio.run(main())
