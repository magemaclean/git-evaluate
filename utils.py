import os
import git

def get_commit_diff(commit):
    parent = commit.parents[0] if commit.parents else None
    diff = commit.diff(parent, create_patch=True) if parent else commit.diff(None, create_patch=True)
    return '\n'.join([d.diff.decode('utf-8') for d in diff])

def save_evaluation(commit_hash, evaluation, target_dir):
    eval_dir = os.path.join(target_dir, '.git-evaluate')
    if not os.path.exists(eval_dir):
        os.makedirs(eval_dir)
    eval_file = os.path.join(eval_dir, f"{commit_hash}.txt")
    with open(eval_file, 'w') as f:
        f.write(evaluation)
