"""Research Agent implementation using LangGraph for multi-step research workflow.

This module implements a research agent that processes user queries through a multi-step
workflow involving topic extraction, research, and analysis. The agent uses LangChain
for LLM interactions and LangGraph for workflow management.

Example:
    ```python
    agent = ResearchAgent()
    response = agent.invoke(
        "What is the impact of climate change on biodiversity?",
        "session-123"
    )
    print(response["content"])
    ```
"""

from dataclasses import dataclass, field
from typing import TypedDict, Dict, Any, Optional, Protocol, List
from collections.abc import AsyncIterable
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
from langchain.schema.runnable import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from common.utils.chat_model_factory import create_chat_model
from dotenv import load_dotenv
import re
import time
import logging
import asyncio

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MAX_QUERY_LENGTH = 1000  # Maximum allowed length for research queries
MAX_SESSION_AGE_HOURS = 24  # Maximum age of session data before cleanup
SESSION_ID_PATTERN = re.compile(r'^[a-zA-Z0-9-_]{1,64}$')  # Valid session ID pattern
SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']  # Supported content types for responses

class ResearchState(TypedDict):
    """State maintained throughout the research workflow.
    
    Attributes:
        user_query: The original query from the user.
        research_topic: The extracted topic to research.
        research_findings: The findings from the research phase.
        research_report: The final analyzed report.
        timestamp: Unix timestamp of when the state was created.
        error: Optional error message if something went wrong.
    """
    user_query: str
    research_topic: str
    research_findings: str
    research_report: str
    timestamp: float
    error: Optional[str]

class AgentResponse(TypedDict):
    """Response structure for the research agent.
    
    Attributes:
        is_task_complete: Whether the research task was completed successfully.
        content: The research report or error message.
        error: Optional error message if something went wrong.
        session_id: The session identifier for the request.
        timestamp: Unix timestamp of when the response was generated.
    """
    is_task_complete: bool
    content: str
    error: Optional[str]
    session_id: str
    timestamp: float

@dataclass
class AgentConfig:
    """Configuration for the ResearchAgent.
    
    Attributes:
        max_query_length: Maximum allowed length for research queries.
        max_session_age_hours: Maximum age of session data before cleanup.
        supported_content_types: List of supported content types for responses.
    """
    max_query_length: int = MAX_QUERY_LENGTH
    max_session_age_hours: int = MAX_SESSION_AGE_HOURS
    supported_content_types: List[str] = field(default_factory=lambda: SUPPORTED_CONTENT_TYPES)

class ResearchAgentProtocol(Protocol):
    """Protocol defining the interface for research agents.
    
    This protocol ensures that any implementation of a research agent
    must provide both invoke and stream methods with the specified signatures.
    The protocol defines the contract that all research agent implementations
    must follow, ensuring consistent behavior across different implementations.
    
    Methods:
        invoke: Process a research query synchronously and return results.
        stream: Process a research query asynchronously and stream updates.
    """
    def invoke(self, query: str, session_id: str) -> AgentResponse:
        """Process a research query and return the results.
        
        Args:
            query: The research query to process.
            session_id: Unique identifier for the research session.
            
        Returns:
            AgentResponse containing the research results or error information.
            
        Raises:
            ValueError: If the query or session_id is invalid.
            RuntimeError: If the research workflow fails.
            
        Example:
            ```python
            agent = ResearchAgent()
            response = agent.invoke("climate change", "session-123")
            if response["is_task_complete"]:
                print(response["content"])
            ```
        """
        ...
    
    async def stream(self, query: str, session_id: str) -> AsyncIterable[AgentResponse]:
        """Process a research query and stream updates as they occur.
        
        This method provides real-time updates as the research progresses through
        each stage of the workflow. Each update includes the current stage,
        content, and status information.
        
        Args:
            query: The research query to process.
            session_id: Unique identifier for the research session.
            
        Yields:
            AgentResponse containing the current stage and content.
            Each response includes:
                - is_task_complete: Whether the research is complete
                - content: Current content or update message
                - error: Optional error message
                - session_id: Session identifier
                - timestamp: Unix timestamp of the update
            
        Raises:
            ValueError: If the query or session_id is invalid.
            RuntimeError: If the research workflow fails.
            TimeoutError: If the operation exceeds the configured timeout.
            
        Example:
            ```python
            async for update in agent.stream("climate change", "session-123"):
                if update["is_complete"]:
                    print("Research complete!")
                else:
                    print(f"Content: {update['content']}")
            ```
        """
        ...

