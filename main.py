import argparse
import os
import json
from datetime import datetime
from openai import OpenAI
import git
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
console = Console()

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

def display_evaluation(evaluation):
    console.print("\n")  # Add spacing
    console.print("[bold green]Evaluation Result:[/bold green]")
    console.print(evaluation)

def display_summary(summary):
    console.print("\n")  # Add spacing
    console.print("[bold green]Summary Result:[/bold green]")
    console.print(summary)

def save_json_evaluation(commit, evaluation, target_dir):
    eval_data = {
        "hash": commit.hexsha,
        "author": commit.author.name,
        "email": commit.author.email,
        "date": str(commit.committed_datetime),
        "message": commit.message.strip(),
        "diff": get_commit_diff(commit),
        "evaluation": evaluation
    }
    eval_dir = os.path.join(target_dir, '.git-evaluate')
    if not os.path.exists(eval_dir):
        os.makedirs(eval_dir)
    eval_file = os.path.join(eval_dir, f"{commit.hexsha}.json")
    with open(eval_file, 'w') as f:
        json.dump(eval_data, f, indent=4)
    
    console.print(f"\n[bold green]Evaluation saved to:[/bold green] {eval_file}")

def get_commit_diff(commit):
    parent = commit.parents[0] if commit.parents else None
    diff = commit.diff(parent, create_patch=True) if parent else commit.diff(None, create_patch=True)
    diffs = []
    for d in diff:
        try:
            diffs.append(d.diff.decode('utf-8'))
        except UnicodeDecodeError:
            diffs.append(d.diff.decode('latin-1'))
    return '\n'.join(diffs)

def evaluate_specific_commit(repo, message, target_dir, branch, commit_id, author):
    available_commits = [commit.hexsha for commit in repo.iter_commits(branch, author=author)]

    if commit_id not in available_commits:
        raise ValueError(f"The commit hash {commit_id} could not be found in the repository.")
    
    try:
        commit = repo.commit(commit_id)
    except git.exc.BadName:
        raise ValueError(f"The commit hash {commit_id} could not be found in the repository.")
    except Exception as e:
        raise ValueError(f"An error occurred while retrieving the commit {commit_id}: {e}")
    
    display_commit_info(commit)
    commit_diff = get_commit_diff(commit)

    evaluation = get_openai_evaluation(commit.message, commit_diff, message)
    display_evaluation(evaluation)
    save_json_evaluation(commit, evaluation, target_dir)

def evaluate_last_commit(repo, message, target_dir, branch, author):
    try:
        commit = next(repo.iter_commits(branch, max_count=1, author=author))
    except StopIteration:
        raise ValueError(f"No commits found in the branch {branch} by the specified author.")
    
    display_commit_info(commit)
    commit_diff = get_commit_diff(commit)

    evaluation = get_openai_evaluation(commit.message, commit_diff, message)
    display_evaluation(evaluation)
    save_json_evaluation(commit, evaluation, target_dir)

def evaluate_last_n_commits(repo, message, target_dir, branch, author, n):
    try:
        commits = list(repo.iter_commits(branch, max_count=n, author=author))
        if not commits:
            raise ValueError(f"No commits found in the branch {branch} by the specified author.")
    except git.exc.GitCommandError as e:
        raise ValueError(f"An error occurred while retrieving the last {n} commits: {e}")

    for commit in commits:
        display_commit_info(commit)
        commit_diff = get_commit_diff(commit)

        evaluation = get_openai_evaluation(commit.message, commit_diff, message)
        display_evaluation(evaluation)
        save_json_evaluation(commit, evaluation, target_dir)

def evaluate_commit_range(repo, message, target_dir, branch, start_commit, end_commit, author):
    try:
        commits = list(repo.iter_commits(f'{start_commit}..{end_commit}', author=author))
    except git.exc.GitCommandError as e:
        raise ValueError(f"An error occurred while retrieving the commit range {start_commit}..{end_commit}: {e}")

    for commit in commits:
        display_commit_info(commit)
        commit_diff = get_commit_diff(commit)

        evaluation = get_openai_evaluation(commit.message, commit_diff, message)
        display_evaluation(evaluation)
        save_json_evaluation(commit, evaluation, target_dir)

