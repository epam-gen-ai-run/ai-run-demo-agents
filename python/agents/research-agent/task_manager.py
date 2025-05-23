import asyncio
import logging
import traceback
import os
from collections.abc import AsyncIterable

from agent import ResearchAgent, AgentResponse
from common.server import utils
from common.server.task_manager import InMemoryTaskManager
from common.types import (
    Artifact,
    InternalError,
    JSONRPCResponse,
    Message,
    SendTaskRequest,
    SendTaskResponse,
    SendTaskStreamingRequest,
    SendTaskStreamingResponse,
    Task,
    TaskArtifactUpdateEvent,
    TaskIdParams,
    TaskSendParams,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
)


# Configure logging
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AgentTaskManager(InMemoryTaskManager):
    """Task manager for handling ResearchAgent operations.
    
    This class manages the execution of research tasks, both synchronous and
    streaming, and handles the communication between the agent and the client.
    
    Attributes:
        agent: The ResearchAgent instance to handle research operations.
    """
    
    def __init__(self, agent: ResearchAgent):
        """Initialize the AgentTaskManager.
        
        Args:
            agent: The ResearchAgent instance to use for research operations.
        """
        super().__init__()
        self.agent = agent

    async def _run_streaming_agent(self, request: SendTaskStreamingRequest):
        """Run the research agent in streaming mode.
        
        This method processes a research query through the agent's streaming
        interface and updates the task status and artifacts as updates arrive.
        
        Args:
            request: The streaming task request containing the query and parameters.
            
        The method handles:
            - Streaming updates from the research workflow
            - Task state management
            - Artifact updates
            - Error handling and reporting
        """
        task_send_params: TaskSendParams = request.params
        query = self._get_user_query(task_send_params)

        try:
            async for update in self.agent.stream(
                query, task_send_params.sessionId
            ):
                # Convert update to AgentResponse for type safety
                response = AgentResponse(**update)
                
                # Prepare message parts
                parts = [{'type': 'text', 'text': response['content']}]
                message = Message(role='agent', parts=parts)
                
                # Determine task state and completion
                if response['error']:
                    task_state = TaskState.FAILED
                    end_stream = True
                    artifact = None
                elif response['is_task_complete']:
                    task_state = TaskState.COMPLETED
                    end_stream = True
                    artifact = Artifact(parts=parts, index=0, append=False)
                else:
                    task_state = TaskState.WORKING
                    end_stream = False
                    artifact = None

                # Update task status
                task_status = TaskStatus(state=task_state, message=message)
                latest_task = await self.update_store(
                    task_send_params.id,
                    task_status,
                    None if artifact is None else [artifact],
                )

                # Send artifact update if available
                if artifact:
                    task_artifact_update_event = TaskArtifactUpdateEvent(
                        id=task_send_params.id, artifact=artifact
                    )
                    await self.enqueue_events_for_sse(
                        task_send_params.id, task_artifact_update_event
                    )

                # Send status update
                task_update_event = TaskStatusUpdateEvent(
                    id=task_send_params.id,
                    status=task_status,
                    final=end_stream
                )
                await self.enqueue_events_for_sse(
                    task_send_params.id, task_update_event
                )

                # Break the stream if we've reached a terminal state
                if end_stream:
                    break

        except Exception as e:
            logger.error(
                'Error in streaming workflow: %s\n%s',
                str(e),
                traceback.format_exc()
            )
            error_message = f'An error occurred during research: {str(e)}'
            await self._handle_streaming_error(
                task_send_params.id, error_message
            )

    async def _handle_streaming_error(
        self, task_id: str, error_message: str
    ) -> None:
        """Handle errors in the streaming workflow.
        
        Args:
            task_id: The ID of the task that encountered an error.
            error_message: The error message to report.
        """
        # Update task status to error
        task_status = TaskStatus(
            state=TaskState.FAILED,
            message=Message(
                role='agent',
                parts=[{'type': 'text', 'text': error_message}]
            )
        )
        await self.update_store(task_id, task_status, None)
        
        # Send error notification
        await self.enqueue_events_for_sse(
            task_id,
            TaskStatusUpdateEvent(
                id=task_id,
                status=task_status,
                final=True
            )
        )
        
        # Send error event
        await self.enqueue_events_for_sse(
            task_id,
            InternalError(message=error_message)
        )

    def _validate_request(
        self, request: SendTaskRequest | SendTaskStreamingRequest
    ) -> JSONRPCResponse | None:
        """Validate the incoming request.
        
        Args:
            request: The request to validate.
            
        Returns:
            JSONRPCResponse with error if validation fails, None otherwise.
        """
        task_send_params: TaskSendParams = request.params
        
        # Validate output modes
        if not utils.are_modalities_compatible(
            task_send_params.acceptedOutputModes,
            self.agent.config.supported_content_types,
        ):
            logger.warning(
                'Unsupported output mode. Received %s, Support %s',
                task_send_params.acceptedOutputModes,
                self.agent.config.supported_content_types,
            )
            return utils.new_incompatible_types_error(request.id)

        # Validate query
        try:
            query = self._get_user_query(task_send_params)
            if not query or len(query) > self.agent.config.max_query_length:
                return JSONRPCResponse(
                    id=request.id,
                    error=InternalError(
                        message=f'Invalid query length. Maximum allowed: {self.agent.config.max_query_length}'
                    )
                )
        except ValueError as e:
            return JSONRPCResponse(
                id=request.id,
                error=InternalError(message=str(e))
            )

        return None

    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        """Handle synchronous task requests.
        
        Args:
            request: The task request to process.
            
        Returns:
            SendTaskResponse containing the task result or error.
            
        Raises:
            ValueError: If the agent invocation fails.
        """
        validation_error = self._validate_request(request)
        if validation_error:
            return SendTaskResponse(id=request.id, error=validation_error.error)

        await self.upsert_task(request.params)
        task = await self.update_store(
            request.params.id,
            TaskStatus(state=TaskState.WORKING),
            None
        )

        task_send_params: TaskSendParams = request.params
        query = self._get_user_query(task_send_params)
        
        try:
            agent_response = self.agent.invoke(
                query, task_send_params.sessionId
            )
            return await self._process_agent_response(request, agent_response)
        except Exception as e:
            logger.error('Error invoking agent: %s\n%s', str(e), traceback.format_exc())
            raise ValueError(f'Error invoking agent: {str(e)}')

    async def on_send_task_subscribe(
        self, request: SendTaskStreamingRequest
    ) -> AsyncIterable[SendTaskStreamingResponse] | JSONRPCResponse:
        """Handle streaming task requests.
        
        Args:
            request: The streaming task request to process.
            
        Returns:
            AsyncIterable of streaming responses or error response.
        """
        try:
            error = self._validate_request(request)
            if error:
                return error

            await self.upsert_task(request.params)
            task_send_params: TaskSendParams = request.params
            
            # Set up SSE consumer
            sse_event_queue = await self.setup_sse_consumer(
                task_send_params.id, False
            )

            # Start streaming task
            asyncio.create_task(self._run_streaming_agent(request))

            return self.dequeue_events_for_sse(
                request.id, task_send_params.id, sse_event_queue
            )
        except Exception as e:
            logger.error(
                'Error in SSE stream: %s\n%s',
                str(e),
                traceback.format_exc()
            )
            return JSONRPCResponse(
                id=request.id,
                error=InternalError(
                    message='An error occurred while setting up the stream'
                )
            )

    async def _process_agent_response(
        self, request: SendTaskRequest, agent_response: AgentResponse
    ) -> SendTaskResponse:
        """Process the agent's response and update the task store.
        
        Args:
            request: The original task request.
            agent_response: The response from the agent.
            
        Returns:
            SendTaskResponse containing the processed task result.
        """
        task_send_params: TaskSendParams = request.params
        task_id = task_send_params.id
        history_length = task_send_params.historyLength

        # Prepare message parts
        parts = [{'type': 'text', 'text': agent_response['content']}]
        
        # Determine task status based on response
        if agent_response['error']:
            task_status = TaskStatus(
                state=TaskState.FAILED,
                message=Message(role='agent', parts=parts)
            )
            artifact = None
        elif agent_response['is_task_complete']:
            task_status = TaskStatus(state=TaskState.COMPLETED)
            artifact = Artifact(parts=parts, index=0, append=False)
        else:
            task_status = TaskStatus(
                state=TaskState.WORKING,
                message=Message(role='agent', parts=parts)
            )
            artifact = None

        # Update task store
        task = await self.update_store(
            task_id,
            task_status,
            None if artifact is None else [artifact]
        )
        
        # Prepare response
        task_result = self.append_task_history(task, history_length)
        
        return SendTaskResponse(id=request.id, result=task_result)

    def _get_user_query(self, task_send_params: TaskSendParams) -> str:
        """Extract and validate the user query from task parameters.
        
        Args:
            task_send_params: The task parameters containing the query.
            
        Returns:
            The extracted query text.
            
        Raises:
            ValueError: If the query is not in a supported format.
        """
        if not task_send_params.message.parts:
            raise ValueError('No message parts provided')
            
        part = task_send_params.message.parts[0]
        if not isinstance(part, TextPart):
            raise ValueError('Only text parts are supported')
            
        return part.text

    async def on_resubscribe_to_task(
        self, request
    ) -> AsyncIterable[SendTaskStreamingResponse] | JSONRPCResponse:
        """Handle task resubscription requests.
        
        Args:
            request: The resubscription request.
            
        Returns:
            AsyncIterable of streaming responses or error response.
        """
        task_id_params: TaskIdParams = request.params
        try:
            sse_event_queue = await self.setup_sse_consumer(
                task_id_params.id, True
            )
            return self.dequeue_events_for_sse(
                request.id, task_id_params.id, sse_event_queue
            )
        except Exception as e:
            logger.error(
                'Error while reconnecting to SSE stream: %s\n%s',
                str(e),
                traceback.format_exc()
            )
            return JSONRPCResponse(
                id=request.id,
                error=InternalError(
                    message=f'An error occurred while reconnecting to stream: {str(e)}'
                )
            )


# Example usage
async def main():
    """Example usage of the AgentTaskManager."""
    agent = ResearchAgent()
    task_manager = AgentTaskManager(agent)

    # Create a streaming request with all required fields
    request = SendTaskStreamingRequest(
        id="test-request-1",
        params=TaskSendParams(
            id="test-task-1",
            sessionId="test-session-1",  # Required for session management
            message=Message(
                role="user",  # Required field for Message
                parts=[TextPart(text="What is the most important thing to do to fix the planet?")]
            ),
            acceptedOutputModes=["text"],  # Required for output mode validation
            historyLength=5  # Required for history tracking
        )
    )

    try:
        # First await the subscription to get the stream
        stream = await task_manager.on_send_task_subscribe(request)
        
        # Check if we got an error response
        if isinstance(stream, dict) and "error" in stream:
            print(f"Error: {stream['error'].message}")
            return
            
        # Now we can iterate over the stream
        async for response in stream:
            print(">>> RESPONSE:", response)
    except Exception as e:
        print(f"Error during streaming: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
