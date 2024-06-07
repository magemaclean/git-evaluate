
# Git Evaluate

Git Evaluate is a Python application designed to evaluate git commits using the OpenAI API. It can evaluate specific commits, a range of commits, or all commits in a repository, and save the evaluations as JSON files. Additionally, it can generate a summary of all evaluations.

## Installation

1. **Clone the repository**

   ```bash
   git clone <repository_url>
   cd <repository_directory>
   ```

2. **Create a virtual environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

   *** Note: For Windows, use `venv\Scripts\activate` instead of `source venv/bin/activate`. ***


3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up OpenAI API Key**

   Export your OpenAI API key as an environment variable:

   ```bash
   export OPENAI_API_KEY=your_openai_api_key
   ```

    *** Note: For Windows, use `set OPENAI_API_KEY=your_openai_api_key` instead of `export OPENAI_API_KEY=your_openai_api_key`. ***

## Usage

Run the `main.py` script with the appropriate arguments:

```bash
python main.py --evaluate <evaluation_type> --message <prompt_message> --target-dir <target_directory> [--branch <branch_name>] [--author <author_email>] [--summary <summary_prompt>]
```

### Arguments

- `--evaluate`: Specify the type of evaluation. Options are:
  - `all`: Evaluate all commits in the repository.
  - `last`: Evaluate the last commit.
  - `last:n`: Evaluate the last `n` commits.
  - `commit_hash`: Evaluate a specific commit by its hash.
  - `start_commit:end_commit`: Evaluate a range of commits from `start_commit` to `end_commit`.
- `--message`: The prompt message for the evaluation.
- `--target-dir`: The target directory containing the git repository.
- `--branch`: (Optional) The branch to evaluate commits from. Defaults to the current branch.
- `--author`: (Optional) Filter commits by author email.
- `--summary`: (Optional) Generate a summary of all evaluations with a prompt message.

### Examples

1. **Evaluate all commits**

   ```bash
   python main.py --evaluate all --message "Evaluate this commit" --target-dir /path/to/repo
   ```

2. **Evaluate the last commit**

   ```bash
   python main.py --evaluate last --message "Evaluate this commit" --target-dir /path/to/repo
   ```

3. **Evaluate the last 5 commits**

   ```bash
   python main.py --evaluate last:5 --message "Evaluate these commits" --target-dir /path/to/repo
   ```

4. **Evaluate a specific commit**

   ```bash
   python main.py --evaluate abc1234 --message "Evaluate this specific commit" --target-dir /path/to/repo
   ```

5. **Evaluate a range of commits**

   ```bash
   python main.py --evaluate abc1234:def5678 --message "Evaluate these commits" --target-dir /path/to/repo
   ```

6. **Generate a summary**

   ```bash
   python main.py --evaluate all --message "Evaluate this commit" --target-dir /path/to/repo --summary "Summarize the evaluations"
   ```

## Output

The evaluations are saved in the `.git-evaluate` directory within the target directory as JSON files. The summary, if generated, is also saved in this directory.

