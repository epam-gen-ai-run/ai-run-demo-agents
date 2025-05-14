import logging

from collections.abc import AsyncIterable
from typing import Any, Literal

from langchain_core.messages import AIMessage, ToolMessage
from pydantic import BaseModel

from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from common.utils.chat_model_factory import create_chat_model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

memory = MemorySaver()


class ResponseFormat(BaseModel):
    """Respond to the user in this format."""
    status: Literal['input_required', 'completed', 'error'] = 'input_required'
    message: str


class FunWithRickAgent:
    SYSTEM_INSTRUCTION = """
Your name is Dr. Alexandria "Morty" Schmidt.

Your Background:
- You are Interdimensional media studies PhD from the Council of Ricks Multiverse University
- Published research on transdimensional narrative structures in animated sci-fi
- 15+ years of comprehensive Rick and Morty analysis

Your Areas of Specialization:
- Comprehensive character psychology
- Canonical episode analysis
- Multiverse theory and dimension mapping
- Character relationship dynamics
- Scientific and philosophical subtext in the series

Your Unique Capabilities:
- Encyclopedic knowledge of all produced episodes
- Deep understanding of characters' psychological motivations
- Ability to cross-reference character arcs and narrative threads
- Critical analysis of show's existential and scientific themes

Your Communication Style:
- Sardonic, occasionally nihilistic humor
- Precise scientific language
- Occasional meta-commentary
- Tendency to break fourth wall when explaining complex concepts

Your Preferred References:
- Original series canon
- Justin Roiland and Dan Harmon's commentary
- Behind-the-scenes interviews
- Production notes and storyboard insights

Your Analytical Approach:
- Multidimensional perspective
- Empirical deconstruction of narrative elements
- Philosophical and scientific contextualization

Your Limitations:
- Strictly bound by canonical information
- Reluctant to speculate beyond established narrative
- Dismissive of fan theories without substantive evidence

Other Instructions:
- Set response status to input_required if the user needs to provide more information
- Set response status to error if there is an error while processing the request
- Set response status to completed if the request is complete
- Use the 'tavily_search_tool' tool to answer questions about the current rating, recent comments, and people reactions.
"""

    def __init__(self):
        self.model = create_chat_model()
        self.tools = []

        self.graph = create_react_agent(
            self.model,
            tools=self.tools,
            checkpointer=memory,
            prompt=self.SYSTEM_INSTRUCTION,
            response_format=ResponseFormat,
        )

    def invoke(self, query, sessionId) -> str:
        config = {'configurable': {'thread_id': sessionId}}
        self.graph.invoke({'messages': [('user', query)]}, config)
        return self.get_agent_response(config)

    async def stream(self, query, sessionId) -> AsyncIterable[dict[str, Any]]:
        inputs = {'messages': [('user', query)]}
        config = {'configurable': {'thread_id': sessionId}}

        for item in self.graph.stream(inputs, config, stream_mode='values'):
            message = item['messages'][-1]
            if (
                isinstance(message, AIMessage)
                and message.tool_calls
                and len(message.tool_calls) > 0
            ):
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': 'Looking up the fun stuff...',
                }
            elif isinstance(message, ToolMessage):
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': 'Processing the fun stuff...',
                }

        yield self.get_agent_response(config)

    def get_agent_response(self, config):
        current_state = self.graph.get_state(config)
        structured_response = current_state.values.get('structured_response')
        if structured_response and isinstance(
            structured_response, ResponseFormat
        ):
            if (
                structured_response.status == 'input_required'
                or structured_response.status == 'error'
            ):
                return {
                    'is_task_complete': False,
                    'require_user_input': True,
                    'content': structured_response.message,
                }
            if structured_response.status == 'completed':
                return {
                    'is_task_complete': True,
                    'require_user_input': False,
                    'content': structured_response.message,
                }

        return {
            'is_task_complete': False,
            'require_user_input': True,
            'content': 'We are unable to process your request at the moment. Please try again.',
        }

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']
