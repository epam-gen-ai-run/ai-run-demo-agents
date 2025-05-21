import logging

import click

from agent_executor import FinancialAgentExecutor
from agent import FinancialAgent
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentAuthentication,
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from dotenv import load_dotenv
import uvicorn
from pyngrok import ngrok


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10500)
def main(host, port):
    """Starts the Financial Agent server."""
    try:
        # ngrok_url = ngrok.connect(port)
        # logger.info(f'ngrok tunnel "{ngrok_url.public_url}" -> "http://{host}:{port}"')

        skill = AgentSkill(
            id='financial_agent',
            name='Tool for searching and analysing financial market data',
            description='Helps to search and analyze financial market data',
            tags=['financial market data'],
            examples=["How does EPAM feels today comparing with ACN?", "What happened today with EPAM stocks?"],
        )
        agent_card = AgentCard(
            name="Financial Agent",
            description="Helps to search and analyze financial market data",
            # url=ngrok_url.public_url,
            url=f'http://{host}:{port}/',
            version='1.0.0',
            defaultInputModes=FinancialAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=FinancialAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=AgentCapabilities(streaming=True),
            skills=[skill],
            authentication=AgentAuthentication(schemes=['public']),
        )

        request_handler = DefaultRequestHandler(
            agent_executor=FinancialAgentExecutor(),
            task_store=InMemoryTaskStore(),
        )
        
        server = A2AStarletteApplication(
            agent_card=agent_card,
            http_handler=request_handler,
        )
        
        logger.info(f'Starting server on {host}:{port}')
        uvicorn.run(server.build(), host=host, port=port)
    except Exception as e:
        logger.error(f'An error occurred during server startup: {e}')
        exit(1)


if __name__ == '__main__':
    main()
