import os
import json
import git
from rich.console import Console
from datetime import datetime
from utils import display_commit_info, display_response_info
from evaluation import get_openai_evaluation, get_openai_summary

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

def evaluate_specific_commit(repo, message, target_dir, branch, commit_id, author, model):
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

    evaluation = get_openai_evaluation(commit.message, commit_diff, message, model)
    save_json_evaluation(commit, evaluation, target_dir)

    return [commit.hexsha]

def evaluate_last_commit(repo, message, target_dir, branch, author, model):
    try:
        commit = next(repo.iter_commits(branch, max_count=1, author=author))
    except StopIteration:
        raise ValueError(f"No commits found in the branch {branch} by the specified author.")
    
    display_commit_info(commit)
    commit_diff = get_commit_diff(commit)

    evaluation = get_openai_evaluation(commit.message, commit_diff, message, model)
    save_json_evaluation(commit, evaluation, target_dir)

    return [commit.hexsha]

def evaluate_last_n_commits(repo, message, target_dir, branch, author, n, model):
    try:
        commits = list(repo.iter_commits(branch, max_count=n, author=author))
        if not commits:
            raise ValueError(f"No commits found in the branch {branch} by the specified author.")
    except git.exc.GitCommandError as e:
        raise ValueError(f"An error occurred while retrieving the last {n} commits: {e}")

    evaluated_commits = []

    for commit in commits:
        display_commit_info(commit)
        commit_diff = get_commit_diff(commit)

        evaluation = get_openai_evaluation(commit.message, commit_diff, message, model)
        save_json_evaluation(commit, evaluation, target_dir)

        evaluated_commits.append(commit.hexsha)

    return evaluated_commits

def evaluate_commit_range(repo, message, target_dir, branch, start_commit, end_commit, author, model):
    try:
        commits = list(repo.iter_commits(f'{start_commit}..{end_commit}', author=author))
    except git.exc.GitCommandError as e:
        raise ValueError(f"An error occurred while retrieving the commit range {start_commit}..{end_commit}: {e}")

    evaluated_commits = []

    for commit in commits:
        display_commit_info(commit)
        commit_diff = get_commit_diff(commit)

        evaluation = get_openai_evaluation(commit.message, commit_diff, message, model)
        save_json_evaluation(commit, evaluation, target_dir)

        evaluated_commits.append(commit.hexsha)

    return evaluated_commits

def evaluate_all_commits(repo, message, target_dir, branch, author, model):
    evaluated_commits = []

    for commit in repo.iter_commits(branch, author=author):
        display_commit_info(commit)
        commit_diff = get_commit_diff(commit)

        evaluation = get_openai_evaluation(commit.message, commit_diff, message, model)
        save_json_evaluation(commit, evaluation, target_dir)

        evaluated_commits.append(commit.hexsha)

    return evaluated_commits

def generate_summary(target_dir, summary_prompt, branch, evaluated_commits, model):
    eval_dir = os.path.join(target_dir, '.git-evaluate')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_file_name = f"summary_{branch}_{timestamp}.json"
    summary_file = os.path.join(eval_dir, summary_file_name)
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

    with open(summary_file, 'w') as f:
        json.dump(summary_data, f, indent=4)

    console.print(f"\n[bold green]Summary saved to:[/bold green] {summary_file}")
