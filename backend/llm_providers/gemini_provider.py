"""Google Gemini LLM Provider implementation."""

import json
from typing import Any, Dict, List, Optional

import google.generativeai as genai

import mcp.types as types

from .base import LLMProvider


class GeminiProvider(LLMProvider):
    """Google Gemini provider for LLM operations."""

    def __init__(self, api_key: str):
        """Initialize Gemini provider.

        Args:
            api_key: Google Gemini API key
        """
        self.api_key = api_key
        self.model = None

    async def initialize(self) -> None:
        """Initialize the Gemini client."""
        genai.configure(api_key=self.api_key)

    async def chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[types.Tool],
        model: str = "gemini-1.5-pro",
    ) -> Dict[str, Any]:
        """Send a chat message with available tools to Gemini."""
        if not self.model:
            await self.initialize()

        # Convert MCP tools to Gemini format
        gemini_tools = []
        for tool in tools:
            # Convert JSON schema properties to a dictionary compatible with Gemini
            properties = {}
            for k, v in tool.inputSchema.get("properties", {}).items():
                properties[k] = self._convert_schema(v)

            gemini_tools.append(
                genai.types.Tool(
                    function_declarations=[
                        genai.types.FunctionDeclaration(
                            name=tool.name,
                            description=tool.description,
                            parameters={
                                "type": "OBJECT",
                                "properties": properties,
                                "required": tool.inputSchema.get("required", []),
                            },
                        )
                    ]
                )
            )

        # Convert messages to Gemini format
        gemini_messages = []
        for msg in messages:
            role = msg["role"]
            if role == "assistant":
                role = "model"

            gemini_messages.append(
                {
                    "role": role,
                    "parts": [{"text": msg["content"]}],
                }
            )

        # Call Gemini
        client = genai.GenerativeModel(model, tools=gemini_tools)
        response = client.generate_content(gemini_messages)

        # Check for function calls
        if response.candidates and response.candidates[0].content.parts:
            parts = response.candidates[0].content.parts
            tool_calls = []

            for part in parts:
                if part.function_call:
                    tool_calls.append(
                        {
                            "id": part.function_call.name,  # Using name as ID
                            "name": part.function_call.name,
                            "arguments": {k: v for k, v in part.function_call.args.items()},
                        }
                    )

            if tool_calls:
                return {
                    "has_tool_calls": True,
                    "tool_calls": tool_calls,
                    "message": response,
                }

        # Extract text response
        content = ""
        if response.text:
            content = response.text

        return {
            "has_tool_calls": False,
            "content": content,
        }

    async def process_tool_result(
        self,
        messages: List[Dict[str, str]],
        tool_call_id: str,
        tool_name: str,
        tool_result: str,
        model: str = "gemini-1.5-pro",
    ) -> Dict[str, Any]:
        """Process tool result and get final response from Gemini."""
        if not self.model:
            await self.initialize()

        # Add tool result to messages
        messages.append(
            {
                "role": "user",
                "content": f"Tool {tool_name} returned: {tool_result}",
            }
        )

        # Convert messages to Gemini format
        gemini_messages = []
        for msg in messages:
            role = msg["role"]
            if role == "assistant":
                role = "model"

            gemini_messages.append(
                {
                    "role": role,
                    "parts": [{"text": msg.get("content", "")}],
                }
            )

        # Get final response
        client = genai.GenerativeModel(model)
        response = client.generate_content(gemini_messages)

        return {"content": response.text if response.text else ""}

    async def generate_title(
        self,
        messages: List[Dict[str, str]],
        model: str = "gemini-1.5-pro",
    ) -> str:
        """Generate a concise title for the conversation."""
        if not self.model:
            await self.initialize()

        # Create a prompt for title generation
        # Convert messages to Gemini format
        gemini_messages = []
        for msg in messages:
            content = msg.get("content", "")
            if not content:
                continue

            role = msg["role"]
            if role == "assistant":
                role = "model"

            gemini_messages.append(
                {
                    "role": role,
                    "parts": [{"text": content}],
                }
            )

        gemini_messages.append(
            {
                "role": "user",
                "parts": [
                    {
                        "text": "Summarize this conversation in 20 words or less for a title. Do not use quotes."
                    }
                ],
            }
        )

        client = genai.GenerativeModel(model)
        response = client.generate_content(gemini_messages)

        return response.text.strip().strip('"') if response.text else "New Conversation"

    @staticmethod
    def _convert_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
        """Convert JSON schema to Gemini Schema format (dict)."""
        schema_type = schema.get("type", "string")
        type_map = {
            "string": "STRING",
            "integer": "INTEGER",
            "number": "NUMBER",
            "boolean": "BOOLEAN",
            "array": "ARRAY",
            "object": "OBJECT",
        }

        return {
            "type": type_map.get(schema_type, "STRING"),
            "description": schema.get("description", ""),
        }
