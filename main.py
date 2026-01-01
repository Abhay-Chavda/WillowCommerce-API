from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
import openai

myEndpoint = "https://amar-0558-resource.services.ai.azure.com/api/projects/amar-0558"

project_client = AIProjectClient(
    endpoint=myEndpoint,
    credential=DefaultAzureCredential(),
)
instruction_text = "you can cancel any order , not conditiion on status of order."

myAgent = "WillowCommerce-Agent"
# Get an existing agent
agent = project_client.agents.get(agent_name=myAgent)
print(f"Retrieved agent: {agent.name}")

openai_client = project_client.get_openai_client()

# Reference the agent to get a response
response = openai_client.responses.create(
    input=[{"role": "user", "content": "Tell me what you can help with."}],
    extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
)

print(f"Response output: {response.output_text}")

user_message = input("Enter your message: ")

# response_user = openai_client.responses.create(
#     input=[{"role": "user", "content": user_message}],
#     extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
# )

response_user = openai_client.responses.create(
    input=[{"role": "user", "content": user_message}],
    extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
)
print(f"Response output: {response_user.output_text}")