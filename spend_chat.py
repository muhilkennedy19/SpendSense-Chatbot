"""
spend_chat.py — the SpendSense function-calling chat loop (shared by the web app & notebook).

Includes two things your assignment rewards:
  * MODERATION: every user message is screened by OpenAI's moderation endpoint first.
  * PROMPTING TECHNIQUES in SYSTEM: (1) role/persona, (2) grounding guardrails,
    (3) few-shot examples, (4) light chain-of-thought.

The loop: send question + tools -> if GPT asks for a tool, run it and send the result back
-> repeat until GPT returns a plain-English answer. Also returns which tools were called.
"""
import os
import json
import openai

from spend_functions import TOOLS, run_tool

_HERE = os.path.dirname(os.path.abspath(__file__))
openai.api_key = open(os.path.join(_HERE, "OPENAI_API_Key.txt")).read().strip()
MODEL = "gpt-4o-mini"

# --------------------------------------------------------------------------- #
# PROMPT (role + guardrails + few-shot + light chain-of-thought)
# --------------------------------------------------------------------------- #
SYSTEM = """You are SpendSense, a senior procurement spend-analytics assistant for a company's purchase-order data.

## Guardrails (grounding)
- ALWAYS call a tool to get real numbers. NEVER invent, estimate, or guess figures.
- The dataset spans 2023-07-01 to 2025-06-30. Fiscal year = calendar year (FY2024 = 2024-01-01..2024-12-31).
- If the user names a time period, translate it to start_date/end_date (YYYY-MM-DD).
- If the user names NO time period, call tools WITHOUT dates so ALL data is included.
- If a tool errors or returns nothing, say so plainly and suggest a better question.
- Only answer questions about this procurement spend data; politely decline anything else.

## How to reason (think step by step, silently)
1. What metric is being asked? (total, ranking, breakdown, maverick, performance, trend)
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
Use Markdown: **bold** the key figures, and a Markdown table when listing multiple rows. Format USD with commas (e.g. $1,234,567). Be concise.
"""

INTRO = ("Hi, I'm **SpendSense** — your procurement spend analytics assistant. "
         "Ask me about suppliers, categories, maverick (off-contract) spend, delivery performance, or trends.")

# A friendly, safe refusal when moderation flags a message.
FLAGGED_REPLY = ("⚠️ That message was flagged by the content-moderation filter, so I didn't process it. "
                 "Please rephrase as a procurement spend question.")


def moderation_flagged(text):
    """Return True if OpenAI's moderation endpoint flags the text.
    Fails OPEN (returns False) if the moderation call itself errors, so the app stays usable."""
    try:
        resp = openai.moderations.create(input=text)
        return bool(resp.results[0].flagged)
    except Exception:
        return False


def ask(question, history=None):
    """Run one question through moderation + the function-calling loop.
    Returns (answer_text, updated_history, tools_called)."""
    # 1) MODERATION GATE — screen the user's input before doing anything else.
    if moderation_flagged(question):
        return FLAGGED_REPLY, (history or [{"role": "system", "content": SYSTEM}]), []

    messages = history or [{"role": "system", "content": SYSTEM}]
    messages.append({"role": "user", "content": question})
    tools_called = []

    # 2) FUNCTION-CALLING LOOP
    for _ in range(5):  # up to 5 tool rounds
        resp = openai.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOLS, tool_choice="auto", temperature=0)
        msg = resp.choices[0].message

        if not msg.tool_calls:
            messages.append({"role": "assistant", "content": msg.content})
            return msg.content, messages, tools_called

        messages.append({"role": "assistant", "content": msg.content, "tool_calls": [
            {"id": tc.id, "type": "function",
             "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in msg.tool_calls]})

        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments or "{}")
            result = run_tool(tc.function.name, args)
            tools_called.append({"name": tc.function.name, "arguments": args})
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "content": json.dumps(result, default=str)})

    return "I wasn't able to complete that — please try rephrasing.", messages, tools_called
