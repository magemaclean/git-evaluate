# git-evaluate

`git-evaluate` is a Python script to evaluate git commits using OpenAI's API.

## Features

- Evaluate all commits in a git repository.
- Evaluate a specific commit by its hash.
- Evaluate a range of commits by specifying start and end commit hashes.
- Evaluate the last commit on a specified branch.
- Generate a summary report of all evaluations.
- Save evaluations in a `.git-evaluate` folder within the target directory.

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/yourusername/git-evaluate.git
    cd git-evaluate
    ```

2. Create a virtual environment and install dependencies:

    On Unix or MacOS:
    ```sh
    python3 -m venv venv
    source venv/bin/activate
    ```

    On Windows:
    ```sh
    python -m venv venv
    venv\Scripts\activate
    ```

3. Install required packages:
    ```sh
    pip install -r requirements.txt
    ```

4. Set the `OPENAI_API_KEY` environment variable:
    ```sh
    export OPENAI_API_KEY='your-openai-api-key'  # Unix or MacOS
    set OPENAI_API_KEY='your-openai-api-key'  # Windows
    $env:OPENAI_API_KEY="your_api_key_here" # Windows PowerShell
    ```

## Usage

Navigate to any project directory containing a git repository and run:

```sh
python path/to/git-evaluate/main.py --evaluate <all|last|commit_id|start_commit:end_commit> --message "Analyze the following git diff and provide a summary of the changes, highlighting improvements, issues, and potential impacts on the codebase." --target-dir path/to/your/git/repository
```

- `<all|last|commit_id|start_commit:end_commit>`: Specify the commits to evaluate.
- `--message`: Provide a prompt for the evaluation.
- `--target-dir`: Specify the path to the git repository.

For example, to evaluate all commits in the current directory's git repository:

```sh
python path/to/git-evaluate/main.py --evaluate all --message "Analyze the following git diff and provide a summary of the changes, highlighting improvements, issues, and potential impacts on the codebase." --target-dir .
```

To evaluate the last commit on the `main` branch in a specific directory:

```sh
python path/to/git-evaluate/main.py --evaluate last --message "Analyze the following git diff and provide a summary of the changes, highlighting improvements, issues, and potential impacts on the codebase." --target-dir path/to/your/git/repository
```

To evaluate a specific commit by its hash:

```sh
python path/to/git-evaluate/main.py --evaluate commit_id --message "Analyze the following git diff and provide a summary of the changes, highlighting improvements, issues, and potential impacts on the codebase." --target-dir path/to/your/git/repository
```

To evaluate a range of commits by specifying start and end commit hashes:

```sh
python path/to/git-evaluate/main.py --evaluate start_commit:end_commit --message "Analyze the following git diff and provide a summary of the changes, highlighting improvements, issues, and potential impacts on the codebase." --target-dir path/to/your/git/repository
```

## Output

The script will generate a summary report of the evaluations and save them in a `.git-evaluate` folder within the target directory.
