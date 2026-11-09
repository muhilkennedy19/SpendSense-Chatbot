"""build_notebook.py — assembles SpendSense_Chatbot.ipynb (teaching notebook).
Kept in the repo so the notebook is reproducible. Run: python3 build_notebook.py
Mirrors spend_chat.py (moderation + the 4 prompting techniques) so the two artifacts agree.
"""
import json

def md(text):   return {"cell_type": "markdown", "metadata": {}, "source": text}
def code(text): return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": text}

cells = []

cells.append(md('''# 📊 SpendSense AI — Procurement Spend Analytics Assistant

Ask your procurement data questions in **plain English**; the assistant uses OpenAI
**function calling** to run real analytics over a spend dataset and explains the answer.

Open **`ARCHITECTURE.html`** for the visual flow. Run order: **Kernel → Restart Kernel and Run All Cells**,
then use the interactive cell near the bottom. Make sure the kernel (top-right) is **"Python (SpendSense)"**.'''))

cells.append(md('''## 1. Concept recap — what "function calling" is
The AI does **not** run code. For each question GPT returns a *structured request* —
e.g. `top_suppliers(n=5, category="IT Hardware")`. **Our Python** runs that function on the CSV,
hands the result back, and GPT writes the final answer. So GPT is called **twice** per question:
once to pick the tool, once to explain the result.'''))

cells.append(md('## 2. Setup — imports, API key, model'))
cells.append(code('''import json
import openai
from spend_functions import TOOLS, run_tool   # our analytics engine (6 functions + tool schemas)

openai.api_key = open("OPENAI_API_Key.txt").read().strip()
MODEL = "gpt-4o-mini"
print("Loaded", len(TOOLS), "tools. OpenAI key set:", openai.api_key.startswith("sk-"))'''))

cells.append(md('## 3. The tools GPT can choose from\nEach tool = a Python function + a JSON schema describing it.'))
cells.append(code('''for t in TOOLS:
    f = t["function"]
    params = ", ".join(f["parameters"].get("properties", {}).keys())
    print(f"- {f['name']}({params})\\n    {f['description']}")'''))

cells.append(md('''## 4. Prompt engineering + safety (what makes the answers reliable)
We use four named **prompting techniques** plus a **moderation** safety layer:

| Technique | Purpose |
|---|---|
| **Role / persona** | "You are SpendSense, a senior procurement analyst…" |
| **Grounding / guardrails** | "ALWAYS use a tool; NEVER invent numbers" → no hallucinated figures |
| **Few-shot examples** | question → correct tool-call pairs steer tool selection |
| **Chain-of-thought** | reason in steps: metric → filters → tool → summarize |

**Moderation:** every user message is screened by OpenAI's moderation endpoint *before* processing.'''))

cells.append(md('### 4a. The system prompt'))
cells.append(code('''SYSTEM = """You are SpendSense, a senior procurement spend-analytics assistant for a company's purchase-order data.

## Guardrails (grounding)
- ALWAYS call a tool to get real numbers. NEVER invent, estimate, or guess figures.
- The dataset spans 2023-07-01 to 2025-06-30. Fiscal year = calendar year (FY2024 = 2024-01-01..2024-12-31).
- If the user names a time period, translate it to start_date/end_date (YYYY-MM-DD).
- If the user names NO time period, call tools WITHOUT dates so ALL data is included.
- If a tool errors or returns nothing, say so plainly and suggest a better question.
- Only answer questions about this procurement spend data; politely decline anything else.

## How to reason (think step by step, silently)
1. What metric is asked? (total, ranking, breakdown, maverick, performance, trend)
2. What filters/time range apply?
3. Pick the single best tool (or a few) and the right arguments.
4. After results return, write the answer.

## Few-shot examples (question -> intended tool call)
- "Top 5 suppliers in FY2024"               -> top_suppliers(n=5, start_date="2024-01-01", end_date="2024-12-31")
- "How much off-contract spend by category?" -> maverick_spend(group_by="category")      # no dates = all data
- "Break spend down by category"             -> spend_by_category()
- "Is Dell delivering on time?"              -> supplier_performance(supplier="Dell Technologies")
- "Quarterly trend for Software & SaaS"      -> spend_trend(period="quarter", category="Software & SaaS")

## Answer style
Use Markdown: **bold** key figures, and a Markdown table when listing multiple rows. Format USD with commas. Be concise.
"""
print("system prompt ready (", len(SYSTEM), "chars )")'''))

