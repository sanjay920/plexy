import click
import sys
from rich.console import Console
from core.agent import Agent
from core.logger import log


console = Console()


@click.command()
@click.option("--model", default="openai", help="Model provider (default: openai)")
@click.option("--tool-dir", default="", help="Path to a folder with extra tools")
@click.option("--debug", is_flag=True, help="Enable debug prints")
@click.option(
    "--max-iters", default=2, help="Max decision iterations before forced answer"
)
def plexy(model: str, tool_dir: str, debug: bool, max_iters: int):
    """
    Plexy - A CLI-based AI assistant that uses an iterative pipeline approach.
    """
    if debug:
        log("[DEBUG] Debug mode enabled")

    log("Starting Plexy...")
    log("Type your question or type 'exit' to quit.")

    agent = Agent(
        model_provider=model, tool_dir=tool_dir, debug=debug, max_iters=max_iters
    )

    while True:
        try:
            user_input = input("\n> ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "q", "quit"):
                break

            console.print("[bold cyan]\nPlexy says:[/bold cyan]")
            for chunk in agent.run_pipeline(user_input):
                sys.stdout.write(chunk)
                sys.stdout.flush()

        except KeyboardInterrupt:
            break
        except Exception as e:
            log(f"Error: {str(e)}", error=True)

    log("Goodbye!")


if __name__ == "__main__":
    plexy()
