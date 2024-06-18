import argparse
import os
import git
from rich.console import Console
from rich.panel import Panel
from git_operations import (
    evaluate_all_commits, evaluate_last_commit, evaluate_last_n_commits,
    evaluate_commit_range, evaluate_specific_commit, generate_summary,
    list_branches, list_authors, list_commits, show_commit
)
from models import DEFAULT_MODEL, MODELS

console = Console()

def load_config(config_file):
    import json
    with open(config_file, 'r') as file:
        config = json.load(file)
    return config

def main():
    parser = argparse.ArgumentParser(description='Evaluate git commits using OpenAI.')
    parser.add_argument('--evaluate', help='Evaluate all commits, a specific commit by its hash, a range of commits (start_hash:end_hash), or the last commit(s).')
    parser.add_argument('--message', help='Prompt message for the evaluation.')
    parser.add_argument('--target-dir', help='Target directory containing the git repository.')
    parser.add_argument('--branch', help='Branch to evaluate commits from.')
    parser.add_argument('--author', help='Filter commits by author.')
    parser.add_argument('--summary', help='Generate a summary of all evaluations with a prompt message.')
    parser.add_argument('--model', help='Specify the model to use for evaluation (default: gpt-4o-2024-05-13)')
    parser.add_argument('--config-file', help='Path to a configuration file with OpenAI API key and other settings.')
    parser.add_argument('--max-tokens', type=int, help='Maximum number of tokens for the OpenAI API.')
    parser.add_argument('--include-diff', action='store_true', help='Include commit diff in the evaluation.')
    parser.add_argument('--output-format', choices=['json', 'text'], help='Format of the output evaluation file.')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging.')
    
    # New query arguments
    parser.add_argument('--list-branches', action='store_true', help='List all branches in the repository.')
    parser.add_argument('--list-authors', action='store_true', help='List all authors who have contributed to the repository.')
    parser.add_argument('--list-commits', type=int, nargs='?', const=10, help='List the most recent commits in the repository (default: 10).')
    parser.add_argument('--show-commit', help='Show details of a specific commit.')

    args = parser.parse_args()

    # Load config file if specified
    if args.config_file:
        config = load_config(args.config_file)
        os.environ['OPENAI_API_KEY'] = config.get('openai_api_key', os.getenv('OPENAI_API_KEY'))
        default_model = config.get('default_model', DEFAULT_MODEL)
        max_tokens = config.get('max_tokens', None)
        include_diff = config.get('include_diff', False)
        output_format = config.get('output_format', 'json')
        verbose = config.get('verbose', False)
        target_dir = config.get('target_dir', None)
        message = config.get('message', None)
        summary = config.get('summary', None)
        evaluate = config.get('evaluate', None)
    else:
        default_model = DEFAULT_MODEL
        target_dir = None
        message = None
        summary = None
        evaluate = None

    # Override config settings with command-line arguments if provided
    if args.model:
        default_model = args.model
    if args.target_dir:
        target_dir = args.target_dir
    if args.message:
        message = args.message
    if args.summary:
        summary = args.summary
    if args.evaluate:
        evaluate = args.evaluate

    # Validate required arguments for evaluation
    if not target_dir:
        console.print(f"[bold red]Error:[/bold red] 'target-dir' argument is required.")
        return

    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        console.print("[bold red]Error:[/bold red] OPENAI_API_KEY environment variable not set.")
        return

    # Get the git repository from the target directory
    try:
        repo = git.Repo(target_dir, search_parent_directories=False)
    except git.exc.InvalidGitRepositoryError:
        console.print(f"[bold red]Error:[/bold red] The directory {target_dir} is not a valid git repository.")
        return
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] An error occurred while accessing the repository: {e}")
        return

    # Handle repository queries
    if args.list_branches:
        list_branches(repo)
        return

    if args.list_authors:
        list_authors(repo)
        return

    if args.list_commits:
        list_commits(repo, args.list_commits)
        return

    if args.show_commit:
        show_commit(repo, args.show_commit)
        return

    # If evaluating, ensure message and evaluate are provided
    if not message or not evaluate:
        console.print(f"[bold red]Error:[/bold red] 'message' and 'evaluate' arguments are required for evaluation.")
        return

    console.print(f"[bold blue]Using repository:[/bold blue] {repo.working_dir}")
    branch = args.branch
    if not branch:
        try:
            branch = repo.active_branch.name
        except TypeError:
            branches = [head.name for head in repo.heads]
            branch = branches[0] if branches else None
            if branch is None:
                console.print("[bold red]Error:[/bold red] No branches found in the repository.")
                return

    console.print(f"[bold blue]Using branch:[/bold blue] {branch}")

    evaluated_commits = []

    try:
        # Evaluate commits based on the provided arguments
        if evaluate == 'all':
            evaluated_commits = evaluate_all_commits(repo, message, target_dir, branch, args.author, default_model)
        elif evaluate.startswith('last:'):
            n = int(evaluate.split(':')[1])
            evaluated_commits = evaluate_last_n_commits(repo, message, target_dir, branch, args.author, n, default_model)
        elif evaluate == 'last':
            evaluated_commits = evaluate_last_commit(repo, message, target_dir, branch, args.author, default_model)
        elif ':' in evaluate:
            start_commit, end_commit = evaluate.split(':')
            evaluated_commits = evaluate_commit_range(repo, message, target_dir, branch, start_commit, end_commit, args.author, default_model)
        else:
            evaluated_commits = evaluate_specific_commit(repo, message, target_dir, branch, evaluate, args.author, default_model)
        
        # Generate a summary if the option is provided
        if summary:
            generate_summary(target_dir, summary, branch, evaluated_commits, default_model)
        
    except ValueError as ve:
        console.print(Panel(f"[bold red]ValueError:[/bold red] {ve}", title="Error", subtitle="Please check your input"))
    except git.exc.GitCommandError as gce:
        console.print(Panel(f"[bold red]GitCommandError:[/bold red] {gce}", title="Error", subtitle="Git command issue"))
    except Exception as e:
        console.print(Panel(f"[bold red]Unexpected Error:[/bold red] {e}", title="Error", subtitle="An unexpected error occurred"))

if __name__ == '__main__':
    main()
