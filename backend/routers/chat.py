import json
import logging
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import func

from backend.config import settings
from backend.database import get_db
from backend.llm_providers.factory import LLMProviderFactory
from backend.mcp_handlers.server import handle_call_tool, handle_list_tools, mcp_server
from backend.models import ChatMessage, Conversation, User

router = APIRouter(prefix="/chat", tags=["chat"])

# Initialize LLM provider based on config
_llm_provider = None


async def get_llm_provider():
    """Get or initialize the LLM provider."""
    global _llm_provider
    if _llm_provider is None:
        # Get API key based on provider
        if settings.LLM_PROVIDER.lower() == "openai":
            api_key = settings.OPENAI_API_KEY
        elif settings.LLM_PROVIDER.lower() == "gemini":
            api_key = settings.GEMINI_API_KEY
        else:
            raise ValueError(f"Unknown LLM provider: {settings.LLM_PROVIDER}")

        _llm_provider = LLMProviderFactory.create_provider(settings.LLM_PROVIDER, api_key)
        await _llm_provider.initialize()

    return _llm_provider


async def get_current_user(
    x_character_id: Optional[str] = Header(None, alias="X-Character-Id"),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not x_character_id:
        # For development/testing if header is missing, try to find a default user or raise error
        # raise HTTPException(status_code=401, detail="Missing X-Character-Id header")
        # Fallback for now to allow testing without auth if needed, or strict check
        pass

    if x_character_id:
        result = await db.execute(select(User).filter(User.character_id == int(x_character_id)))
        user = result.scalars().first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user

    raise HTTPException(status_code=401, detail="Authentication required")


class ConversationCreate(BaseModel):
    title: Optional[str] = "New Conversation"


class ConversationRead(BaseModel):
    id: int
    title: Optional[str]
    created_at: Any
    updated_at: Any


class MessageRead(BaseModel):
    role: str
    content: str
    created_at: Any


class ChatRequest(BaseModel):
    conversation_id: int
    message: str


@router.get("/conversations", response_model=List[ConversationRead])
async def list_conversations(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Conversation)
        .filter(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
    )
    return result.scalars().all()


@router.post("/conversations", response_model=ConversationRead)
async def create_conversation(
    conversation: ConversationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    new_conversation = Conversation(user_id=user.id, title=conversation.title)
    db.add(new_conversation)
    await db.commit()
    await db.refresh(new_conversation)
    return new_conversation


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageRead])
async def get_conversation_messages(
    conversation_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Conversation).filter(
            Conversation.id == conversation_id, Conversation.user_id == user.id
        )
    )
    conversation = result.scalars().first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await db.execute(
        select(ChatMessage)
        .filter(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at.asc())
    )
    return result.scalars().all()


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Conversation).filter(
            Conversation.id == conversation_id, Conversation.user_id == user.id
        )
    )
    conversation = result.scalars().first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await db.delete(conversation)
    await db.commit()
    return None


@router.post("/")
async def chat(
    request: ChatRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    try:
        # Verify conversation ownership
        result = await db.execute(
            select(Conversation).filter(
                Conversation.id == request.conversation_id, Conversation.user_id == user.id
            )
        )
        conversation = result.scalars().first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Save user message
        user_msg = ChatMessage(
            conversation_id=conversation.id, role="user", content=request.message
        )
        db.add(user_msg)
        await db.commit()

        provider = await get_llm_provider()

        # Validate provider has API key
        if settings.LLM_PROVIDER.lower() == "openai" and not settings.OPENAI_API_KEY:
            raise HTTPException(status_code=500, detail="OpenAI API Key not configured")
        elif settings.LLM_PROVIDER.lower() == "gemini" and not settings.GEMINI_API_KEY:
            raise HTTPException(status_code=500, detail="Gemini API Key not configured")

        # 1. Get MCP Tools
        mcp_tools = await handle_list_tools()

        # 2. Get conversation history
        history_result = await db.execute(
            select(ChatMessage)
            .filter(ChatMessage.conversation_id == conversation.id)
            .order_by(ChatMessage.created_at.asc())
        )
        history = history_result.scalars().all()
        messages = [{"role": m.role, "content": m.content} for m in history]
        # Prepend system prompt if available (simple single-file approach)
        try:
            prompt_path = (
                Path(__file__).resolve().parents[1] / "llm_providers" / "system_prompt.txt"
            )
            if prompt_path.exists():
                system_text = prompt_path.read_text(encoding="utf-8")
                messages = [{"role": "system", "content": system_text}] + messages
        except Exception:
            # Non-fatal: if prompt cannot be read, continue without it
            pass

        final_response_content = ""

        try:
            # 3. Call LLM provider with tools
            response = await provider.chat_with_tools(
                messages=messages,
                tools=mcp_tools,
                model=settings.LLM_MODEL,
            )

            # 4. Handle Tool Calls
            if response.get("has_tool_calls"):
                tool_calls = response["tool_calls"]

                for tool_call in tool_calls:
                    function_name = tool_call["name"]
                    function_args = tool_call["arguments"]
                    tool_call_id = tool_call["id"]

                    # Execute the tool using the MCP handler
                    try:
                        tool_results = await handle_call_tool(function_name, function_args)

                        # Combine results into a string
                        content = ""
                        for result in tool_results:
                            if result.type == "text":
                                content += result.text
                            # Handle other types if necessary
                    except Exception as e:
                        # If tool execution fails, pass the error to the LLM
                        logging.error(f"Tool execution failed: {str(e)}")
                        logging.error(traceback.format_exc())
                        content = f"Error executing tool {function_name}: {str(e)}"

                    # 5. Process tool result and get final response
                    final_response = await provider.process_tool_result(
                        messages=messages,
                        tool_call_id=tool_call_id,
                        tool_name=function_name,
                        tool_result=content,
                        model=settings.LLM_MODEL,
                    )

                    final_response_content = final_response.get("content", "")
            else:
                # No tool calls, return direct response
                final_response_content = response.get("content", "")

            # Save assistant response
            assistant_msg = ChatMessage(
                conversation_id=conversation.id, role="assistant", content=final_response_content
            )
            db.add(assistant_msg)
            conversation.updated_at = func.now()

            # Generate and update title
            try:
                full_history = messages + [{"role": "assistant", "content": final_response_content}]
                logging.info(f"Generating title for conversation {conversation.id}...")
                new_title = await provider.generate_title(full_history, model=settings.LLM_MODEL)
                logging.info(f"Generated title: {new_title}")
                if new_title:
                    conversation.title = new_title
                    db.add(conversation)  # Ensure it's marked for update
            except Exception as e:
                logging.error(f"Failed to generate title: {e}")

            await db.commit()

            return {"role": "assistant", "content": final_response_content}

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "Quota exceeded" in error_msg:
                raise HTTPException(status_code=429, detail=error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Chat endpoint failed: {str(e)}")
        logging.error(traceback.format_exc())
        error_msg = str(e)
        if "429" in error_msg or "Quota exceeded" in error_msg:
            raise HTTPException(status_code=429, detail=error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
