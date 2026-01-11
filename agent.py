import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

load_dotenv()

AGENT_MESSAGES = {}
response_output = []

project_client = AIProjectClient(
    endpoint=os.environ["PROJECT_ENDPOINT"],
    credential=DefaultAzureCredential(),
)

myAgent = "willowcommerce-user1"
agent = project_client.agents.get(agent_name=myAgent)
print(f"Retrieved agent: {agent.name}")
agent_id = agent.id

openai_client = project_client.get_openai_client()

while True:
    message = input("\nEnter Message (or type exit):\n").strip()
    if not message:
        continue
    if message.lower() == "exit":
        break

    # keep history
    AGENT_MESSAGES.setdefault(agent_id, [])
    AGENT_MESSAGES[agent_id].append({"role": "user", "content": message})

    # ✅ send entire history so "yes" has context
    response = openai_client.responses.create(
        input=AGENT_MESSAGES[agent_id],
        extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
    )

    reply = response.output_text or ""
    print("\nResponse output:", reply)

    AGENT_MESSAGES[agent_id].append({
        "role": "assistant",
        "content": reply,
    })
    response_output.append(response.output)


print("\nChat ended.")
print("Response Outputs :  /n" , response_output)