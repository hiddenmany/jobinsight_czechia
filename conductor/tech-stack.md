# Technology Stack

## Core Development
- **Language:** Python 3.10+
- **Frontend Framework:** Streamlit (Interactive Dashboards)
- **Data Processing:** Pandas
- **Visualization:** Plotly, Altair

## Data Acquisition & Storage
- **Scraping Engine:** Playwright (Headless Browser Automation)
- **Database:** DuckDB (High-performance analytical storage)
- **Parsers:** custom `lxml` and regex-based parsers

## Intelligence & AI
- **LLM Provider:** Google Gemini
- **SDK:** `google-genai`
- **Model:** `gemini-3-pro-preview` (for market analysis and reporting)
- **Embeddings:** `sentence-transformers` (Optional for role classification)

## Infrastructure & DevOps
- **Automation:** GitHub Actions (Weekly scheduled scrapes and reports)
- **Environment Management:** `python-dotenv`
- **Testing:** `pytest`
