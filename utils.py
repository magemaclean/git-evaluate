from rich.console import Console
from rich.table import Table
from models import MODELS, DEFAULT_MODEL
import tiktoken

console = Console()

def count_tokens(text, model=DEFAULT_MODEL):
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text)
    return len(tokens)

def display_commit_info(commit):
    console.print("\n")  # Add spacing
    table = Table(title="Commit Information")
    table.add_column("Field", style="bold")
    table.add_column("Value")

    table.add_row("Hash", commit.hexsha)
    table.add_row("Author", commit.author.name)
    table.add_row("Email", commit.author.email)
    table.add_row("Date", str(commit.committed_datetime))
    table.add_row("Message", commit.message.strip())

    console.print(table)

def display_response_info(system_text, user_prompt, response, total_tokens, model):
    console.print("\n")  # Add spacing

    table = Table(title="Response Information")
    table.add_column("Field", style="bold")
    table.add_column("Value")

    table.add_row("Model", MODELS[model]["name"])
    table.add_row("System Text", system_text)
    table.add_row("User Prompt", user_prompt)
    table.add_row("Total Tokens", f"{total_tokens}")
    table.add_row("Response Length", f"{len(response)}")
    table.add_row("", "")
    table.add_row("Response", response, style="green")

    console.print(table)
