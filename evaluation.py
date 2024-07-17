import os
from openai import OpenAI
from rich.console import Console
from chunking import chunk_on_delimiter, tokenize
from utils import display_response_info, count_tokens
from models import MODELS, DEFAULT_MODEL

console = Console()

def get_openai_evaluation(commit_message, commit_diff, evaluation_prompt, model=DEFAULT_MODEL):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    evaluation_system_text = "Evaluating the commit message and diff to provide a summary."
    evaluation_text = f"{evaluation_prompt}\n\nCommit message: {commit_message}\n\nCommit diff:\n{commit_diff}"
    full_response = ""
    continuation_prompt = "CONTINUE"
    total_usage = 0

    # Chunk the evaluation text if it exceeds the model's max tokens
    max_tokens = MODELS[model]["max_tokens"]
    evaluation_chunks = chunk_on_delimiter(evaluation_text, max_tokens, "\n\n")

    # Define the message list with the initial system message
    message_list = [
        {"role": "system", "content": f"{evaluation_system_text}"},
    ]

    for chunk in evaluation_chunks:
        message_list.append({"role": "user", "content": f"{chunk}"})
        response = client.chat.completions.create(
            model=model,
            messages=message_list,
            max_tokens=max_tokens
        )
        part_response = response.choices[0].message.content.strip()
        
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
    display_response_info(evaluation_system_text, evaluation_prompt, full_response, count_tokens(evaluation_text, model), model)

    # Return the full response
    return full_response.strip()

def get_openai_summary(evaluations, summary_prompt, model=DEFAULT_MODEL):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    summary_system_text = "Generating a summary of all evaluations with a prompt message."
    summary_text = "\n\n".join([f"Commit {eval.get('hash')}:\n{eval.get('evaluation', 'No evaluation found')}" for eval in evaluations])
    full_response = ""
    continuation_prompt = "CONTINUE"

    # Chunk the summary text if it exceeds the model's max tokens
    max_tokens = MODELS[model]["max_tokens"]
    summary_chunks = chunk_on_delimiter(summary_text, max_tokens, "\n\n")

    message_list = [
        {"role": "system", "content": f"{summary_system_text}"},
    ]

    for chunk in summary_chunks:
        message_list.append({"role": "user", "content": f"{chunk}"})
        response = client.chat.completions.create(
            model=model,
            messages=message_list,
            max_tokens=max_tokens
        )
        part_response = response.choices[0].message.content.strip()
        
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
    display_response_info(summary_system_text, summary_prompt, full_response, count_tokens(summary_text, model), model)

    # Return the full response
    return full_response.strip()
