"""
app.py — SpendSense AI web UI (Flask + AJAX chat, SAP Fiori styling).

Routes:
  GET  /       -> the chat page
  POST /chat   -> {message} -> runs moderation + function-calling loop -> {answer, tools}
  POST /reset  -> clears the conversation

Run:  ./.venv/bin/python app.py   then open http://127.0.0.1:5002
"""
from flask import Flask, render_template, request, jsonify

from spend_chat import ask, INTRO

app = Flask(__name__)

# Single shared conversation (fine for a local single-user demo).
HISTORY = None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/intro")
def intro():
    return jsonify(intro=INTRO)


@app.route("/chat", methods=["POST"])
def chat():
    global HISTORY
    message = (request.get_json(silent=True) or {}).get("message", "").strip()
    if not message:
        return jsonify(answer="Please type a question.", tools=[])
    answer, HISTORY, tools = ask(message, HISTORY)
    return jsonify(answer=answer, tools=tools)


@app.route("/reset", methods=["POST"])
def reset():
    global HISTORY
    HISTORY = None
    return jsonify(ok=True)


if __name__ == "__main__":
    # Port 5002 (5000 = macOS AirPlay, 5001 = ShopAssist web app)
    app.run(host="127.0.0.1", port=5002, debug=False)
