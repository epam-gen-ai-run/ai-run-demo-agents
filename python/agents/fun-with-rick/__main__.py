import logging

import click

from agent_executor import FunWithRickAgentExecutor
from agent import FunWithRickAgent
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
@click.option('--port', 'port', default=10600)
def main(host, port):
    """Starts the FunWithRickAgent server."""
    try:
        # ngrok_url = ngrok.connect(port)
        # logger.info(f'ngrok tunnel "{ngrok_url.public_url}" -> "http://{host}:{port}"')

        skill = AgentSkill(
            id='alexandria_morty_schmidt',
            name='Rick and Morty Expert',
            description="Provides comprehensive analytical services covering Rick and Morty's canonical lore, character psychology, episode breakdowns, and philosophical deconstructions of the show's narrative multiverse, backed by rigorous academic research and deep existential insight.",
            tags=['Rick and Morty', 'Existential Insight'],
            examples=["What are the psychological motivations behind Rick's alcoholism?", "Compare the different versions of Rick across multiverses"],
        )
        agent_card = AgentCard(
            name="Dr. Alexandria 'Morty' Schmidt",
            description="Provides comprehensive analytical services covering Rick and Morty's canonical lore, character psychology, episode breakdowns, and philosophical deconstructions of the show's narrative multiverse, backed by rigorous academic research and deep existential insight.",
            # url=ngrok_url.public_url,
            url=f'http://{host}:{port}/',
            version='1.0.0',
            defaultInputModes=FunWithRickAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=FunWithRickAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=AgentCapabilities(streaming=True),
            skills=[skill],
            authentication=AgentAuthentication(schemes=['public']),
        )

        request_handler = DefaultRequestHandler(
            agent_executor=FunWithRickAgentExecutor(),
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
