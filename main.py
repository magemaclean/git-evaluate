import argparse
import os
from openai import OpenAI
import git
import json
from utils import get_commit_diff, save_evaluation

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def main():
    parser = argparse.ArgumentParser(description='Evaluate git commits using OpenAI.')
    parser.add_argument('--evaluate', required=True, help='Evaluate all commits, a specific commit by its hash, or a range of commits (start_hash:end_hash).')
    parser.add_argument('--message', required=True, help='Prompt message for the evaluation.')
    parser.add_argument('--target-dir', required=True, help='Target directory containing the git repository.')
    parser.add_argument('--summary', action='store_true', help='Generate a summary of all evaluations.')

    args = parser.parse_args()

    # Check if OpenAI API key is set
    if not client.api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set.")

    # Get the git repository from the target directory
    repo = git.Repo(args.target_dir, search_parent_directories=True)

    if args.evaluate == 'all':
        evaluate_all_commits(repo, args.message, args.target_dir)
    elif ':' in args.evaluate:
        start_commit, end_commit = args.evaluate.split(':')
        evaluate_commit_range(repo, args.message, args.target_dir, start_commit, end_commit)
    else:
        evaluate_specific_commit(repo, args.message, args.target_dir, args.evaluate)

    if args.summary:
        generate_summary(args.target_dir)

def evaluate_specific_commit(repo, message, target_dir, commit_id):
    commit = repo.commit(commit_id)
    commit_message = commit.message
    commit_diff = get_commit_diff(commit)

    evaluation = get_openai_evaluation(commit_message, commit_diff, message)
    save_evaluation(commit.hexsha, evaluation, target_dir)

def evaluate_commit_range(repo, message, target_dir, start_commit, end_commit):
    commits = list(repo.iter_commits(f'{start_commit}..{end_commit}'))
    for commit in commits:
        commit_message = commit.message
        commit_diff = get_commit_diff(commit)

        evaluation = get_openai_evaluation(commit_message, commit_diff, message)
        save_evaluation(commit.hexsha, evaluation, target_dir)

def evaluate_all_commits(repo, message, target_dir):
    for commit in repo.iter_commits():
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

def generate_summary(target_dir):
    eval_dir = os.path.join(target_dir, '.git-evaluate')
    summary_file = os.path.join(eval_dir, "summary.json")
    evaluations = []

    for filename in os.listdir(eval_dir):
        if filename.endswith(".txt"):
            commit_hash = filename.replace(".txt", "")
            with open(os.path.join(eval_dir, filename), 'r') as f:
                evaluation = f.read()
            evaluations.append({
                "commit_hash": commit_hash,
                "evaluation": evaluation
            })

    with open(summary_file, 'w') as f:
        json.dump(evaluations, f, indent=4)


if __name__ == '__main__':
    main()
