import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition

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
instruction = f"""You work for user with user_id {os.environ["USER_ID"]}.You can not cancel order if it is deliverd"""

project_client = AIProjectClient(
    endpoint=os.environ["PROJECT_ENDPOINT"],
    credential=DefaultAzureCredential(),
)

myAgent = "willowcommerce-user1"
# Get an existing agent
agent = project_client.agents.get(agent_name=myAgent)
print(f"Retrieved agent: {agent.name}")


openai_client = project_client.get_openai_client()

# Reference the agent to get a response
response = openai_client.responses.create(
    input=[{"role": "user", "content": "I want to return order with order_id "}],
    extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
)

print(f"Response output: {response.output_text}")

