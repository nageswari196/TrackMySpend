# TrackMySpend — Upgraded

## What changed vs. the original `app1.py`

| Area | Before | After |
|---|---|---|
| Passwords | Unsalted SHA-256 | bcrypt (salted, slow-hash). Existing users are silently migrated to bcrypt the next time they log in — no reset needed. |
| Tesseract path | Hardcoded `C:\Program Files\Tesseract-OCR\...` | Auto-detected on PATH, or set `TESSERACT_CMD` in `.env`. App degrades gracefully (OCR disabled, rest still works) if Tesseract isn't found. |
| Budgets | Reset every rerun (never saved) | Persisted per user/month in a new `budgets` table. |
| Edit/Delete expense | Selected by merchant **name** — ambiguous/buggy if two expenses shared a merchant | Selected by row **id** — always correct. |
| `category_model.pkl` | A bare `MultinomialNB` with no vectorizer — never actually usable, unused in the app | Retrained as a full pipeline (TF-IDF + Naive Bayes) and wired into "Add Expense" to auto-suggest a category from OCR'd receipt text. Retrain anytime with `python train_category_model.py`. |
| Currency conversion | `forex-python`, which depends on a defunct free API | `exchangerate.host` (maintained, keyless) with a static fallback table so it never crashes offline. |
| Data export | None | CSV export button on the "View Expenses" page. |
| Theme | Forced light mode only | Modern-minimal design system: soft-shadow cards, teal/emerald accent, Inter font, light/dark toggle in the sidebar — replaces the old flat forced-light CSS. |
| View Expenses | Plain table, no way to find anything in a long list | Search box (merchant/description), category filter, date range, 4 sort options, and pagination (10/25/50/100 rows per page) — see `filters.py`. Charts and CSV export now reflect the filtered result, not the whole table. |
| Home dashboard | Single "Total Spent" metric | 3-metric row (total, recent daily average, top recent category) plus charts grouped into cards with a matching Plotly theme (transparent background, themed grid/fonts). |
| AI Assistant | Keyword matching only | Same keyword fallback by default (zero setup) + optional real natural-language answers via the Claude API if you set `ANTHROPIC_API_KEY`. |
| Config | Hardcoded everywhere | Centralized in `config.py`, overridable via `.env`. |

## Project structure

```
pro4/
├── app.py                    # main Streamlit app (run this)
├── config.py                 # env-driven settings
├── auth.py                   # bcrypt hashing + legacy migration
├── db.py                     # all SQLite access (users, expenses, budgets)
├── categorize.py             # loads category_model.pkl, predicts category from text
├── currency.py                # currency conversion with fallback
├── train_category_model.py   # retrain the category classifier
├── filters.py                 # search / sort / pagination controls for expense tables
├── category_model.pkl        # trained TF-IDF + Naive Bayes pipeline
├── expenses.db                # SQLite database
├── logo.png
├── requirements.txt
└── .env.example               # copy to .env and fill in as needed
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # edit as needed (all fields optional)
streamlit run app.py
```

Your existing `expenses.db` and user accounts carry over unchanged — old
passwords keep working and are upgraded to bcrypt automatically on next login.

## Notes / next ideas not yet implemented

- The `data.db` file in the original zip appears unused by the app (only
  `expenses.db` is referenced) — safe to remove unless something else of
  yours depends on it.
- Auto-categorization is trained on a small seed dataset (40 examples across
  4 categories). Accuracy will improve if you retrain it on your own labeled
  expense history — happy to build a script that trains from your existing
  `expenses` table if you want that next.
- Budgets are currently one flat monthly number; category-level budgets
  (e.g. "Food ≤ ₹3000/mo") would be a natural next step given the table
  already tracks category sums.
