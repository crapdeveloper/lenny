"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import mcp.types as types


@dataclass
class ToolParameter:
    """Represents a parameter for a tool."""

    name: str
    type: str  # "string", "integer", "number", "boolean", "object", "array"
    description: str
    required: bool = True
    properties: Optional[Dict[str, Any]] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the provider with any necessary setup."""
        pass

    @abstractmethod
    async def chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[types.Tool],
        model: str,
    ) -> Dict[str, Any]:
        """
        Send a chat message with available tools.

        Args:
            messages: List of message dicts with "role" and "content"
            tools: List of MCP Tool objects
            model: Model identifier

        Returns:
            Dict with response data including:
            - content: Final response text
            - tool_calls: List of tool calls (if any)
        """
        pass

    @abstractmethod
    async def process_tool_result(
        self,
        messages: List[Dict[str, str]],
        tool_call_id: str,
        tool_name: str,
        tool_result: str,
        model: str,
    ) -> Dict[str, Any]:
        """
        Process the result from a tool execution and get the final response.

        Args:
            messages: Conversation history
            tool_call_id: ID of the tool call
            tool_name: Name of the tool that was executed
            tool_result: Result from tool execution
            model: Model identifier

        Returns:
            Dict with response data including:
            - content: Final response text
        """
        pass

    @abstractmethod
    async def generate_title(
        self,
        messages: List[Dict[str, str]],
        model: str,
    ) -> str:
        """
        Generate a concise title for the conversation.

        Args:
            messages: Conversation history
            model: Model identifier

        Returns:
            Generated title string
        """
        pass

    @staticmethod
    def convert_mcp_tool_to_dict(tool: types.Tool) -> Dict[str, Any]:
        """Convert MCP Tool to provider-agnostic format."""
        return {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.inputSchema,
        }
