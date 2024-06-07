import os
import json

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

def save_evaluation(commit_hash, evaluation, target_dir):
    eval_dir = os.path.join(target_dir, '.git-evaluate')
    if not os.path.exists(eval_dir):
        os.makedirs(eval_dir)
    eval_file = os.path.join(eval_dir, f"{commit_hash}.txt")
    with open(eval_file, 'w') as f:
        f.write(evaluation)

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
