# LangGraph FunWithRick Agent with A2A Protocol

This sample demonstrates an agent built with [LangGraph](https://langchain-ai.github.io/langgraph/) and exposed through the A2A protocol. It showcases conversational interactions with support for multi-turn dialogue and streaming responses.

## How It Works

This agent uses LangGraph with OpenAI to provide comprehensive analytical services covering Rick and Morty's canonical lore, character psychology, episode breakdowns, and philosophical deconstructions of the show's narrative multiverse, backed by rigorous academic research and deep existential insight. The A2A protocol enables standardized interaction with the agent, allowing clients to send requests and receive real-time updates.

## Prerequisites

- Python 3.13 or higher
- [UV](https://docs.astral.sh/uv/)
- Access to an LLM and API Key

## Setup & Running

1. Navigate to the samples directory:

   ```bash
   cd ai-run-demo-agents/python/agents/langgraph
   ```

2. Create an environment file with your API key:

   ```bash
   echo "AZURE_OPENAI_API_KEY=your_api_key_here" > .env
   echo "AZURE_OPENAI_ENDPOINT=your_endpoint_url" >> .env
   echo "OPENAI_API_VERSION=2024-12-01-preview" >> .env
   ```

3. Run the agent:

   ```bash
   # Basic run on default port 10600
   uv run .

   # On custom host/port
   uv run . --host 0.0.0.0 --port 8080
   ```

## Limitations

- Only supports text-based input/output (no multi-modal support)
- Memory is session-based and not persisted between server restarts