def evaluate_all_commits(repo, message, target_dir, branch, author):
    for commit in repo.iter_commits(branch, author=author):
        display_commit_info(commit)
        commit_diff = get_commit_diff(commit)

        evaluation = get_openai_evaluation(commit.message, commit_diff, message)
        display_evaluation(evaluation)
        save_json_evaluation(commit, evaluation, target_dir)

def get_openai_evaluation(commit_message, commit_diff, message):
    response = client.chat.completions.create(
        model="gpt-4o-2024-05-13",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that evaluates git commit diffs."},
            {"role": "user", "content": f"{message}\n\nCommit message: {commit_message}\n\nCommit diff:\n{commit_diff}"}
        ],
        max_tokens=500
    )
    return response.choices[0].message.content.strip()

def generate_summary(target_dir, summary_prompt, branch, evaluate):
    eval_dir = os.path.join(target_dir, '.git-evaluate')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_file_name = f"summary_{branch}_{evaluate}_{timestamp}.json"
    summary_file = os.path.join(eval_dir, summary_file_name)
    evaluations = []

    for filename in os.listdir(eval_dir):
        if filename.endswith(".json"):
            with open(os.path.join(eval_dir, filename), 'r') as f:
                evaluation = json.load(f)
            evaluations.append(evaluation)

    summary = get_openai_summary(evaluations, summary_prompt)

    display_summary(summary)

    summary_data = {
        "evaluations": evaluations,
        "summary": summary
    }

    with open(summary_file, 'w') as f:
        json.dump(summary_data, f, indent=4)

    console.print(f"\n[bold green]Summary saved to:[/bold green] {summary_file}")

    return summary_file_name

def get_openai_summary(evaluations, summary_prompt):
    evaluations_text = "\n\n".join([f"Commit {eval.get('hash')}:\n{eval.get('evaluation', 'No evaluation found')}" for eval in evaluations])
    response = client.chat.completions.create(
        model="gpt-4o-2024-05-13",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes git commit evaluations."},
            {"role": "user", "content": f"{summary_prompt}\n\n{evaluations_text}"}
        ],
        max_tokens=500
    )
    return response.choices[0].message.content.strip()

def main():
    parser = argparse.ArgumentParser(description='Evaluate git commits using OpenAI.')
    parser.add_argument('--evaluate', required=True, help='Evaluate all commits, a specific commit by its hash, a range of commits (start_hash:end_hash), or the last commit(s).')
    parser.add_argument('--message', required=True, help='Prompt message for the evaluation.')
    parser.add_argument('--target-dir', required=True, help='Target directory containing the git repository.')
    parser.add_argument('--branch', required=False, help='Branch to evaluate commits from.')
    parser.add_argument('--author', required=False, help='Filter commits by author.')
    parser.add_argument('--summary', help='Generate a summary of all evaluations with a prompt message.')

    args = parser.parse_args()

    # Check if OpenAI API key is set
    if not client.api_key:
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
        if args.evaluate == 'all':
            evaluate_all_commits(repo, args.message, args.target_dir, branch, args.author)
        elif args.evaluate.startswith('last:'):
            n = int(args.evaluate.split(':')[1])
            evaluate_last_n_commits(repo, args.message, args.target_dir, branch, args.author, n)
        elif args.evaluate == 'last':
            evaluate_last_commit(repo, args.message, args.target_dir, branch, args.author)
        elif ':' in args.evaluate:
            start_commit, end_commit = args.evaluate.split(':')
            evaluate_commit_range(repo, args.message, args.target_dir, branch, start_commit, end_commit, args.author)
        else:
            evaluate_specific_commit(repo, args.message, args.target_dir, branch, args.evaluate, args.author)
    except ValueError as ve:
        console.print(Panel(f"[bold red]ValueError:[/bold red] {ve}", title="Error", subtitle="Please check your input"))
    except git.exc.GitCommandError as gce:
        console.print(Panel(f"[bold red]GitCommandError:[/bold red] {gce}", title="Error", subtitle="Git command issue"))
    except Exception as e:
        console.print(Panel(f"[bold red]Unexpected Error:[/bold red] {e}", title="Error", subtitle="An unexpected error occurred"))

    if args.summary:
        try:
            summary_file_name = generate_summary(args.target_dir, args.summary, branch, args.evaluate)
            console.print(f"[bold green]Summary saved to:[/bold green] {summary_file_name}")
        except Exception as e:
            console.print(Panel(f"[bold red]Error generating summary:[/bold red] {e}", title="Error"))

if __name__ == '__main__':
    main()