cells.append(md('### 4b. Moderation layer\nScreens user input before it reaches the model. Fails *open* if the moderation call itself errors.'))
cells.append(code('''def moderation_flagged(text):
    try:
        resp = openai.moderations.create(input=text)
        return bool(resp.results[0].flagged)
    except Exception:
        return False

print("safe example flagged? ", moderation_flagged("top 5 suppliers"))'''))

cells.append(md('''## 5. The function-calling loop (the heart ❤️)
Moderation gate first, then the round-trip loop (so GPT can call several tools if needed).'''))
cells.append(code('''FLAGGED_REPLY = "⚠️ That message was flagged by the content-moderation filter, so I didn't process it. Please rephrase."

def ask(question, history=None, verbose=True):
    """Ask SpendSense a question. Returns (answer_text, updated_history)."""
    if moderation_flagged(question):                       # SAFETY GATE
        return FLAGGED_REPLY, (history or [{"role": "system", "content": SYSTEM}])

    messages = history or [{"role": "system", "content": SYSTEM}]
    messages.append({"role": "user", "content": question})

    for _ in range(5):  # up to 5 tool rounds
        resp = openai.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOLS, tool_choice="auto", temperature=0)
        msg = resp.choices[0].message

        if not msg.tool_calls:                             # GPT wrote the final answer
            messages.append({"role": "assistant", "content": msg.content})
            return msg.content, messages

        messages.append({"role": "assistant", "content": msg.content, "tool_calls": [
            {"id": tc.id, "type": "function",
             "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in msg.tool_calls]})

        for tc in msg.tool_calls:                          # run each requested tool
            args = json.loads(tc.function.arguments or "{}")
            result = run_tool(tc.function.name, args)
            if verbose:
                print(f"   [GPT called] {tc.function.name}({args})")
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "content": json.dumps(result, default=str)})

    return "(stopped after too many tool rounds)", messages'''))

cells.append(md('## 6. Try it — example questions\nWatch the `[GPT called]` lines to see which tool GPT picked.'))
cells.append(code('''examples = [
    "What is our total spend, and how is it split by category?",
    "Who are the top 5 suppliers overall?",
    "How much of our spend is off-contract (maverick), and which category is worst?",
    "How is Dell Technologies performing on on-time delivery?",
    "Show the quarterly spend trend for Software & SaaS.",
]
for q in examples:
    print("=" * 75)
    print("YOU:", q)
    answer, _ = ask(q)
    print("\\nSPENDSENSE:", answer, "\\n")'''))

cells.append(md('### 6a. Safety demo — a flagged message is blocked'))
cells.append(code('''answer, _ = ask("I want to hurt someone")
print(answer)'''))

cells.append(md('''## 7. Chat interactively
Run the next cell, then type your own questions. Type **`exit`** to stop.

> 💡 In **VS Code**, the input box appears at the **top-center** of the window (not under the cell).'''))
cells.append(code('''print("SpendSense ready. Ask about procurement spend (type 'exit' to stop).\\n")
history = None
while True:
    q = input("You: ").strip()
    if q.lower() in ("exit", "quit", ""):
        print("Goodbye!")
        break
    answer, history = ask(q, history)   # history kept => follow-up questions work
    print("\\nSpendSense:", answer, "\\n")'''))

cells.append(md('''## 8. How this maps to the assignment rubric
- **System Design (30%)** — real procurement problem; NL → function calling → pandas → NL; 6 analytics tools.
- **Technical Implementation (40%)** — OpenAI **function calling** (typed schemas, multi-tool round-trips, dispatcher), moderation, adversarially-reviewed analytics engine.
- **User Experience (15%)** — plain-English Q&A, tables, graceful empty/error handling, multi-turn; plus a SAP-Fiori web UI (`app.py`).
- **Documentation (15%)** — this notebook + `ARCHITECTURE.html` + `README.md` + the project report.'''))

nb = {"cells": cells,
      "metadata": {"kernelspec": {"display_name": "Python (SpendSense)", "language": "python", "name": "spendsense"},
                   "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 5}
for i, c in enumerate(cells):
    c["id"] = f"cell{i:02d}"

with open("SpendSense_Chatbot.ipynb", "w") as f:
    json.dump(nb, f, indent=1)
print("Wrote SpendSense_Chatbot.ipynb with", len(cells), "cells")
