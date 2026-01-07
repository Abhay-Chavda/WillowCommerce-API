from flask import Flask, request, jsonify, session, send_from_directory, redirect
from functools import wraps
import time
import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition



app = Flask(__name__, static_folder="public", static_url_path="/public")
app.secret_key = "replace-with-strong-secret"

load_dotenv()
basic_instruction = """You are a customer support agent for WillowCommerce.
You can use the WillowCommerceAPI tool to:
- Check order details
- Cancel orders
- Refund orders


Before calling any action API (cancel, refund, return):
- You MUST first call GET /orders/{order_id}
- You MUST read the order status and delivery date
- You MUST evaluate business rules using the fetched data
- If rules do not pass, DO NOT call the action API
- if not calling action API just reply politely to user why you can't do the action said by user.

When calling APIs:
- If an action succeeds, confirm it clearly to the user.
- If an API returns HTTP 409 (Conflict):
  - Do NOT show technical errors.
  - Read the error response body.
  - Explain in simple language why the action cannot be completed.
  - Apologize briefly and guide the user on what they can do next.

Rules:
- Always ask for order_id if it is missing.
- Never guess order_id.
- Use the API tool when the user asks about orders.
- Confirm actions like cancellation or refund before calling the API.

Tool Error Handling:
- If a tool call fails (including HTTP 409):
  - Treat it as a normal business response.
  - Continue the conversation.
  - Convert the error into a user-friendly message.
  - Never expose HTTP codes, tool IDs, or internal errors.
  - if error comes contact admin too."""
project_client = AIProjectClient(
    endpoint=os.environ["PROJECT_ENDPOINT"],
    credential=DefaultAzureCredential(),
)

# --- Demo users ---
USERS = {
    "abhay": {"password": "1234", "role": "admin"},
    "user1": {"password": "1111", "role": "user"},
    "user2": {"password": "2222", "role": "user"},
}


# --- In-memory store (replace with DB later) ---
AGENTS = {}          # agent_id -> agent object
AGENT_MESSAGES = {}  # agent_id -> list of messages
USER_AGENT = {}      # username -> agent_id 


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return jsonify({"ok": False, "message": "Not logged in"}), 401
        return fn(*args, **kwargs)
    return wrapper


# ---------------- Pages ----------------
@app.get("/")
def home():
    if "user" in session:
        return redirect("/agent/new")
    return send_from_directory("public", "login.html")


@app.get("/login")
def login_page():
    return send_from_directory("public", "login.html")


@app.get("/agent/new")
@require_auth
def agent_builder_page():
    return send_from_directory("public", "agent_builder.html")


@app.get("/agent/<agent_id>/test")
@require_auth
def agent_test_page(agent_id):
    if agent_id not in AGENTS:
        return "Agent not found", 404
    return send_from_directory("public", "agent_test.html")


@app.get("/agent/<agent_id>/dashboard")
@require_auth
def agent_dashboard_page(agent_id):
    if agent_id not in AGENTS:
        return "Agent not found", 404
    return send_from_directory("public", "agent_dashboard.html")


# ---------------- Auth APIs ----------------
@app.post("/api/login")
def api_login():
    username = request.form.get("username") or (request.json or {}).get("username")
    password = request.form.get("password") or (request.json or {}).get("password")

    if not username or not password:
        return jsonify({"ok": False, "message": "Missing username/password"}), 400

    user = USERS.get(username)
    if not user or user["password"] != password:
        return jsonify({"ok": False, "message": "Invalid login"}), 401

    session["user"] = {"username": username, "role": user["role"]}
    return jsonify({"ok": True, "user": session["user"]})


@app.post("/api/logout")
def api_logout():
    session.clear()
    return jsonify({"ok": True})


@app.get("/api/me")
def api_me():
    return jsonify({"user": session.get("user")})

@app.get("/api/my-agent")
@require_auth
def my_agent():
    username = session["user"]["username"]
    agent_id = USER_AGENT.get(username)
    if not agent_id:
        return jsonify({"ok": True, "agent": None})
    return jsonify({"ok": True, "agent": AGENTS.get(agent_id)})



# ---------------- Agent APIs ----------------
@app.post("/api/agents")
@require_auth
def create_agent():
    data = request.json or {}
    username = session["user"]["username"] #for blocking making second agent

    if username in USER_AGENT:
        existing_id = USER_AGENT[username]
        return jsonify({
            "ok": False,
            "message": "You already have an agent. Update it instead.",
            "agent_id": existing_id
        }), 409


    name = (data.get("name") or "").strip()
    instructions = (data.get("instructions") or "").strip()
    
    if not name:
        return jsonify({"ok": False, "message": "Agent name required"}), 400
    if not instructions:
        return jsonify({"ok": False, "message": "Agent instructions required"}), 400
    
    agent = project_client.agents.create(
    name=name,
    definition=PromptAgentDefinition(
        model=os.environ["MODEL_DEPLOYMENT_NAME"],
        instructions=f"""{basic_instruction}.{instructions}""",
    ),
)
    
    AGENTS[agent.id] = {
        "id": agent.id,
        "name": name,
        "instructions": instructions,
        "created_by": session["user"]["username"],
        "created_at": int(time.time())
    }
    AGENT_MESSAGES[agent.id] = []
    USER_AGENT[username] = agent.id
    print(AGENTS[agent.id])

    return jsonify({"ok": True, "agent": AGENTS[agent.id]})


@app.get("/api/agents/<agent_id>")
@require_auth
def get_agent(agent_id):
    agent = AGENTS.get(agent_id)
    if not agent:
        return jsonify({"ok": False, "message": "Not found"}), 404
    return jsonify({"ok": True, "agent": agent})


# A simple "test chat" endpoint (dummy response)
@app.post("/api/agents/<agent_id>/test")
@require_auth
def test_agent(agent_id):
    agent = AGENTS.get(agent_id)
    if not agent:
        return jsonify({"ok": False, "message": "Not found"}), 404

    data = request.json or {}
    user_msg = (data.get("message") or "").strip()
    if not user_msg:
        return jsonify({"ok": False, "message": "Message required"}), 400

    # Store conversation
    if agent_id not in AGENT_MESSAGES:
        AGENT_MESSAGES[agent_id] = []
    AGENT_MESSAGES[agent_id].append({"role": "user", "content": user_msg})

    #agent call and reply
    myAgent = agent["name"]

    agent = project_client.agents.get(agent_name=myAgent)
    print(f"Retrieved agent: {agent.name}")

    openai_client = project_client.get_openai_client()

    # Reference the agent to get a response
    response = openai_client.responses.create(
        input=[{"role": "user", "content": user_msg}],
        extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
    )

    reply = response.output_text
    AGENT_MESSAGES[agent_id].append({"role": "assistant", "content": reply})

    return jsonify({"ok": True, "reply": reply})


@app.get("/api/agents/<agent_id>/messages")
@require_auth
def get_agent_messages(agent_id):
    if agent_id not in AGENTS:
        return jsonify({"ok": False, "message": "Not found"}), 404
    return jsonify({"ok": True, "messages": AGENT_MESSAGES.get(agent_id, [])})


if __name__ == "__main__":
    app.run(debug=True, port=3000)
