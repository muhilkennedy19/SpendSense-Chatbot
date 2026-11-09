# SpendSense AI — Procurement Spend Analytics Assistant

Ask procurement spend questions in plain English. SpendSense uses **OpenAI function calling** to
translate your question into a precise analytics function, runs it over a procurement spend dataset
with **pandas**, and answers in natural language — with tables and tool transparency.

Built for the GenAI capstone (Build-Your-Own-Project option).

---

## Quick start

> Prerequisite: an OpenAI API key with a little billing credit, saved in **`OPENAI_API_Key.txt`**
> (one line, `sk-...`). The environment (`.venv/`, Python 3.12) is already set up.

### Option A — Web app (SAP Fiori-styled chat)
```bash
cd "SpendSenseAI"
./.venv/bin/python app.py
# open http://127.0.0.1:5002   (stop with: pkill -f "SpendSenseAI/app.py")
```

### Option B — Jupyter notebook (walkthrough)
```bash
./.venv/bin/jupyter notebook SpendSense_Chatbot.ipynb
```
Pick the kernel **"Python (SpendSense)"**, then **Kernel → Restart Kernel and Run All Cells**.

---

## What's inside

| File | Purpose |
|---|---|
| `data/procurement_spend.csv` | Synthetic dataset — 2,600 POs, ~$417M, 8 categories, 37 suppliers, 2 fiscal years |
| `make_data.py` | Regenerates the dataset (fixed seed → reproducible) |
| `spend_functions.py` | 6 analytics functions + their JSON **tool schemas** + `run_tool()` dispatcher |
| `spend_chat.py` | The shared chat loop: **moderation** gate + **function-calling** round-trip |
| `app.py` + `templates/index.html` | Flask AJAX web UI, SAP Fiori styling, tool-transparency chips |
| `SpendSense_Chatbot.ipynb` | Teaching notebook (built by `build_notebook.py`) |
| `ARCHITECTURE.html` | Visual architecture / flow diagram |
| `REPORT.md` / `REPORT.html` | Project report (export the HTML to PDF for submission) |

---

## The analytics tools GPT can call

| Tool | Answers |
|---|---|
| `get_total_spend(...)` | "How much did we spend on X?" |
| `top_suppliers(n, ...)` | "Top N suppliers by spend" |
| `spend_by_category(...)` | "Break spend down by category" |
| `maverick_spend(group_by, ...)` | "How much off-contract (maverick) spend?" |
| `supplier_performance(supplier)` | "Is supplier X delivering on time?" |
| `spend_trend(period, ...)` | "Show the spend trend over time" |

---

## Using a real dataset instead of synthetic
Replace `data/procurement_spend.csv` with any procurement/PO export whose columns are renamed to match:
`po_date, supplier, category, department, region, amount, contract_id (blank = off-contract),
delivery_days_promised, delivery_days_actual, on_time`. No code changes needed.

---

## Tech
Python 3.12 · `openai` (gpt-4o-mini, function calling + moderation) · `pandas` · `flask` · Jupyter.

---

## Fresh install (e.g. from the submission zip — `.venv` is not included)
```bash
cd SpendSenseAI
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
# then put your real OpenAI key in OPENAI_API_Key.txt (replace the placeholder)
./.venv/bin/python app.py          # web app at http://127.0.0.1:5002
# or: ./.venv/bin/jupyter notebook SpendSense_Chatbot.ipynb
```
