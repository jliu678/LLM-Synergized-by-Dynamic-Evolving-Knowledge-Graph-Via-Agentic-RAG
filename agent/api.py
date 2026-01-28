"""
FastAPI application for the agentic RAG system.
"""

import os
import logging
import re
from collections import Counter
from contextlib import asynccontextmanager
from typing import Optional
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import asyncio

from .agent import rag_agent, AgentDependencies
from .models import ChatRequest, ChatResponse, ToolCall
from .db_utils import get_pool, close_pool, create_session, add_message, get_session
from .graph_utils import get_graphiti_client, close_graphiti

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    # Startup
    logger.info("Starting up application...")
    await get_pool()  # Initialize database pool
    await get_graphiti_client()  # Initialize Graphiti
    logger.info("Application started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    await close_pool()
    await close_graphiti()
    logger.info("Application shutdown complete")


app = FastAPI(
    title="PrimeKG Agentic RAG API",
    description="Biomedical knowledge retrieval with PrimeKG and Graphiti",
    version="0.1.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "primekg-rag"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint (non-streaming).
    
    Args:
        request: Chat request with message and optional session_id
    
    Returns:
        Chat response with assistant message and tool calls
    """
    try:
        logger.info(f"Chat request: message='{request.message}' session_id='{request.session_id}'")
        
        # Get or create session
        if request.session_id:
            try:
                session_id = UUID(request.session_id)
                logger.info(f"Parsed existing session_id: {session_id}")
            except ValueError as e:
                logger.error(f"Invalid session_id format: {request.session_id}")
                raise HTTPException(status_code=400, detail="Invalid session ID format")
            
            session = await get_session(session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
        else:
            session_id = await create_session(request.user_id)
            logger.info(f"Created new session_id: {session_id}")
        
        # Save user message
        await add_message(session_id, "user", request.message)
        
        # Create dependencies
        deps = AgentDependencies(
            session_id=str(session_id),
            user_id=request.user_id
        )
        
        # Run agent with model settings to prevent repetition
        logger.info("Running agent...")
        try:
            # Apply model settings at runtime as well (in case constructor settings aren't applied)
            from pydantic_ai.settings import ModelSettings
            runtime_settings: ModelSettings = {
                "frequency_penalty": 1.2,  # Strong penalty to prevent repetition
                "presence_penalty": 1.0,   # Strong penalty for repeated tokens
                "max_tokens": 1500,        # Limit response length
            }
            result = await rag_agent.run(request.message, deps=deps, model_settings=runtime_settings)
            logger.info("Agent run completed")
        except Exception as ae:
            logger.error(f"Agent run failed: {ae}", exc_info=True)
            raise ae
        
        # Extract tool calls
        tool_calls = []
        if hasattr(result, '_all_messages'):
            for msg in result._all_messages:
                if hasattr(msg, 'parts'):
                    for part in msg.parts:
                        if hasattr(part, 'tool_name'):
                            tool_calls.append(ToolCall(
                                tool_name=part.tool_name,
                                arguments=part.args if hasattr(part, 'args') else {}
                            ))
        
        # Save assistant message
        await add_message(
            session_id,
            "assistant",
            result.output,
            [tc.model_dump() for tc in tool_calls] if tool_calls else None
        )
        
        return ChatResponse(
            message=result.output,
            session_id=str(session_id),
            tool_calls=tool_calls
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint using Server-Sent Events.
    
    Args:
        request: Chat request
    
    Returns:
        Streaming response
    """
    async def generate():
        try:
            logger.info(f"Stream request: message='{request.message}' session_id='{request.session_id}'")
            
            # Get or create session
            if request.session_id:
                try:
                    session_id = UUID(request.session_id)
                except ValueError:
                    yield f"data: Error: Invalid session ID format\n\n"
                    return
            else:
                session_id = await create_session(request.user_id)
            
            # Save user message
            await add_message(session_id, "user", request.message)
            
            # Create dependencies
            deps = AgentDependencies(
                session_id=str(session_id),
                user_id=request.user_id
            )
            
            # Stream response with model settings to prevent repetition
            full_response = ""
            logger.info("Starting stream...")
            try:
                # Apply model settings at runtime
                from pydantic_ai.settings import ModelSettings
                runtime_settings: ModelSettings = {
                    "frequency_penalty": 1.2,  # Strong penalty to prevent repetition
                    "presence_penalty": 1.0,   # Strong penalty for repeated tokens
                    "max_tokens": 800,         # Reduce max tokens to prevent huge responses
                }
                async with rag_agent.run_stream(request.message, deps=deps, model_settings=runtime_settings) as result:
                    async for chunk in result.stream_text():
                        full_response += chunk
                        
                        # Debug: Log every chunk
                        logger.info(f"Received chunk: '{chunk}', total length: {len(full_response)}")
                        
                        # IMMEDIATE repetition detection - check after every chunk
                        should_stop = False
                        
                        # Check for "Cancer – an overview" pattern specifically
                        if "Cancer – an overview" in full_response:
                            count = full_response.count("Cancer – an overview")
                            if count >= 3:  # Increased threshold
                                logger.warning(f"Detected 'Cancer – an overview' repeated {count} times, stopping stream")
                                yield f"data: \n\n[Response stopped: Repetition detected]\n\n"
                                should_stop = True
                        
                        # Check for any bold pattern repeated 3+ times (much less sensitive)
                        if not should_stop and len(full_response) > 200:  # Increased content threshold
                            bold_patterns = re.findall(r'\*\*([^*]+)\*\*', full_response)
                            if len(bold_patterns) >= 3:
                                pattern_counts = Counter(bold_patterns)
                                for pattern, count in pattern_counts.items():
                                    if count >= 3 and len(pattern.strip()) > 5:  # Increased thresholds
                                        logger.warning(f"Detected repeated bold pattern '{pattern}' {count} times, stopping stream")
                                        yield f"data: \n\n[Response stopped: Repetition detected]\n\n"
                                        should_stop = True
                                        break
                        
                        # Check for any phrase repeated 4+ times (very lenient threshold)
                        if not should_stop and len(full_response.split()) >= 10:
                            words = full_response.split()
                            # Check consecutive words
                            for i in range(len(words) - 3):
                                phrase = f"{words[i]} {words[i+1]} {words[i+2]} {words[i+3]}"
                                if len(phrase.strip()) > 8:
                                    count = full_response.count(phrase)
                                    if count >= 4:  # Very high threshold for phrases
                                        logger.warning(f"Detected repeated phrase '{phrase}' {count} times, stopping stream")
                                        yield f"data: \n\n[Response stopped: Repetition detected]\n\n"
                                        should_stop = True
                                        break
                        
                        if should_stop:
                            break
                        
                        yield f"data: {chunk}\n\n"
                        
            except Exception as stream_error:
                logger.error(f"Streaming failed, falling back to non-streaming: {stream_error}")
                # Fallback to non-streaming
                try:
                    fallback_settings: ModelSettings = {
                        "frequency_penalty": 1.2,
                        "presence_penalty": 1.0,
                        "max_tokens": 800,
                    }
                    fallback_result = await rag_agent.run(request.message, deps=deps, model_settings=fallback_settings)
                    full_response = fallback_result.output
                    logger.info(f"Fallback response length: {len(full_response)}")
                    
                    # Send the complete response as one chunk
                    yield f"data: {full_response}\n\n"
                    
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed: {fallback_error}")
                    yield f"data: Error: Unable to generate response due to streaming issues.\n\n"
                    return
            
            # Save assistant message
            await add_message(session_id, "assistant", full_response)
            
            yield f"data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            yield f"data: Error: {str(e)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("APP_PORT", 8058))
    uvicorn.run(app, host="0.0.0.0", port=port)
