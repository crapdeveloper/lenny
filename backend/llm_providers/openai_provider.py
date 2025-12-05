"""OpenAI LLM Provider implementation."""

import json
from typing import Any, Dict, List, Optional
from openai import AsyncOpenAI
import mcp.types as types
from .base import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI provider for LLM operations."""

    def __init__(self, api_key: str):
        """Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key
        """
        self.api_key = api_key
        self.client: Optional[AsyncOpenAI] = None

    async def initialize(self) -> None:
        """Initialize the OpenAI client."""
        self.client = AsyncOpenAI(api_key=self.api_key)

    async def chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[types.Tool],
        model: str = "gpt-4-turbo-preview",
    ) -> Dict[str, Any]:
        """Send a chat message with available tools to OpenAI."""
        if not self.client:
            await self.initialize()

        # Convert MCP tools to OpenAI format
        openai_tools = []
        for tool in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            })

        # Call OpenAI
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            tools=openai_tools,
            tool_choice="auto",
        )

        response_message = response.choices[0].message

        # Check for tool calls
        if response_message.tool_calls:
            return {
                "has_tool_calls": True,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments),
                    }
                    for tc in response_message.tool_calls
                ],
                "message": response_message,
            }

        return {
            "has_tool_calls": False,
            "content": response_message.content,
        }

    async def process_tool_result(
        self,
        messages: List[Dict[str, str]],
        tool_call_id: str,
        tool_name: str,
        tool_result: str,
        model: str = "gpt-4-turbo-preview",
    ) -> Dict[str, Any]:
        """Process tool result and get final response from OpenAI."""
        if not self.client:
            await self.initialize()

        # Add tool result to messages
        messages.append({
            "tool_call_id": tool_call_id,
            "role": "tool",
            "name": tool_name,
            "content": tool_result,
        })

        # Get final response
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
        )

        return {
            "content": response.choices[0].message.content
        }

    async def generate_title(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4-turbo-preview",
    ) -> str:
        """Generate a concise title for the conversation."""
        if not self.client:
            await self.initialize()

        # Create a prompt for title generation
        # Filter out messages with empty content to avoid API errors
        title_messages = [m for m in messages if m.get("content")]
        title_messages.append({
            "role": "user",
            "content": "Summarize this conversation in 20 words or less for a title. Do not use quotes."
        })

        response = await self.client.chat.completions.create(
            model=model,
            messages=title_messages,
            max_tokens=50,
        )

        return response.choices[0].message.content.strip().strip('"')
