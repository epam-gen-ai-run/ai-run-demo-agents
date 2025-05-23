from common.client import A2AClient
from typing import Any
from uuid import uuid4
from common.client.card_resolver import A2ACardResolver
from common.types import (
    SendTaskResponse,
    GetTaskResponse,
    Task,
    Message,
    TextPart,
)
import httpx
import traceback

AGENT_URL = 'http://localhost:10700'


def create_send_task_payload(
    text: str, task_id: str | None = None, context_id: str | None = None
) -> Message:
    """Helper function to create the payload for sending a task."""
    return Message(
        role='user',
        parts=[TextPart(text=text)],
    )


def print_json_response(response: Any, description: str) -> None:
    """Helper function to print the JSON representation of a response."""
    print(f'--- {description} ---')
    if hasattr(response, 'result'):
        print(f'{response.result.model_dump_json(exclude_none=True)}\n')
    else:
        print(f'{response.model_dump(mode="json", exclude_none=True)}\n')


async def run_single_turn_test(client: A2AClient) -> None:
    """Runs a single-turn non-streaming test."""

    send_payload = create_send_task_payload(
        text="What is the most important thing to do to fix the planet?"
    )
    
    # Create task parameters as a dictionary
    task_params = {
        "id": uuid4().hex,
        "message": send_payload.model_dump(),
    }

    print('--- Single Turn Request ---')
    # Send Message
    send_response: SendTaskResponse = await client.send_task(task_params)
    print_json_response(send_response, 'Single Turn Request Response')

    if not isinstance(send_response.result, Task):
        print('received non-task response. Aborting get task ')
        return

    task_id: str = send_response.result.id
    print('---Query Task---')
    # query the task
    get_params = {"id": task_id}
    get_response: GetTaskResponse = await client.get_task(get_params)
    print_json_response(get_response, 'Query Task Response')


async def run_streaming_test(client: A2AClient) -> None:
    """Runs a streaming test."""

    send_payload = create_send_task_payload(
        text="What is the most important thing to do to fix the planet?"
    )
    
    # Create task parameters as a dictionary
    task_params = {
        "id": uuid4().hex,
        "message": send_payload.model_dump(),
    }

    print('--- Streaming Request ---')
    stream_response = client.send_task_streaming(task_params)
    async for chunk in stream_response:
        print_json_response(chunk, 'Streaming Chunk')


async def main() -> None:
    """Main function to run the tests."""
    print(f'Connecting to agent at {AGENT_URL}...')
    try:
        agent_card_resolver = A2ACardResolver(AGENT_URL)
        agent_card = agent_card_resolver.get_agent_card()
        client = A2AClient(agent_card)
        
        print(f'Connected to agent at {client.url}')
        
        await run_single_turn_test(client)
        await run_streaming_test(client)
        
    except Exception as e:
        traceback.print_exc()
        print(f'An error occurred: {e}')
        print('Ensure the agent server is running.')


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())