"""Research Agent Server Entry Point.

This module provides the main entry point for the Research Agent A2A server. It handles
server initialization, configuration, and startup. The server provides a JSON-RPC
interface for interacting with the Research Agent, supporting both synchronous and
streaming operations.

The server implements the A2A (Agent-to-Agent) protocol, allowing other agents to
interact with the Research Agent through a standardized JSON-RPC interface. It supports
both synchronous requests and streaming responses for long-running research tasks.

Environment Variables:
    HOST: Server host address (default: localhost)
    PORT: Server port number (default: 10700)
    LOG_LEVEL: Logging level (default: INFO)
    ENABLE_NGROK: Whether to enable ngrok tunneling (default: false)

Example:
    To start the server with default settings:
        python -m research-agent

    To start the server with custom host and port:
        python -m research-agent --host 0.0.0.0 --port 8080

    To enable ngrok tunneling:
        python -m research-agent --enable-ngrok
"""

import logging
import os
import sys

import click
from dotenv import load_dotenv

from agent import ResearchAgent, SUPPORTED_CONTENT_TYPES
from task_manager import AgentTaskManager
from common.server import A2AServer
from common.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)


# Load environment variables
load_dotenv()

# Configure logging
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_port(port: int) -> bool:
    """Validate if the specified port is available for binding.
    
    This function attempts to bind to the specified port on localhost to verify
    if it's available for use. This helps prevent port conflicts during server
    startup.
    
    Args:
        port: The port number to validate, must be between 0 and 65535.
        
    Returns:
        bool: True if the port is available for binding, False otherwise.
        
    Example:
        >>> validate_port(8080)
        True
        >>> validate_port(80)  # Might be False if port is in use
        False
    """
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('localhost', port))
        sock.close()
        return True
    except OSError:
        return False


def create_agent_card(host: str, port: int) -> AgentCard:
    """Create an AgentCard instance for the Research Agent.
    
    This function creates a standardized agent card that describes the Research
    Agent's capabilities, skills, and interface details. The agent card is used
    by the A2A server to advertise the agent's capabilities to other agents.
    
    Args:
        host: The host address where the agent server will be running.
        port: The port number where the agent server will be listening.
        
    Returns:
        AgentCard: A configured agent card instance containing the agent's
            capabilities, skills, and interface details.
            
    Example:
        >>> card = create_agent_card('localhost', 10700)
        >>> print(card.name)
        'Research Assistant'
        >>> print(card.capabilities.streaming)
        True
    """
    skill = AgentSkill(
        id='research_agent',
        name='Research Assistant',
        description="Provides comprehensive research services, conducting thorough "
                   "analysis of topics, gathering relevant information, and presenting "
                   "findings in a clear and structured manner. Capable of handling "
                   "complex queries and providing detailed, well-researched responses.",
        tags=['Research', 'Analysis', 'Information Gathering'],
        examples=[
            "What are the latest developments in quantum computing?",
            "Analyze the impact of climate change on coastal cities",
            "Research the history and evolution of artificial intelligence"
        ],
    )
    
    return AgentCard(
        name="Research Assistant",
        description="A powerful research agent that conducts thorough analysis of "
                   "topics, gathers relevant information, and presents findings in a "
                   "clear and structured manner. Capable of handling complex queries "
                   "and providing detailed, well-researched responses.",
        url=f'http://{host}:{port}/',
        version='1.0.0',
        defaultInputModes=SUPPORTED_CONTENT_TYPES,
        defaultOutputModes=SUPPORTED_CONTENT_TYPES,
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
    )


def setup_server(host: str, port: int) -> A2AServer:
    """Set up and configure the A2A server instance.
    
    This function initializes and configures the A2A server with the Research
    Agent's capabilities. It sets up the server with proper routing, task
    management, and agent configuration.
    
    Args:
        host: The host address where the server will bind.
        port: The port number where the server will listen.
        
    Returns:
        A2AServer: A configured server instance ready to start.
        
    Raises:
        ValueError: If the specified port is not available for binding.
        
    Example:
        >>> server = setup_server('localhost', 10700)
        >>> server.host
        'localhost'
        >>> server.port
        10700
    """
    if not validate_port(port):
        raise ValueError(f"Port {port} is not available")
        
    # Create server
    server = A2AServer(
        agent_card=create_agent_card(host, port),
        task_manager=AgentTaskManager(
            agent=ResearchAgent(),
        ),
        host=host,
        port=port,
    )
    
    return server


@click.command()
@click.option('--host', 'host', default=lambda: os.getenv('HOST', 'localhost'))
@click.option('--port', 'port', type=int, default=lambda: int(os.getenv('PORT', '10700')))
@click.option('--enable-ngrok', 'enable_ngrok', is_flag=True, 
              default=lambda: os.getenv('ENABLE_NGROK', '').lower() == 'true')
def main(host: str, port: int, enable_ngrok: bool) -> None:
    """Start the Research Agent A2A server.
    
    This is the main entry point for the Research Agent server. It handles
    server initialization, signal handling, and startup. The server can be
    configured through command-line arguments or environment variables.
    
    Args:
        host: The host address to bind the server to. Can be set via --host
            or HOST environment variable.
        port: The port number to listen on. Can be set via --port or PORT
            environment variable.
        enable_ngrok: Whether to enable ngrok tunneling. Can be set via
            --enable-ngrok or ENABLE_NGROK environment variable.
            
    Raises:
        ValueError: If there are configuration errors (e.g., port not available).
        Exception: For any other errors during server startup.
        
    Example:
        Start server with default settings:
            $ python -m research-agent
            
        Start server with custom host and port:
            $ python -m research-agent --host 0.0.0.0 --port 8080
            
        Start server with ngrok tunneling:
            $ python -m research-agent --enable-ngrok
    """
    server = None
    try:
        # Validate port range
        if not (0 <= port <= 65535):
            raise ValueError(f"Port must be between 0 and 65535, got {port}")
            
        # Set up ngrok if enabled
        if enable_ngrok:
            from pyngrok import ngrok
            ngrok_url = ngrok.connect(port)
            logger.info(f'ngrok tunnel "{ngrok_url.public_url}" -> "http://{host}:{port}"')
        
        # Start server
        server = setup_server(host, port)
        logger.info(f'Starting server on {host}:{port}')
        server.start()
        
    except ValueError as e:
        logger.error(f'Configuration error: {e}')
        sys.exit(1)
    except Exception as e:
        logger.error(f'An error occurred during server startup: {e}', exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
