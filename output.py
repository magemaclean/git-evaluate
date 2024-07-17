# output.py

import os
import json
from rich.console import Console
from datetime import datetime 

console = Console()

def save_evaluation_json(eval_data, eval_file, output_include_diff=False):
    with open(eval_file, 'w') as f:
        json.dump(eval_data, f, indent=4)
    
    console.print(f"\n[bold green]Evaluation saved to:[/bold green] {eval_file}")

def save_evaluation_text(eval_data, eval_file, output_include_diff=False):
    with open(eval_file, 'w') as f:
        f.write(f"Commit Hash: {eval_data['hash']}\n")
        f.write(f"Author: {eval_data['author']}\n")
        f.write(f"Email: {eval_data['email']}\n")
        f.write(f"Date: {eval_data['date']}\n")
        f.write(f"Message: {eval_data['message']}\n")
        
        if output_include_diff:
          f.write("\nCommit Diff:\n")
          f.write(eval_data['diff'])
        
        f.write("\n\nEvaluation:\n")
        f.write(eval_data['evaluation'])
    
    console.print(f"\n[bold green]Evaluation saved to:[/bold green] {eval_file}")

def save_evaluation(eval_data, target_dir, output_format='json', output_include_diff=False):
    eval_dir = os.path.join(target_dir, '.git-evaluate')
    if not os.path.exists(eval_dir):
        os.makedirs(eval_dir)
    
    eval_file = os.path.join(eval_dir, f"{eval_data['hash']}.{output_format}")
    
    if output_format == 'json':
        save_evaluation_json(eval_data, eval_file, output_include_diff)
    elif output_format == 'text':
        save_evaluation_text(eval_data, eval_file, output_include_diff)
    else:
        raise ValueError(f"Unsupported output format: {output_format}")
    
    return eval_file

def save_summary(summary_data, target_dir, branch, output_format='json', output_include_diff=False):
    eval_dir = os.path.join(target_dir, '.git-evaluate')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_file_name = f"summary_{branch}_{timestamp}.{output_format}"
    summary_file = os.path.join(eval_dir, summary_file_name)
    
    if output_format == 'json':
        with open(summary_file, 'w') as f:
            json.dump(summary_data, f, indent=4)
    elif output_format == 'text':
        with open(summary_file, 'w') as f:
            for eval_data in summary_data['evaluations']:
                f.write(f"Commit Hash: {eval_data['hash']}\n")
                f.write(f"Author: {eval_data['author']}\n")
                f.write(f"Email: {eval_data['email']}\n")
                f.write(f"Date: {eval_data['date']}\n")
                f.write(f"Message: {eval_data['message']}\n")
                
                if output_include_diff:
                  f.write("\nCommit Diff:\n")
                  f.write(eval_data['diff'])
                  
                f.write("\n\nEvaluation:\n")
                f.write(eval_data['evaluation'])
                f.write("\n\n" + "-"*80 + "\n\n")
            f.write("\nSummary:\n")
            f.write(summary_data['summary'])
    
    console.print(f"\n[bold green]Summary saved to:[/bold green] {summary_file}")

    return summary_file
