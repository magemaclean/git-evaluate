# git_operations.py

import os
import json
import git
from datetime import datetime
from rich.console import Console
from rich.table import Table
from utils import display_commit_info
from evaluation import get_openai_evaluation, get_openai_summary
from output import save_evaluation, save_summary

console = Console()

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

def evaluate_specific_commit(repo, message, target_dir, branch, commit_id, author, model, output_format, output_dir, output_include_diff):
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
    commit_diff = get_commit_diff(commit) if output_include_diff else ""

    evaluation = get_openai_evaluation(commit.message, commit_diff, message, model)
    eval_data = {
        "hash": commit.hexsha,
        "author": commit.author.name,
        "email": commit.author.email,
        "date": str(commit.committed_datetime),
        "message": commit.message.strip(),
        "diff": commit_diff,
        "evaluation": evaluation
    }
    save_evaluation(eval_data, output_dir or target_dir, output_format)

    return [commit.hexsha]

def evaluate_last_commit(repo, message, target_dir, branch, author, model, output_format, output_dir, output_include_diff):
    try:
        commit = next(repo.iter_commits(branch, max_count=1, author=author))
    except StopIteration:
        raise ValueError(f"No commits found in the branch {branch} by the specified author.")
    
    display_commit_info(commit)
    commit_diff = get_commit_diff(commit) if output_include_diff else ""

    evaluation = get_openai_evaluation(commit.message, commit_diff, message, model)
    eval_data = {
        "hash": commit.hexsha,
        "author": commit.author.name,
        "email": commit.author.email,
        "date": str(commit.committed_datetime),
        "message": commit.message.strip(),
        "diff": commit_diff,
        "evaluation": evaluation
    }
    save_evaluation(eval_data, output_dir or target_dir, output_format)

    return [commit.hexsha]

def evaluate_last_n_commits(repo, message, target_dir, branch, author, n, model, output_format, output_dir, output_include_diff):
    try:
        commits = list(repo.iter_commits(branch, max_count=n, author=author))
        if not commits:
            raise ValueError(f"No commits found in the branch {branch} by the specified author.")
    except git.exc.GitCommandError as e:
        raise ValueError(f"An error occurred while retrieving the last {n} commits: {e}")

    evaluated_commits = []

    for commit in commits:
        display_commit_info(commit)
        commit_diff = get_commit_diff(commit) if output_include_diff else ""

        evaluation = get_openai_evaluation(commit.message, commit_diff, message, model)
        eval_data = {
            "hash": commit.hexsha,
            "author": commit.author.name,
            "email": commit.author.email,
            "date": str(commit.committed_datetime),
            "message": commit.message.strip(),
            "diff": commit_diff,
            "evaluation": evaluation
        }
        save_evaluation(eval_data, output_dir or target_dir, output_format)

        evaluated_commits.append(commit.hexsha)

    return evaluated_commits

def evaluate_commit_range(repo, message, target_dir, branch, start_commit, end_commit, author, model, output_format, output_dir, output_include_diff):
    try:
        commits = list(repo.iter_commits(f'{start_commit}..{end_commit}', author=author))
    except git.exc.GitCommandError as e:
        raise ValueError(f"An error occurred while retrieving the commit range {start_commit}..{end_commit}: {e}")

    evaluated_commits = []

    for commit in commits:
        display_commit_info(commit)
        commit_diff = get_commit_diff(commit) if output_include_diff else ""

        evaluation = get_openai_evaluation(commit.message, commit_diff, message, model)
        eval_data = {
            "hash": commit.hexsha,
            "author": commit.author.name,
            "email": commit.author.email,
            "date": str(commit.committed_datetime),
            "message": commit.message.strip(),
            "diff": commit_diff,
            "evaluation": evaluation
        }
        save_evaluation(eval_data, output_dir or target_dir, output_format)

        evaluated_commits.append(commit.hexsha)

    return evaluated_commits

def evaluate_all_commits(repo, message, target_dir, branch, author, model, output_format, output_dir, output_include_diff):
    evaluated_commits = []

    for commit in repo.iter_commits(branch, author=author):
        display_commit_info(commit)
        commit_diff = get_commit_diff(commit) if output_include_diff else ""

        evaluation = get_openai_evaluation(commit.message, commit_diff, message, model)
        eval_data = {
            "hash": commit.hexsha,
            "author": commit.author.name,
            "email": commit.author.email,
            "date": str(commit.committed_datetime),
            "message": commit.message.strip(),
            "diff": commit_diff,
            "evaluation": evaluation
        }
        save_evaluation(eval_data, output_dir or target_dir, output_format)

        evaluated_commits.append(commit.hexsha)

    return evaluated_commits

def generate_summary(target_dir, summary_prompt, branch, evaluated_commits, model, output_format, output_dir, output_include_diff):
    eval_dir = os.path.join(output_dir or target_dir, '.git-evaluate')
    evaluations = []

    for commit_hash in evaluated_commits:
        eval_file = os.path.join(eval_dir, f"{commit_hash}.json")
        if os.path.exists(eval_file):
            with open(eval_file, 'r') as f:
                evaluation = json.load(f)
            evaluations.append(evaluation)

    summary = get_openai_summary(evaluations, summary_prompt, model)
    summary_data = {
        "evaluations": evaluations,
        "summary": summary
    }

    save_summary(summary_data, output_dir or target_dir, branch, output_format, output_include_diff)


def list_branches(repo):
    branches = [head.name for head in repo.heads]
    console.print(f"\n[bold blue]Branches:[/bold blue] {', '.join(branches)}")

def list_authors(repo):
    authors = {}
    for commit in repo.iter_commits():
        author = commit.author
        if author.email not in authors:
            authors[author.email] = {
                "name": author.name,
                "email": author.email,
                "username": author.name  # Assuming username is the same as name; change as needed
            }
    table = Table(title="Authors")
    table.add_column("Name", style="bold")
    table.add_column("Email")
    table.add_column("Username")

    for author in authors.values():
        table.add_row(author["name"], author["email"], author["username"])

    console.print(table)

def list_commits(repo, num_commits):
    commits = list(repo.iter_commits(max_count=num_commits))
    table = Table(title="Recent Commits")
    table.add_column("Hash", style="bold")
    table.add_column("Author")
    table.add_column("Date")
    table.add_column("Message")

    for commit in commits:
        table.add_row(commit.hexsha, commit.author.name, str(commit.committed_datetime), commit.message.strip())
    
    console.print(table)

def show_commit(repo, commit_hash):
    try:
        commit = repo.commit(commit_hash)
    except git.exc.BadName:
        console.print(f"[bold red]Error:[/bold red] The commit hash {commit_hash} could not be found in the repository.")
        return
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] An error occurred while retrieving the commit {commit_hash}: {e}")
        return
    
    display_commit_info(commit)
    commit_diff = get_commit_diff(commit)
    
    console.print("\n[bold blue]Commit Diff:[/bold blue]")
    console.print(commit_diff)
