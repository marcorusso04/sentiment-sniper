import os
import pandas as pd
from datetime import datetime


# ── Supported column name aliases ─────────────────────────────────────────────
# Maps common column names from Judge.me, Shopify, and manual exports
# to our internal normalized field names.

COLUMN_ALIASES = {
    "product_id":     ["product_id", "product id", "productid", "id prodotto"],
    "product_title":  ["product_title", "product title", "product", "prodotto", "title", "titolo"],
    "rating":         ["rating", "stars", "voto", "stelle", "score", "punteggio"],
    "review_text":    ["review_text", "review", "body", "comment", "commento", "recensione", "testo", "message"],
    "reviewer_name":  ["reviewer_name", "reviewer", "author", "name", "nome", "autore", "customer"],
    "date":           ["date", "created_at", "data", "review_date", "submitted_at"],
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Renames dataframe columns to our internal normalized names
    based on COLUMN_ALIASES. Case-insensitive matching.
    """
    col_map = {}
    df_cols_lower = {c.lower().strip(): c for c in df.columns}

    for internal_name, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias.lower() in df_cols_lower:
                original_col = df_cols_lower[alias.lower()]
                col_map[original_col] = internal_name
                break

    df = df.rename(columns=col_map)
    return df


def _normalize_rating(value) -> int | None:
    """
    Converts rating to integer 1-5.
    Handles floats (4.0), strings ("4"), and None.
    """
    try:
        r = int(float(str(value).strip()))
        return r if 1 <= r <= 5 else None
    except (ValueError, TypeError):
        return None


def _normalize_date(value) -> str:
    """
    Converts various date formats to ISO string YYYY-MM-DD.
    Falls back to today if unparseable.
    """
    if pd.isna(value) or value is None:
        return datetime.today().strftime("%Y-%m-%d")
    try:
        return pd.to_datetime(value).strftime("%Y-%m-%d")
    except Exception:
        return datetime.today().strftime("%Y-%m-%d")


def _to_normalized_review(row: dict, source: str) -> dict | None:
    """
    Converts a raw dataframe row to a normalized review dict.
    Returns None if the row is missing critical fields.
    """
    review_text = str(row.get("review_text", "")).strip()
    rating = _normalize_rating(row.get("rating"))

    # Skip rows without review text or valid rating
    if not review_text or review_text.lower() in ("nan", "none", ""):
        return None
    if rating is None:
        return None

    return {
        "product_id":    str(row.get("product_id", "unknown")).strip(),
        "product_title": str(row.get("product_title", "Unknown Product")).strip(),
        "rating":        rating,
        "review_text":   review_text,
        "reviewer_name": str(row.get("reviewer_name", "Anonymous")).strip(),
        "date":          _normalize_date(row.get("date")),
        "source":        source,
    }


# ── Public API ────────────────────────────────────────────────────────────────

def parse_file(filepath: str) -> list[dict]:
    """
    Parses a CSV or Excel file containing reviews.
    Returns a list of normalized review dicts.

    Supported formats: .csv, .xlsx, .xls
    """
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".csv":
        df = pd.read_csv(filepath, dtype=str)
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(filepath, dtype=str)
    else:
        raise ValueError(f"Unsupported file format: {ext}. Use .csv or .xlsx")

    print(f"📂  Loaded {len(df)} rows from '{os.path.basename(filepath)}'")

    # Normalize column names
    df = _normalize_columns(df)

    # Check that at minimum review_text exists
    if "review_text" not in df.columns:
        raise ValueError(
            "Could not find a review text column. "
            "Expected one of: review, body, comment, review_text, recensione, testo"
        )

    # Parse each row
    reviews = []
    skipped = 0

    for _, row in df.iterrows():
        normalized = _to_normalized_review(row.to_dict(), source="upload")
        if normalized:
            reviews.append(normalized)
        else:
            skipped += 1

    print(f"✅  Parsed {len(reviews)} valid reviews — skipped {skipped} incomplete rows")
    return reviews


def filter_by_rating(reviews: list[dict], max_stars: int = 4) -> list[dict]:
    """
    Filters reviews to only include those with rating <= max_stars.
    Default: 1-4 stars (excludes 5-star reviews per Sentiment Sniper's target).
    """
    filtered = [r for r in reviews if r["rating"] <= max_stars]
    print(f"⭐  Filtered to {len(filtered)} reviews with rating 1–{max_stars} stars")
    return filtered


# ── Quick test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 file_parser.py path/to/reviews.csv")
        print("\nExpected columns (any of these names work):")
        for field, aliases in COLUMN_ALIASES.items():
            print(f"  {field}: {', '.join(aliases)}")
        sys.exit(0)

    filepath = sys.argv[1]
    reviews = parse_file(filepath)
    reviews = filter_by_rating(reviews)

    print(f"\n── Sample (first 3 reviews) ──────────────────")
    for r in reviews[:3]:
        print(f"\n  Product : {r['product_title']}")
        print(f"  Rating  : {'⭐' * r['rating']}")
        print(f"  Reviewer: {r['reviewer_name']} — {r['date']}")
        print(f"  Review  : {r['review_text'][:120]}...")
