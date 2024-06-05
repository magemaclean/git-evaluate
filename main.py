import argparse
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
import git
from utils import get_commit_diff, save_evaluation

def main():
    parser = argparse.ArgumentParser(description='Evaluate git commits using OpenAI.')
    parser.add_argument('--evaluate', required=True, help='Evaluate all commits or a specific commit by its hash.')
    parser.add_argument('--message', required=True, help='Prompt message for the evaluation.')
    parser.add_argument('--target-dir', required=True, help='Target directory containing the git repository.')

    args = parser.parse_args()

    # Load OpenAI API key
    if not client.api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set.")

    # Get the git repository from the target directory
    repo = git.Repo(args.target_dir, search_parent_directories=True)

    if args.evaluate == 'all':
        evaluate_all_commits(repo, args.message, args.target_dir)
    else:
        evaluate_specific_commit(repo, args.message, args.target_dir, args.evaluate)

def evaluate_specific_commit(repo, message, target_dir, commit_id):
    commit = repo.commit(commit_id)
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
    response = client.chat.completions.create(model="gpt-4-turbo-2024-04-09",
    messages=[
        {"role": "system", "content": "You are a helpful assistant that evaluates git commit diffs."},
        {"role": "user", "content": f"{message}\n\nCommit message: {commit_message}\n\nCommit diff:\n{commit_diff}"}
    ],
    max_tokens=500)
    return response.choices[0].message.content.strip()

if __name__ == '__main__':
    main()
