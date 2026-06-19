# Sentiment Sniper

AI-powered product review analyser. Classifies each review row-by-row (Sentiment / Category / Recommended Action) and writes the results back into the source Excel file. Also generates a high-level aggregate report of the top 3 recurring problems.

## Tech stack

| Layer | Library |
|---|---|
| UI | Streamlit 1.58 |
| Data | Pandas + openpyxl |
| AI | Anthropic SDK — Haiku (per-row) / Sonnet (aggregate) |
| Config | python-dotenv → `.env` |

## Run

```bash
# Web UI
streamlit run app.py

# CLI (classify all rows + aggregate report)
python sniper.py
```

## File structure

```
Sniper/
├── app.py            # Streamlit UI (two tabs: classify + aggregate)
├── sniper.py         # CLI entry point + shared analysis functions
├── reviews.xlsx      # Source data (read + enriched in place)
├── .env              # ANTHROPIC_API_KEY=sk-ant-...
├── CLAUDE.md         # This file
└── .streamlit/
    └── config.toml   # Dark theme, primaryColor #e63946
```

## Excel layout

The source file has a non-standard header structure — do not change the read logic without accounting for this:

| openpyxl row | content |
|---|---|
| 1 | Notion page title (ignored) |
| 2 | Generic column labels (ignored) |
| **3** | Real headers: `Reviewer`, `Rating`, `Review Text` → `HEADER_ROW = 3` |
| **4** | Markdown separator `:---` → `SEP_ROW = 4` (skipped by pandas) |
| **5–19** | Data rows → `DATA_START = 5` |

Pandas is loaded with `header=2, skiprows=[3]`.  
New classification columns are written to **D, E, F** (columns 4–6).  
Mapping: `pandas iloc[i]` → `openpyxl row DATA_START + i`.

## Models

- **Row-by-row classification** → `claude-haiku-4-5-20251001` (speed + cost)
- **Aggregate report** → `claude-sonnet-4-6` (reasoning quality)

## Classification schema

Each review is classified into:

```json
{
  "sentiment": "Positive | Neutral | Negative",
  "category":  "Quality | Shipping | Packaging | Usability | Value | Durability | Missing Accessories | Customer Service",
  "recommended_action": "<one sentence, imperative Italian, no filler>"
}
```

Sentiment rules:
- **Positive** — clear satisfaction or praise
- **Neutral** — mixed: praise AND complaint coexist
- **Negative** — clear dissatisfaction or product failure

## Active dev state (last updated 2026-06-17)

**Done**
- `sniper.py` v2.0: `classify_all()` writes D/E/F to Excel; `analyze_with_claude()` returns aggregate Sonnet report; `main()` runs both steps sequentially
- `app.py`: dark Streamlit UI; Tab 1 = row-by-row classifier with `st.progress()` + results table + Excel download; Tab 2 = aggregate problem cards; session state persists results across reruns; temp-file pattern for Streamlit uploads
- Prompt sharpened: strict enum for sentiment and category; recommended_action in imperative Italian with filler banned

**Not started / potential next steps**
- Export report as PDF
- Filter/sort the results table by sentiment or category
- Batch API calls to speed up large files
- Support CSV input alongside XLSX
