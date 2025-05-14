import os
from langchain_core.language_models.chat_models import BaseChatModel
from langchain.chat_models import init_chat_model
from langchain_openai import AzureChatOpenAI

def create_chat_model() -> BaseChatModel:
    """
    Creates and returns an instance of a provider-specific chat model based on the environment configuration.
    The function determines the model provider and initializes the appropriate chat model.
    It supports both Azure and other providers specified via environment variables.
    
    Returns:
        An instance of the chat model initialized with the specified configuration.
    Raises:
        ValueError: If the Azure configuration is incomplete (missing AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_API_VERSION).
        ValueError: If the model name is not specified (missing CHAT_MODEL environment variable).
    """
    model_name = os.getenv('CHAT_MODEL', 'gpt-4o')
    model_provider = os.getenv('CHAT_MODEL_PROVIDER', 'openai')

    if model_provider == 'azure':
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION")

        if not azure_endpoint or not azure_api_version:
            raise ValueError("Azure configuration is incomplete. Ensure AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_VERSION are set.")

        chat_model = AzureChatOpenAI(
            azure_endpoint=azure_endpoint,
            azure_deployment=model_name,
            openai_api_version=azure_api_version
        )
    else:
        if not model_name:
            raise ValueError("Model name is not specified. Ensure CHAT_MODEL is set.")

        chat_model = init_chat_model(
            model_name=model_name,
            model_provider=model_provider,
        )

    return chat_model