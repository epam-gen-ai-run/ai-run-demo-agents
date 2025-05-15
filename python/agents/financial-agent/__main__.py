import logging
import os

import click

from agent import FinancialAgent
from task_manager import AgentTaskManager
from common.server import A2AServer
from common.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    MissingAPIKeyError,
)
from common.utils.push_notification_auth import PushNotificationSenderAuth
from dotenv import load_dotenv
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

        capabilities = AgentCapabilities(streaming=True, pushNotifications=True)
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
            capabilities=capabilities,
            skills=[skill],
        )

        notification_sender_auth = PushNotificationSenderAuth()
        notification_sender_auth.generate_jwk()
        server = A2AServer(
            agent_card=agent_card,
            task_manager=AgentTaskManager(
                agent=FinancialAgent(),
                notification_sender_auth=notification_sender_auth,
            ),
            host=host,
            port=port,
        )

        server.app.add_route(
            '/.well-known/jwks.json',
            notification_sender_auth.handle_jwks_endpoint,
            methods=['GET'],
        )

        logger.info(f'Starting server on {host}:{port}')
        server.start()
    except MissingAPIKeyError as e:
        logger.error(f'Error: {e}')
        exit(1)
    except Exception as e:
        logger.error(f'An error occurred during server startup: {e}')
        exit(1)


if __name__ == '__main__':
    main()
