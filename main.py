import argparse
import os
from openai import OpenAI
import git
import json
from utils import get_commit_diff, save_evaluation, generate_summary

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def main():
    parser = argparse.ArgumentParser(description='Evaluate git commits using OpenAI.')
    parser.add_argument('--evaluate', required=True, help='Evaluate all commits, a specific commit by its hash, a range of commits (start_hash:end_hash), or the last commit.')
    parser.add_argument('--message', required=True, help='Prompt message for the evaluation.')
    parser.add_argument('--target-dir', required=True, help='Target directory containing the git repository.')
    parser.add_argument('--branch', required=False, help='Branch to evaluate commits from.')
    parser.add_argument('--summary', action='store_true', help='Generate a summary of all evaluations.')

    args = parser.parse_args()

    # Check if OpenAI API key is set
    if not client.api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set.")

    # Get the git repository from the target directory
    try:
        repo = git.Repo(args.target_dir, search_parent_directories=False)
    except git.exc.InvalidGitRepositoryError:
        raise ValueError(f"The directory {args.target_dir} is not a valid git repository.")
    except Exception as e:
        raise ValueError(f"An error occurred while accessing the repository: {e}")

    print(f"Using repository: {repo.working_dir}")
    branch = args.branch
    if not branch:
        try:
            branch = repo.active_branch.name
        except TypeError:
            branches = [head.name for head in repo.heads]
            branch = branches[0] if branches else None
            if branch is None:
                raise ValueError("No branches found in the repository.")

    print(f"Using branch: {branch}")

    if args.evaluate == 'all':
        evaluate_all_commits(repo, args.message, args.target_dir, branch)
    elif args.evaluate == 'last':
        evaluate_last_commit(repo, args.message, args.target_dir, branch)
    elif ':' in args.evaluate:
        start_commit, end_commit = args.evaluate.split(':')
        evaluate_commit_range(repo, args.message, args.target_dir, branch, start_commit, end_commit)
    else:
        evaluate_specific_commit(repo, args.message, args.target_dir, branch, args.evaluate)

    if args.summary:
        generate_summary(args.target_dir)

def evaluate_specific_commit(repo, message, target_dir, branch, commit_id):
    # Log all available commit hashes in the specified branch
    available_commits = [commit.hexsha for commit in repo.iter_commits(branch)]

    if commit_id not in available_commits:
        raise ValueError(f"The commit hash {commit_id} could not be found in the repository.")
    
    try:
        commit = repo.commit(commit_id)
    except git.exc.BadName:
        raise ValueError(f"The commit hash {commit_id} could not be found in the repository.")
    except Exception as e:
        raise ValueError(f"An error occurred while retrieving the commit {commit_id}: {e}")
    
    commit_message = commit.message
    commit_diff = get_commit_diff(commit)

    evaluation = get_openai_evaluation(commit_message, commit_diff, message)
    save_evaluation(commit.hexsha, evaluation, target_dir)

def evaluate_last_commit(repo, message, target_dir, branch):
    # Get the last commit on the specified branch
    try:
        commit = next(repo.iter_commits(branch, max_count=1))
    except StopIteration:
        raise ValueError(f"No commits found in the branch {branch}.")
    
    commit_message = commit.message
    commit_diff = get_commit_diff(commit)

    evaluation = get_openai_evaluation(commit_message, commit_diff, message)
    save_evaluation(commit.hexsha, evaluation, target_dir)

def evaluate_commit_range(repo, message, target_dir, branch, start_commit, end_commit):
    try:
        commits = list(repo.iter_commits(f'{start_commit}..{end_commit}'))
    except git.exc.GitCommandError as e:
        raise ValueError(f"An error occurred while retrieving the commit range {start_commit}..{end_commit}: {e}")

    for commit in commits:
        commit_message = commit.message
        commit_diff = get_commit_diff(commit)

        evaluation = get_openai_evaluation(commit_message, commit_diff, message)
        save_evaluation(commit.hexsha, evaluation, target_dir)

def evaluate_all_commits(repo, message, target_dir, branch):
    for commit in repo.iter_commits(branch):
        commit_message = commit.message
        commit_diff = get_commit_diff(commit)

        evaluation = get_openai_evaluation(commit_message, commit_diff, message)
        save_evaluation(commit.hexsha, evaluation, target_dir)

def get_openai_evaluation(commit_message, commit_diff, message):
    response = client.chat.completions.create(
        model="gpt-4o-2024-05-13",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that evaluates git commit diffs."},
            {"role": "user", "content": f"{message}\n\nCommit message: {commit_message}\n\nCommit diff:\n{commit_diff}"}
        ],
        max_tokens=500
    )
    print(response.choices[0].message.content.strip())
    return response.choices[0].message.content.strip()

if __name__ == '__main__':
    main()