class ResearchAgent:
    """Agent that processes research queries through a multi-step workflow.
    
    This agent implements a research workflow that:
    1. Extracts a research topic from the user's query
    2. Conducts research on the topic
    3. Analyzes the findings and generates a report
    
    The agent maintains session state and handles errors gracefully.
    
    Attributes:
        config: Configuration for the agent.
        llm: Language model for processing queries.
        _workflow: The compiled research workflow graph.
        _memory: Memory saver for workflow state.
        _session_states: Dictionary of active session states.
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        """Initialize the ResearchAgent.
        
        Args:
            config: Optional configuration for the agent. If None, uses default settings.
            
        Raises:
            RuntimeError: If the language model or workflow initialization fails.
        """
        self.config = config or AgentConfig()
        self.llm = create_chat_model()
        self._memory = MemorySaver()
        self._workflow = self._create_workflow()
        self._session_states: Dict[str, Dict[str, Any]] = {}
    
    def _create_workflow(self) -> StateGraph:
        """Create and configure the research workflow graph.
        
        Returns:
            StateGraph: A compiled workflow graph for processing research queries.
            
        Raises:
            RuntimeError: If workflow creation or compilation fails.
        """
        workflow = StateGraph(ResearchState)
        
        # Add nodes to the graph
        workflow.add_node("node_research_topic_extraction", self._research_topic_extraction_node)
        workflow.add_node("node_researcher", self._researcher_node)
        workflow.add_node("node_analyst", self._analyst_node)
        
        # Configure the workflow
        workflow.set_entry_point("node_research_topic_extraction")
        workflow.add_edge("node_research_topic_extraction", "node_researcher")
        workflow.add_edge("node_researcher", "node_analyst")
        workflow.set_finish_point("node_analyst")
        
        return workflow.compile(checkpointer=self._memory)
    
    def _validate_input(self, query: str, session_id: str) -> Optional[str]:
        """Validate input parameters.
        
        Args:
            query: The research query to validate.
            session_id: The session ID to validate.
            
        Returns:
            Optional[str]: Error message if validation fails, None if validation passes.
            
        Example:
            ```python
            error = agent._validate_input("climate change", "session-123")
            if error:
                print(f"Validation failed: {error}")
            ```
        """
        if not query or not query.strip():
            return "Query cannot be empty"
        
        if len(query) > self.config.max_query_length:
            return f"Query exceeds maximum length of {self.config.max_query_length} characters"
        
        if not SESSION_ID_PATTERN.match(session_id):
            return "Invalid session ID format"
        
        return None
    
    def _cleanup_old_sessions(self) -> None:
        """Remove sessions older than max_session_age_hours.
        
        This method helps prevent memory leaks by cleaning up old session data.
        It's called automatically before processing new queries.
        """
        current_time = time.time()
        cutoff_time = current_time - (self.config.max_session_age_hours * 3600)
        
        self._session_states = {
            session_id: state 
            for session_id, state in self._session_states.items()
            if state.get('timestamp', 0) > cutoff_time
        }
    
    def _research_topic_extraction_node(self, state: ResearchState) -> Dict[str, Any]:
        """Extract research topic from user query.
        
        Args:
            state: Current workflow state containing the user query.
            
        Returns:
            Dict[str, Any]: Updated state with extracted research topic or error.
            
        Raises:
            ValueError: If topic extraction fails.
        """
        try:
            prompt = PromptTemplate(
                input_variables=["user_query"],
                template="""
                Extract the topic to conduct a research from the following query:
                {user_query}
                
                Topic:
                """
            )
            message = HumanMessage(content=prompt.format(user_query=state["user_query"]))
            research_topic = self.llm.invoke([message]).content.strip()
            
            if not research_topic:
                raise ValueError("Failed to extract research topic")
                
            return {"research_topic": research_topic, "error": None}
        except Exception as e:
            logger.error(f"Error in research topic extraction: {str(e)}")
            return {"research_topic": "", "error": str(e)}
    
    def _researcher_node(self, state: ResearchState) -> Dict[str, Any]:
        """Conduct research on the extracted topic.
        
        Args:
            state: Current workflow state containing the research topic.
            
        Returns:
            Dict[str, Any]: Updated state with research findings or error.
            
        Raises:
            ValueError: If research generation fails.
        """
        if state.get("error"):
            return state
            
        try:
            prompt = PromptTemplate.from_template(
                """
                You are an experienced research specialist for {research_topic} with a talent for finding relevant information from various sources.
                You excel at organizing information in a clear and structured manner, making complex topics accessible to others.
                
                Your goal:
                Find comprehensive and accurate information about {research_topic} with a focus on recent developments and key insights.
                
                Your task:
                Conduct thorough research on {research_topic}. Focus on:
                    1. Key concepts and definitions
                    2. Historical development and recent trends
                    3. Major challenges and opportunities
                    4. Notable applications or case studies
                    5. Future outlook and potential developments
                Make sure to organize your findings in a structured format with clear sections.
                
                Expected output:
                A comprehensive research document with well-organized sections covering all the requested aspects of {research_topic}.
                Include specific facts, figures, and examples where relevant.
                
                Your research findings:
                """
            )
            chain = prompt | self.llm
            response = chain.invoke({"research_topic": state["research_topic"]})
            
            if not response.content:
                raise ValueError("Failed to generate research findings")
                
            return {"research_findings": response.content, "error": None}
        except Exception as e:
            logger.error(f"Error in researcher node: {str(e)}")
            return {"research_findings": "", "error": str(e)}
    
    def _analyst_node(self, state: ResearchState) -> Dict[str, Any]:
        """Analyze research findings and generate a report.
        
        Args:
            state: Current workflow state containing research findings.
            
        Returns:
            Dict[str, Any]: Updated state with research report or error.
            
        Raises:
            ValueError: If report generation fails.
        """
        if state.get("error"):
            return state
            
        try:
            prompt = PromptTemplate.from_template(
                """
                You are a skilled data analyst and report writer for {research_topic} with a background in data interpretation and technical writing.
                You have a talent for identifying patterns and extracting meaningful insights from research data,
                then communicating those insights effectively through well-crafted reports.
                
                Your task:
                Analyze research findings and create a comprehensive, well-structured report on {research_topic} that presents insights in a clear and engaging way.
                The report should:
                    1. Be titled
                    2. Begin with an executive summary
                    3. Include all key information from the research
                    4. Provide insightful analysis of trends and patterns
                    5. Offer recommendations or future considerations
                    6. Be formatted in a professional, easy-to-read style with clear headings
                
                Research findings to analyze:
                {research_findings}
                
                Research report:
                """
            )
            chain = prompt | self.llm
            response = chain.invoke({
                "research_topic": state["research_topic"],
                "research_findings": state["research_findings"]
            })
            
            if not response.content:
                raise ValueError("Failed to generate research report")
                
            return {"research_report": response.content, "error": None}
        except Exception as e:
            logger.error(f"Error in analyst node: {str(e)}")
            return {"research_report": "", "error": str(e)}
    
    def invoke(self, query: str, session_id: str) -> AgentResponse:
        """Process a research query through the complete workflow.
        
        This is the main entry point for the research agent. It handles the entire
        research process from query validation to report generation.
        
        Args:
            query: The user's research query.
            session_id: Unique identifier for the research session.
            
        Returns:
            AgentResponse containing the research results or error information.
            
        Raises:
            ValueError: If the query or session_id is invalid.
            RuntimeError: If the research workflow fails.
            
        Example:
            ```python
            agent = ResearchAgent()
            response = agent.invoke(
                "What is the impact of climate change on biodiversity?",
                "session-123"
            )
            if response["is_task_complete"]:
                print(response["content"])
            else:
                print(f"Error: {response['error']}")
            ```
        """
        # Validate input
        if error := self._validate_input(query, session_id):
            return {
                'is_task_complete': False,
                'content': 'Invalid input',
                'error': error,
                'session_id': session_id,
                'timestamp': time.time()
            }
        
        # Cleanup old sessions
        self._cleanup_old_sessions()
        
        try:
            # Process the query
            config: RunnableConfig = {'configurable': {'thread_id': session_id}}
            initial_state = {
                "user_query": query,
                "timestamp": time.time(),
                "error": None
            }
            
            self._workflow.invoke(initial_state, config)
            return self._get_agent_response(config, session_id)
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return {
                'is_task_complete': False,
                'content': 'An error occurred while processing your request',
                'error': str(e),
                'session_id': session_id,
                'timestamp': time.time()
            }
    
    async def stream(self, query: str, session_id: str) -> AsyncIterable[AgentResponse]:
        """Process a research query and stream updates as they occur.
        
        This method implements the streaming interface defined in ResearchAgentProtocol.
        It processes a research query through multiple stages (topic extraction,
        research, and analysis) while providing real-time updates on the progress.
        
        The method yields updates at each stage of the workflow:
        1. Topic Extraction: Extracts the research topic from the query
        2. Research: Conducts research on the extracted topic
        3. Analysis: Analyzes findings and generates the final report
        
        Each update includes the current stage, content, and status information,
        allowing clients to track progress and handle errors appropriately.
        
        Args:
            query: The research query to process. Must be a non-empty string
                  not exceeding MAX_QUERY_LENGTH characters.
            session_id: Unique identifier for the research session. Must match
                       SESSION_ID_PATTERN.
            
        Yields:
            AgentResponse containing the current stage and content.
            Each response includes:
                - is_task_complete: Whether the research is complete
                - content: Current content or update message
                - error: Optional error message if something went wrong
                - session_id: Session identifier
                - timestamp: Unix timestamp of the update
            
        Raises:
            ValueError: If the query is empty or exceeds MAX_QUERY_LENGTH,
                       or if session_id doesn't match SESSION_ID_PATTERN.
            RuntimeError: If the research workflow fails.
            Exception: For any unexpected errors during processing.
            
        Example:
            ```python
            async def process_research(agent: ResearchAgent, query: str):
                session_id = f"session-{uuid.uuid4()}"
                try:
                    async for update in agent.stream(query, session_id):
                        if update["is_complete"]:
                            print("Research complete!")
                            print(f"Report: {update['content']}")
                        else:
                            print(f"Progress: {update['content']}")
                        if update.get("error"):
                            print(f"Error: {update['error']}")
                            break
                except Exception as e:
                    print(f"Research failed: {str(e)}")
            ```
        """
        try:
            # Add validation at the start
            if error := self._validate_input(query, session_id):
                yield {
                    'is_task_complete': False,
                    'content': 'Invalid input',
                    'error': error,
                    'session_id': session_id,
                    'timestamp': time.time()
                }
                return
            
            # Initialize workflow state
            config: RunnableConfig = {'configurable': {'thread_id': session_id}}
            initial_state = {
                "user_query": query,
                "timestamp": time.time(),
                "error": None
            }

            # Stream updates from each workflow stage
            for item in self._workflow.stream(initial_state, config, stream_mode='updates'):
                if item.get("node_research_topic_extraction"):
                    yield {
                        'is_task_complete': False,
                        'content': 'Extracting research topic...',
                        'error': None,
                        'session_id': session_id,
                        'timestamp': time.time()
                    }
                elif item.get("node_researcher"):
                    yield {
                        'is_task_complete': False,
                        'content': 'Conducting research...',
                        'error': None,
                        'session_id': session_id,
                        'timestamp': time.time()
                    }
                elif item.get("node_analyst"):
                    yield {
                        'is_task_complete': False,
                        'content': 'Generating research report...',
                        'error': None,
                        'session_id': session_id,
                        'timestamp': time.time()
                    }

            # Yield final response
            yield self._get_agent_response(config, session_id)
            
        except Exception as e:
            logger.error(f"Error in streaming workflow: {str(e)}")
            yield {
                'is_task_complete': False,
                'content': 'An error occurred during research',
                'error': str(e),
                'session_id': session_id,
                'timestamp': time.time()
            }
    
    def _get_agent_response(self, config: RunnableConfig, session_id: str) -> AgentResponse:
        """Get the agent response from the workflow state.
        
        Args:
            config: Workflow configuration containing the thread ID.
            session_id: The session identifier.
            
        Returns:
            AgentResponse containing the research results or error information.
            
        Raises:
            RuntimeError: If state retrieval fails.
        """
        try:
            state = self._workflow.get_state(config)
            result = state.values.get('research_report')
            error = state.values.get('error')
            
            if error:
                return {
                    'is_task_complete': False,
                    'content': 'Research processing failed',
                    'error': error,
                    'session_id': session_id,
                    'timestamp': time.time()
                }
            
            if result:
                return {
                    'is_task_complete': True,
                    'content': result,
                    'error': None,
                    'session_id': session_id,
                    'timestamp': time.time()
                }
            
            return {
                'is_task_complete': False,
                'content': 'Unable to generate research report',
                'error': 'No research report generated',
                'session_id': session_id,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"Error getting agent response: {str(e)}")
            return {
                'is_task_complete': False,
                'content': 'Error retrieving research results',
                'error': str(e),
                'session_id': session_id,
                'timestamp': time.time()
            }

# Example usage
async def main():
    """Example usage of the ResearchAgent's streaming functionality.
    
    This function demonstrates how to use the ResearchAgent's stream method
    to process a research query and handle the streaming updates.
    
    Example:
        ```python
        asyncio.run(main())
        # Output:
        # Extracting research topic...
        # Conducting research...
        # Generating research report...
        # Research complete!
        # [Final report content]
        ```
    """
    # Create the agent
    agent = ResearchAgent()
    
    # Use the stream method in an async context
    async for update in agent.stream(
        "What is the most important thing to do to fix the planet?",
        "test-session-123"
    ):
        print(update['content'])
        if update.get("error"):
            print(f"Error: {update['error']}")
            break
        if update["is_task_complete"]:
            print("\nResearch complete!")

# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())

