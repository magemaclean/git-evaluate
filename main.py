import argparse
import os
import json
from datetime import datetime
from openai import OpenAI
import tiktoken
import git
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
console = Console()

# Define the models and their max tokens
DEFAULT_MODEL = "gpt-4o-2024-05-13"
MODELS = {
    "gpt-3.5": { "name": "GPT-3.5", "max_tokens": 500 },
    "gpt-3.5-turbo": { "name": "GPT-3.5 Turbo", "max_tokens": 8192 },
    "gpt-4": { "name": "GPT-4", "max_tokens": 4096 },
    "gpt-4o": { "name": "GPT-4o", "max_tokens": 4096 },
    "gpt-4o-2024-05-13": { "name": "GPT-4o (2024-05-13)", "max_tokens": 4096 }
}
  
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

def display_response_info(system_text, user_prompt, response, total_tokens, model):
    console.print("\n")  # Add spacing

    table = Table(title="Response Information")
    table.add_column("Field", style="bold")
    table.add_column("Value")

    table.add_row("Model", MODELS[model]["name"])
    table.add_row("System Text", system_text)
    table.add_row("User Prompt", user_prompt)
    table.add_row("Total Tokens", f"{total_tokens}")
    table.add_row("Response Length", f"{len(response)}")
    table.add_row("", "")
    table.add_row("Response", response, style="green")

    console.print(table)


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

def evaluate_last_commit(repo, message, target_dir, branch, author, model):
    try:
        commit = next(repo.iter_commits(branch, max_count=1, author=author))
    except StopIteration:
        raise ValueError(f"No commits found in the branch {branch} by the specified author.")
    
    display_commit_info(commit)
    commit_diff = get_commit_diff(commit)

    evaluation = get_openai_evaluation(commit.message, commit_diff, message, model)
    save_json_evaluation(commit, evaluation, target_dir)

def evaluate_last_n_commits(repo, message, target_dir, branch, author, n, model):
    try:
        commits = list(repo.iter_commits(branch, max_count=n, author=author))
        if not commits:
            raise ValueError(f"No commits found in the branch {branch} by the specified author.")
    except git.exc.GitCommandError as e:
        raise ValueError(f"An error occurred while retrieving the last {n} commits: {e}")

    for commit in commits:
        display_commit_info(commit)
        commit_diff = get_commit_diff(commit)

        evaluation = get_openai_evaluation(commit.message, commit_diff, message, model)
        save_json_evaluation(commit, evaluation, target_dir)

def evaluate_commit_range(repo, message, target_dir, branch, start_commit, end_commit, author, model):
    try:
        commits = list(repo.iter_commits(f'{start_commit}..{end_commit}', author=author))
    except git.exc.GitCommandError as e:
        raise ValueError(f"An error occurred while retrieving the commit range {start_commit}..{end_commit}: {e}")

    for commit in commits:
        display_commit_info(commit)
        commit_diff = get_commit_diff(commit)

        evaluation = get_openai_evaluation(commit.message, commit_diff, message, model)
        save_json_evaluation(commit, evaluation, target_dir)

def evaluate_all_commits(repo, message, target_dir, branch, author, model):
    for commit in repo.iter_commits(branch, author=author):
        display_commit_info(commit)
        commit_diff = get_commit_diff(commit)

        evaluation = get_openai_evaluation(commit.message, commit_diff, message, model)
        save_json_evaluation(commit, evaluation, target_dir)

def count_tokens(text, model=DEFAULT_MODEL):
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text)
    return len(tokens)

def get_openai_evaluation(commit_message, commit_diff, evaluation_prompt, model=DEFAULT_MODEL):
    evaluation_system_text = "Evaluating the commit message and diff to provide a summary."
    evaluation_text = f"{evaluation_prompt}\n\nCommit message: {commit_message}\n\nCommit diff:\n{commit_diff}"
    full_response = ""
    continuation_prompt = "CONTINUE"
    total_usage = 0

    # Count tokens
    total_tokens = count_tokens(evaluation_text, model)

    # Check if the evaluation text length exceeds the model's max tokens
    if total_tokens > MODELS[model]["max_tokens"]:
        console.print(f"[bold red]Error:[/bold red] The evaluation text length exceeds the model's max tokens ({MODELS[model]['max_tokens']}).")
        return
    
    # Define the message list with the initial system message
    message_list = [
        {"role": "system", "content": f"{evaluation_system_text}"},
        {"role": "user", "content": f"{evaluation_text}"}
    ]


    # Loop to get the response in parts
    while True:
        response = client.chat.completions.create(
            model=model,
            messages=message_list,
            max_tokens=MODELS[model]["max_tokens"]
        )
        part_response = response.choices[0].message.content.strip()
        # total_usage += response.usage['total_tokens']
        
        # Append the new part of the response, making sure we don't duplicate content
        if part_response not in full_response:
            full_response += part_response
            message_list.append({"role": "assistant", "content": part_response})
        
        # Check if response is complete or needs continuation
        if response.choices[0].finish_reason == "stop":
            break
        else:
            # Continue the prompt responses
            message_list.append({"role": "user", "content": continuation_prompt})

    # Display the response information
    display_response_info(evaluation_system_text, evaluation_prompt, full_response, total_tokens, model)

    # Return the full response
    return full_response.strip()

def generate_summary(target_dir, summary_prompt, branch, evaluate, model):
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

    summary = get_openai_summary(evaluations, summary_prompt, model)

    summary_data = {
        "evaluations": evaluations,
        "summary": summary
    }

    with open(summary_file, 'w') as f:
        json.dump(summary_data, f, indent=4)

    console.print(f"\n[bold green]Summary saved to:[/bold green] {summary_file}")

def get_openai_summary(evaluations, summary_prompt, model=DEFAULT_MODEL):
    summary_system_text = "Generating a summary of all evaluations with a prompt message."
    summary_text = "\n\n".join([f"Commit {eval.get('hash')}:\n{eval.get('evaluation', 'No evaluation found')}" for eval in evaluations])
    full_response = ""
    continuation_prompt = "CONTINUE"

    # Count tokens
    total_tokens = count_tokens(summary_text, model)

    # Check if the summary text length exceeds the model's max tokens
    if total_tokens > MODELS[model]["max_tokens"]:
        console.print(f"[bold red]Error:[/bold red] The summary text length exceeds the model's max tokens ({MODELS[model]['max_tokens']}).")
        return

    messageList = [
        {"role": "system", "content": f"{summary_system_text}"},
        {"role": "user", "content": f"{summary_prompt}\n\n{summary_text}"}
    ]

    # Loop to get the response in parts
    while True:
        response = client.chat.completions.create(
            model=model,
            messages=messageList,
            max_tokens=MODELS[model]["max_tokens"]
        )
        part_response = response.choices[0].message.content.strip()
        
        # Append the new part of the response, making sure we don't duplicate content
        if part_response not in full_response:
            full_response += part_response
            messageList.append({"role": "assistant", "content": part_response})
        
        # Check if response is complete or needs continuation
        if response.choices[0].finish_reason == "stop":
            break
        else:
            # Continue the prompt responses
            messageList.append({"role": "user", "content": continuation_prompt})
    
    # Display the response information
    display_response_info(summary_system_text, summary_prompt, full_response, total_tokens, model)

    # Return the full response
    return full_response.strip()

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
