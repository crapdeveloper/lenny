"""Factory for creating LLM providers."""

from typing import Optional

from .base import LLMProvider
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider


class LLMProviderFactory:
    """Factory for creating LLM provider instances."""

    @staticmethod
    def create_provider(
        provider_type: str,
        api_key: str,
    ) -> LLMProvider:
        """
        Create an LLM provider instance.

        Args:
            provider_type: Type of provider ("openai" or "gemini")
            api_key: API key for the provider

        Returns:
            LLMProvider instance

        Raises:
            ValueError: If provider_type is not supported
        """
        provider_type = provider_type.lower()

        if provider_type == "openai":
            return OpenAIProvider(api_key)
        elif provider_type == "gemini":
            return GeminiProvider(api_key)
        else:
            raise ValueError(
                f"Unsupported LLM provider: {provider_type}. "
                f"Supported providers: openai, gemini"
            )
