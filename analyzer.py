import os
import json
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ── 8 Categories Enum ─────────────────────────────────────────────────────────

CATEGORIES = [
    "Quality",
    "Shipping",
    "Packaging",
    "Usability",
    "Value",
    "Durability",
    "Missing Accessories",
    "Customer Service",
]

# ── Prompt ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert e-commerce review analyst for Sentiment Sniper.
Your job is to analyze customer reviews and classify them into one or more of these 8 categories:

1. Quality        — product build quality, materials, finish, defects
2. Shipping       — delivery speed, tracking, courier issues, late arrival
3. Packaging      — box condition, protection, damaged packaging
4. Usability      — ease of use, ergonomics, setup difficulty, instructions
5. Value          — price vs quality ratio, not worth the money
6. Durability     — product breaking down, wearing out faster than expected
7. Missing Accessories — items listed as included but not in the box
8. Customer Service — support response time, unhelpful staff, unresolved issues

Rules:
- Assign ALL categories that are clearly mentioned or strongly implied in the review
- Minimum 1 category, no maximum
- Only use categories from the list above — no custom categories
- Respond ONLY with a valid JSON object, no preamble, no markdown, no explanation
- Format: {"categories": ["Category1", "Category2"], "summary": "one sentence in the same language as the review"}
"""

# ── Core Classifier ───────────────────────────────────────────────────────────

async def classify_review(review: dict) -> dict:
    """
    Sends a single review to Claude and returns the enriched review dict
    with 'categories' and 'summary' fields added.
    """
    prompt = f"""Product: {review['product_title']}
Rating: {review['rating']}/5
Review: {review['review_text']}

Classify this review."""

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 256,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": prompt}],
            },
        )

    response.raise_for_status()
    raw = response.json()["content"][0]["text"].strip()

    try:
        parsed = json.loads(raw)
        categories = [c for c in parsed.get("categories", []) if c in CATEGORIES]
        summary = parsed.get("summary", "")
    except json.JSONDecodeError:
        categories = ["Quality"]  # safe fallback
        summary = ""

    return {
        **review,
        "categories": categories,
        "summary":    summary,
    }


async def classify_reviews(reviews: list[dict], concurrency: int = 5) -> list[dict]:
    """
    Classifies a list of reviews concurrently.
    concurrency controls how many API calls run in parallel.
    """
    semaphore = asyncio.Semaphore(concurrency)
    results = []
    total = len(reviews)

    async def _classify_with_semaphore(review: dict, index: int) -> dict:
        async with semaphore:
            print(f"  [{index + 1}/{total}] Analyzing: {review['product_title'][:40]} — ⭐{'⭐' * review['rating']}")
            result = await classify_review(review)
            print(f"           → {', '.join(result['categories'])}")
            return result

    tasks = [_classify_with_semaphore(r, i) for i, r in enumerate(reviews)]
    results = await asyncio.gather(*tasks)
    return list(results)


# ── Aggregator ────────────────────────────────────────────────────────────────

def aggregate_by_category(analyzed_reviews: list[dict]) -> dict:
    """
    Returns a summary dict: for each category, how many reviews mention it
    and which products are affected.
    """
    summary = {cat: {"count": 0, "products": set()} for cat in CATEGORIES}

    for review in analyzed_reviews:
        for cat in review.get("categories", []):
            if cat in summary:
                summary[cat]["count"] += 1
                summary[cat]["products"].add(review["product_title"])

    # Convert sets to sorted lists for JSON serialization
    return {
        cat: {
            "count":    data["count"],
            "products": sorted(data["products"]),
        }
        for cat, data in summary.items()
    }


def aggregate_by_product(analyzed_reviews: list[dict]) -> dict:
    """
    Returns a summary dict: for each product, which categories are mentioned
    and how many times.
    """
    summary = {}

    for review in analyzed_reviews:
        title = review["product_title"]
        if title not in summary:
            summary[title] = {cat: 0 for cat in CATEGORIES}
            summary[title]["total_reviews"] = 0
            summary[title]["avg_rating"] = 0.0
            summary[title]["ratings"] = []

        summary[title]["total_reviews"] += 1
        summary[title]["ratings"].append(review["rating"])

        for cat in review.get("categories", []):
            if cat in summary[title]:
                summary[title][cat] += 1

    # Compute avg rating
    for title in summary:
        ratings = summary[title].pop("ratings")
        summary[title]["avg_rating"] = round(sum(ratings) / len(ratings), 2)

    return summary


# ── Quick test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from file_parser import parse_file, filter_by_rating

    async def main():
        # Load and filter reviews
        reviews = parse_file("sample_reviews.csv")
        reviews = filter_by_rating(reviews)

        print(f"\n🤖  Analyzing {len(reviews)} reviews with Claude AI...\n")
        analyzed = await classify_reviews(reviews)

        print(f"\n── Aggregation by Category ───────────────────")
        by_cat = aggregate_by_category(analyzed)
        for cat, data in sorted(by_cat.items(), key=lambda x: -x[1]["count"]):
            if data["count"] > 0:
                print(f"  {cat:<22} {data['count']} mentions — {len(data['products'])} products affected")

        print(f"\n── Aggregation by Product ────────────────────")
        by_prod = aggregate_by_product(analyzed)
        for product, data in by_prod.items():
            issues = [cat for cat in CATEGORIES if data[cat] > 0]
            print(f"\n  {product}")
            print(f"  Avg rating: ⭐{data['avg_rating']} — {data['total_reviews']} reviews")
            print(f"  Issues: {', '.join(issues) if issues else 'none'}")

        # Save raw results to JSON for next step (Streamlit + Excel export)
        with open("analyzed_reviews.json", "w", encoding="utf-8") as f:
            json.dump(analyzed, f, ensure_ascii=False, indent=2)
        print(f"\n💾  Saved analyzed_reviews.json")

    asyncio.run(main())
