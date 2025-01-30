import click
import sys
from .core.agent import Agent
from .core.logger import log

@click.command()
@click.option(
    "--model", default="openai", help="Model provider to use (openai, anthropic, etc.)"
)
@click.option("--tool-dir", help="Directory containing additional tools")
@click.option("--debug", is_flag=True, help="Enable debug mode to see inputs/outputs")
def plexy(model: str, tool_dir: str | None, debug: bool):
    """
    Plexy - A CLI-based AI assistant that streams output and can call tools.
    """
    if debug:
        log("[DEBUG] Debug mode enabled")

    log("Starting Plexy...")
    log("Hi, what would you like to search?")

    agent = Agent(model_provider=model, tool_dir=tool_dir, debug=debug)

    while True:
        try:
            user_input = input("> ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "q", "quit"):
                break

            # Stream the response
            sys.stdout.write("\nPlexy: ")
            sys.stdout.flush()

            for chunk in agent.stream_chat(user_input):
                # Each chunk is text, so just write it out
                sys.stdout.write(chunk)
                sys.stdout.flush()

            # Print newline after the response is done
            sys.stdout.write("\n\n")

        except KeyboardInterrupt:
            break
        except Exception as e:
            log(f"Error: {str(e)}", error=True)

    log("Goodbye!")

if __name__ == "__main__":
    plexy()

