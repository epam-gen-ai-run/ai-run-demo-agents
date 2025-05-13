# AI Run Demo Agents

This repository contains a collection of AI agents built with different frameworks and architectures, designed to demonstrate various capabilities and integration patterns.

## Agents

### LangGraph Currency Agent

**Location:** `/python/agents/langgraph`

A currency conversion agent built with LangGraph that provides real-time exchange rate information through the A2A protocol.

**Key Capabilities:**
- Currency conversion with real-time exchange rates via Frankfurter API
- Multi-turn conversations with follow-up questions
- Real-time streaming with status updates
- Conversational memory across interactions
- Structured response format with clear status indicators

**Example Use Cases:**
- "How much is 100 USD in EUR?"
- "What's the exchange rate for USD to JPY?"
- "Convert 50 EUR to GBP"

## Getting Started

Each agent directory contains its own README with specific setup instructions and examples. To run an agent:

1. Navigate to the agent directory (e.g., `cd python/agents/langgraph`)
2. Follow the setup instructions in the agent's README
3. Run the agent using the provided commands

## Contributing

To add a new agent to this collection:
1. Create a new directory under `/python/agents/` or `/<you_language>/agents`
2. Include a comprehensive README.md with capabilities and examples
3. Ensure the agent follows the established patterns for integration

## License

MIT License