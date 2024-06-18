import argparse
import os
import git
from rich.console import Console
from git_operations import (
    evaluate_all_commits, evaluate_last_commit, evaluate_last_n_commits,
    evaluate_commit_range, evaluate_specific_commit, generate_summary
)
from models import DEFAULT_MODEL

console = Console()

def main():
    parser = argparse.ArgumentParser(description='Evaluate git commits using OpenAI.')
    parser.add_argument('--evaluate', required=True, help='Evaluate all commits, a specific commit by its hash, a range of commits (start_hash:end_hash), or the last commit(s).')
    parser.add_argument('--message', required=True, help='Prompt message for the evaluation.')
    parser.add_argument('--target-dir', required=True, help='Target directory containing the git repository.')
    parser.add_argument('--branch', required=False, help='Branch to evaluate commits from.')
    parser.add_argument('--author', required=False, help='Filter commits by author.')
    parser.add_argument('--summary', help='Generate a summary of all evaluations with a prompt message.')
    parser.add_argument('--model', default=DEFAULT_MODEL, help='Specify the model to use for evaluation (default: gpt-4o-2024-05-13)')

    args = parser.parse_args()

    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        console.print("[bold red]Error:[/bold red] OPENAI_API_KEY environment variable not set.")
        return

    # Get the git repository from the target directory
    try:
        repo = git.Repo(args.target_dir, search_parent_directories=False)
    except git.exc.InvalidGitRepositoryError:
        console.print(f"[bold red]Error:[/bold red] The directory {args.target_dir} is not a valid git repository.")
        return
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] An error occurred while accessing the repository: {e}")
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

    try:
        # Evaluate commits based on the provided arguments
        if args.evaluate == 'all':
            evaluate_all_commits(repo, args.message, args.target_dir, branch, args.author, args.model)
        elif args.evaluate.startswith('last:'):
            n = int(args.evaluate.split(':')[1])
            evaluate_last_n_commits(repo, args.message, args.target_dir, branch, args.author, n, args.model)
        elif args.evaluate == 'last':
            evaluate_last_commit(repo, args.message, args.target_dir, branch, args.author, args.model)
        elif ':' in args.evaluate:
            start_commit, end_commit = args.evaluate.split(':')
            evaluate_commit_range(repo, args.message, args.target_dir, branch, start_commit, end_commit, args.author, args.model)
        else:
            evaluate_specific_commit(repo, args.message, args.target_dir, branch, args.evaluate, args.author, args.model)
        
        # Generate a summary if the option is provided
        if args.summary:
            generate_summary(args.target_dir, args.summary, branch, args.evaluate, args.model)
        
    except ValueError as ve:
        console.print(Panel(f"[bold red]ValueError:[/bold red] {ve}", title="Error", subtitle="Please check your input"))
    except git.exc.GitCommandError as gce:
        console.print(Panel(f"[bold red]GitCommandError:[/bold red] {gce}", title="Error", subtitle="Git command issue"))
    except Exception as e:
        console.print(Panel(f"[bold red]Unexpected Error:[/bold red] {e}", title="Error", subtitle="An unexpected error occurred"))

if __name__ == '__main__':
    main()
