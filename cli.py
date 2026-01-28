"""
Interactive CLI for the PrimeKG Agentic RAG system.
"""

import asyncio
import argparse
import sys
from typing import Optional
import httpx
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

console = Console()
import sys as _sys


class RAGClient:
    """Client for interacting with the RAG API."""
    
    def __init__(self, base_url: str):
        """Initialize client with API base URL."""
        self.base_url = base_url.rstrip('/')
        self.session_id: Optional[str] = None
    
    async def health_check(self) -> bool:
        """Check if API is healthy."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/health", timeout=5.0)
                return response.status_code == 200
        except Exception:
            return False
    
    async def chat(self, message: str) -> dict:
        """Send a chat message (non-streaming)."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat",
                json={
                    "message": message,
                    "session_id": self.session_id
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # Save session ID
            if not self.session_id:
                self.session_id = data.get("session_id")
            
            return data
    
    async def chat_stream(self, message: str, max_retries: int = 2):
        """Send a chat message with streaming response and retry logic."""
        for attempt in range(max_retries + 1):
            try:
                timeout = httpx.Timeout(60.0, connect=10.0, read=30.0)
                async with httpx.AsyncClient(timeout=timeout) as client:
                    async with client.stream(
                        "POST",
                        f"{self.base_url}/chat/stream",
                        json={
                            "message": message,
                            "session_id": self.session_id
                        }
                    ) as response:
                        response.raise_for_status()
                        
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                data = line[6:]  # Remove "data: " prefix
                                if data == "[DONE]":
                                    break
                                elif data.startswith("[Response stopped:"):
                                    # Handle repetition detection stops
                                    yield data
                                    break
                                yield data
                        return  # Success, exit retry loop
                        
            except (httpx.ReadError, httpx.ConnectError, httpx.TimeoutException) as e:
                if attempt < max_retries:
                    # Wait before retry (exponential backoff)
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # All retries failed, raise the last error
                    raise e
            except Exception as e:
                # Non-network error, don't retry
                raise e


async def main():
    """Main CLI loop."""
    parser = argparse.ArgumentParser(description="PrimeKG Agentic RAG CLI")
    parser.add_argument("--url", default="http://localhost:8058", help="API base URL")
    parser.add_argument("--port", type=int, help="API port (overrides URL)")
    
    args = parser.parse_args()
    
    # Construct base URL
    if args.port:
        base_url = f"http://localhost:{args.port}"
    else:
        base_url = args.url
    
    client = RAGClient(base_url)
    
    # Print header
    console.print()
    console.print(Panel.fit(
        "[bold cyan]🧬 PrimeKG Agentic RAG CLI[/bold cyan]\n"
        "[dim]Biomedical Knowledge Retrieval System[/dim]",
        border_style="cyan"
    ))
    console.print()
    
    # Health check
    console.print("[yellow]Checking API connection...[/yellow]")
    if await client.health_check():
        console.print(f"[green]✓ Connected to {base_url}[/green]")
    else:
        console.print(f"[red]✗ Failed to connect to {base_url}[/red]")
        console.print("[yellow]Make sure the API server is running:[/yellow]")
        console.print("  python -m agent.api")
        sys.exit(1)
    
    console.print()
    console.print("[dim]Type 'help' for commands, 'exit' to quit[/dim]")
    console.print("[dim]" + "─" * 60 + "[/dim]")
    console.print()
    
    # Main loop
    while True:
        try:
            # Get user input
            user_input = console.input("[bold green]You:[/bold green] ")
            
            if not user_input.strip():
                continue
            
            # Handle commands
            if user_input.lower() in ['exit', 'quit', 'q']:
                console.print("[yellow]Goodbye![/yellow]")
                break
            
            elif user_input.lower() == 'help':
                console.print()
                console.print("[bold cyan]Available Commands:[/bold cyan]")
                console.print("  [green]help[/green]   - Show this help message")
                console.print("  [green]health[/green] - Check API connection")
                console.print("  [green]clear[/green]  - Clear session and start fresh")
                console.print("  [green]exit[/green]   - Exit the CLI")
                console.print()
                console.print("[bold cyan]Example Queries:[/bold cyan]")
                console.print("  • What are the symptoms of Alzheimer's disease?")
                console.print("  • What drugs treat hypertension?")
                console.print("  • Show me proteins related to cancer pathways")
                console.print("  • How does aspirin work?")
                console.print()
                continue
            
            elif user_input.lower() == 'health':
                if await client.health_check():
                    console.print("[green]✓ API is healthy[/green]")
                else:
                    console.print("[red]✗ API is not responding[/red]")
                console.print()
                continue
            
            elif user_input.lower() == 'clear':
                client.session_id = None
                console.print("[yellow]Session cleared[/yellow]")
                console.print()
                continue
            
            # Send chat message - try non-streaming first to avoid ReadError
            console.print()
            console.print("[bold cyan]🤖 Assistant:[/bold cyan] ", end="")
            
            response_text = ""
            streaming_failed = False
            
            # Try non-streaming first (more reliable)
            try:
                fallback_response = await client.chat(user_input)
                fallback_text = fallback_response.get("message", "")
                
                if fallback_text:
                    console.print(fallback_text)
                    response_text = fallback_text
                    console.print(f"\n[dim][Response: {len(response_text)} chars][/dim]")
                else:
                    streaming_failed = True
                    
            except Exception as non_stream_error:
                console.print(f"[dim][Non-streaming failed: {non_stream_error}][dim]")
                streaming_failed = True
            
            # If non-streaming failed, try streaming as fallback
            if streaming_failed and not response_text:
                buffer = ""
                try:
                    async for chunk in client.chat_stream(user_input):
                        # Check if this is a repetition detection stop message
                        if "[Response stopped: Repetition detected]" in chunk:
                            console.print("[dim][Repetition detected, using fallback...][/dim]")
                            break
                        
                        # Buffer the chunk to handle partial words and newlines
                        buffer += chunk
                        
                        # Only display when we have complete sentences or reasonable chunks
                        if buffer.endswith(('. ', '! ', '? ', '\n')) or len(buffer) > 50:
                            # Clean up the buffer for display
                            display_text = buffer.replace('\n\n', '\n').replace('\n', ' ')
                            console.print(display_text, end="")
                            response_text += display_text
                            buffer = ""
                        
                except Exception as stream_error:
                    # Display any remaining buffer content
                    if buffer:
                        display_text = buffer.replace('\n\n', '\n').replace('\n', ' ')
                        console.print(display_text, end="")
                        response_text += display_text
                    buffer = ""
                    
                    console.print(f"\n[red]Streaming also failed: {stream_error}[/red]")
                
                # Display any remaining buffer content
                if buffer:
                    display_text = buffer.replace('\n\n', '\n').replace('\n', ' ')
                    console.print(display_text, end="")
                    response_text += display_text
            
            console.print()
            console.print()
            console.print("[dim]" + "─" * 60 + "[/dim]")
            console.print()
            
        except KeyboardInterrupt:
            console.print()
            console.print("[yellow]Use 'exit' to quit[/yellow]")
            console.print()
        
        except Exception as e:
            console.print()
            console.print(f"[red]Error: {str(e)}[/red]")
            console.print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print()
        console.print("[yellow]Goodbye![/yellow]")
