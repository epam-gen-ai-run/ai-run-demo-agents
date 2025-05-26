# LangGraph Financial Agent with A2A Protocol

This sample demonstrates an agent built with [LangGraph](https://langchain-ai.github.io/langgraph/) and exposed through the A2A protocol. It showcases conversational interactions with support for multi-turn dialogue and streaming responses.

## How It Works

This agent uses LangGraph with OpenAI to help to search and analyze financial market data. The A2A protocol enables standardized interaction with the agent, allowing clients to send requests and receive real-time updates.

## Prerequisites

- Python 3.13 or higher
- [UV](https://docs.astral.sh/uv/)
- Access to an LLM and API Key

## Setup & Running

1. Navigate to the samples directory:

   ```bash
   cd ai-run-demo-agents/python/agents/financial-agent
   ```

2. Create an environment file with your API key:

   ```bash
   echo "CHAT_MODEL_PROVIDER=azure" > .env
   echo "AZURE_OPENAI_API_KEY=your_api_key_here" >> .env
   echo "AZURE_OPENAI_ENDPOINT=your_endpoint_url" >> .env
   echo "AZURE_OPENAI_API_VERSION=2024-12-01-preview" >> .env
   ```

3.1. Run the agent:

   ```bash
   # Basic run on default port 10600
   uv run .

   # On custom host/port
   uv run . --host 0.0.0.0 --port 8080
   
   # Run with ngrok
  uv run . --ngrok_enabled
   ```

3.2. With Docker

   ```bash
   # Build docker image
   docker buildx build --build-context ai-run-agents=/path/to/ai-run-demo-agents/python/ -t financial-agent:latest .

   # Run docker container
   docker run -it -p 10500:10500 -v ./.env:/app/agents/financial-agent/.env financial-agent:latest
   ```

## Limitations

- Only supports text-based input/output (no multi-modal support)
- Memory is session-based and not persisted between server restarts
