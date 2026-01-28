"""
Example script demonstrating how to use the RAG system programmatically.
"""

import asyncio
from agent.agent import rag_agent, AgentDependencies
from uuid import uuid4


async def simple_query_example():
    """Simple query example."""
    print("=" * 60)
    print("Example 1: Simple Query")
    print("=" * 60)
    
    # Create dependencies
    deps = AgentDependencies(session_id=str(uuid4()))
    
    # Run query
    query = "What are the symptoms of Alzheimer's disease?"
    print(f"\nQuery: {query}\n")
    
    result = await rag_agent.run(query, deps=deps)
    print(f"Response: {result.data}\n")


async def streaming_example():
    """Streaming response example."""
    print("=" * 60)
    print("Example 2: Streaming Response")
    print("=" * 60)
    
    deps = AgentDependencies(session_id=str(uuid4()))
    
    query = "What drugs treat hypertension?"
    print(f"\nQuery: {query}\n")
    print("Response: ", end="", flush=True)
    
    async with rag_agent.run_stream(query, deps=deps) as result:
        async for chunk in result.stream_text():
            print(chunk, end="", flush=True)
    
    print("\n")


async def multi_query_session():
    """Multiple queries in same session."""
    print("=" * 60)
    print("Example 3: Multi-Query Session")
    print("=" * 60)
    
    # Use same session for context
    session_id = str(uuid4())
    
    queries = [
        "What is Type 2 diabetes?",
        "What are common treatments?",
        "Are there any protein biomarkers?"
    ]
    
    for i, query in enumerate(queries, 1):
        deps = AgentDependencies(session_id=session_id)
        
        print(f"\nQuery {i}: {query}")
        result = await rag_agent.run(query, deps=deps)
        print(f"Response: {result.data[:200]}...\n")


async def tool_usage_example():
    """Example showing tool usage tracking."""
    print("=" * 60)
    print("Example 4: Tool Usage Tracking")
    print("=" * 60)
    
    deps = AgentDependencies(session_id=str(uuid4()))
    
    query = "Show me proteins related to cancer pathways"
    print(f"\nQuery: {query}\n")
    
    result = await rag_agent.run(query, deps=deps)
    
    print(f"Response: {result.data[:200]}...\n")
    
    # Check which tools were used
    if hasattr(result, '_all_messages'):
        print("Tools used:")
        for msg in result._all_messages:
            if hasattr(msg, 'parts'):
                for part in msg.parts:
                    if hasattr(part, 'tool_name'):
                        print(f"  - {part.tool_name}")


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("PrimeKG Agentic RAG - Usage Examples")
    print("=" * 60 + "\n")
    
    try:
        await simple_query_example()
        await streaming_example()
        await multi_query_session()
        await tool_usage_example()
        
        print("=" * 60)
        print("All examples completed!")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure:")
        print("  1. Databases are configured and running")
        print("  2. .env file is set up correctly")
        print("  3. Data has been ingested")
        print("  4. Run verify_setup.py to check configuration\n")


if __name__ == "__main__":
    asyncio.run(main())
