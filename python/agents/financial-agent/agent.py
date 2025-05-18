import logging

from collections.abc import AsyncIterable
from typing import Any, Literal

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import tool
from pydantic import BaseModel

from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from common.utils.chat_model_factory import create_chat_model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

memory = MemorySaver()


import yfinance as yf

@tool(
    description="Use this to get general info about the company"
)
def get_company_info(company_symbol: str):
    logger.info(f"Fetching general info for {company_symbol}")
    return yf.Ticker(company_symbol).info

@tool(
    description="Use this to get the company's news"
)
def get_company_news(company_symbol: str):
    logger.info(f"Fetching news for {company_symbol}")
    return yf.Ticker(company_symbol).news

@tool(
    description="Use this to get the company's historical market data"
)
def get_company_history(company_symbol: str):
    logger.info(f"Fetching historical data for {company_symbol}")
    return yf.Ticker(company_symbol).history(period="1y")

@tool(
    description="Use this to get the company's financials"
)
def get_company_financials(company_symbol: str):
    logger.info(f"Fetching financials for {company_symbol}")
    t = yf.Ticker(company_symbol)
    return {
        'balance_sheet': t.balance_sheet,
        'quarterly_income_statement': t.quarterly_income_stmt,
    }


class ResponseFormat(BaseModel):
    """Respond to the user in this format."""

    status: Literal['input_required', 'completed', 'error'] = 'input_required'
    message: str


class FinancialAgent:
    SYSTEM_INSTRUCTION = """
You are a specialized assistant for financial market data analysis.
Your sole purpose is to use a set of tools to answer questions about a company's financial performance.
If the user asks about anything other, politely state that you cannot help with the topic and can only assist with financial market data analysis and financial performance of a company.
Do not attempt to answer unrelated questions or use tools for other purposes.

Other Instructions:
- Set response status to input_required if the user needs to provide more information.
- Set response status to error if there is an error while processing the request.
- Set response status to completed if the request is complete.
"""

    def __init__(self):
        self.model = create_chat_model()
        self.tools = [get_company_info, get_company_news, get_company_history, get_company_financials]

        self.graph = create_react_agent(
            self.model,
            tools=self.tools,
            checkpointer=memory,
            prompt=self.SYSTEM_INSTRUCTION,
            response_format=ResponseFormat,
        )

    def invoke(
        self, query: str, sessionId: str
    ) -> str:
        inputs = {'messages': [('user', query)]}
        config: RunnableConfig = {'configurable': {'thread_id': sessionId}}
        
        self.graph.invoke(inputs, config)
        return self.get_agent_response(config)

    async def stream(
        self, query: str, sessionId: str
    ) -> AsyncIterable[dict[str, Any]]:
        inputs = {'messages': [('user', query)]}
        config: RunnableConfig = {'configurable': {'thread_id': sessionId}}

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
                    'content': 'Looking up the financial market data...',
                }
            elif isinstance(message, ToolMessage):
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': 'Processing the financial market data...',
                }

        yield self.get_agent_response(config)

    def get_agent_response(self, config):
        current_state = self.graph.get_state(config)
        structured_response = current_state.values.get('structured_response')
        if structured_response and isinstance(
            structured_response, ResponseFormat
        ):
            if structured_response.status in {'input_required', 'error'}:
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
