#!/usr/bin/env python3
# /// script
# dependencies = ["tiktoken"]
# ///

import os
import tiktoken
from pathlib import Path
from collections import defaultdict
import mimetypes

# Initialize the tokenizer (using cl100k_base which is used by GPT-4)
enc = tiktoken.get_encoding("cl100k_base")

def is_text_file(filepath):
    """Check if a file is likely a text file."""
    # First check common text file extensions
    text_extensions = {
        '.py', '.txt', '.md', '.json', '.yaml', '.yml', '.toml', '.ini',
        '.cfg', '.conf', '.js', '.ts', '.jsx', '.tsx', '.html', '.css',
        '.scss', '.sql', '.sh', '.bash', '.zsh', '.fish', '.ps1', '.bat',
        '.cmd', '.xml', '.csv', '.log', '.rst', '.tex', '.vim', '.env',
        '.gitignore', '.dockerignore', '.editorconfig', '.eslintrc',
        '.prettierrc', '.babelrc', '.webpack', '.config', '.lock'
    }
    
    if filepath.suffix.lower() in text_extensions:
        return True
    
    # Check files without extensions
    if not filepath.suffix:
        common_names = {
            'Makefile', 'Dockerfile', 'README', 'LICENSE', 'CHANGELOG',
            'AUTHORS', 'CONTRIBUTORS', 'NOTICE', 'VERSION', 'Procfile'
        }
        if filepath.name in common_names:
            return True
    
    # Use mimetypes as fallback
    mime_type, _ = mimetypes.guess_type(str(filepath))
    if mime_type:
        return mime_type.startswith('text/') or mime_type in [
            'application/json', 'application/xml', 'application/javascript'
        ]
    
    return False

def count_tokens_in_file(filepath):
    """Count tokens in a single file."""
    try:
        if not is_text_file(filepath):
            return 0
            
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            tokens = enc.encode(content)
            return len(tokens)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return 0

def analyze_directory(root_path):
    """Analyze token counts for all directories in the given path."""
    root_path = Path(root_path)
    directory_tokens = defaultdict(int)
    directory_file_counts = defaultdict(int)
    total_tokens = 0
    total_files = 0
    
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Skip hidden directories and common non-source directories
        dirnames[:] = [d for d in dirnames if not d.startswith('.') and d not in ['__pycache__', 'node_modules', 'venv', 'env']]
        
        current_dir = Path(dirpath)
        relative_dir = current_dir.relative_to(root_path)
        
        for filename in filenames:
            # Skip hidden files and compiled Python files
            if filename.startswith('.') or filename.endswith('.pyc'):
                continue
                
            filepath = current_dir / filename
            tokens = count_tokens_in_file(filepath)
            
            if tokens > 0:
                # Add tokens to current directory and all parent directories
                temp_dir = current_dir
                while temp_dir >= root_path:
                    relative_temp = temp_dir.relative_to(root_path)
                    directory_tokens[str(relative_temp)] += tokens
                    if temp_dir == current_dir:
                        directory_file_counts[str(relative_temp)] += 1
                    temp_dir = temp_dir.parent
                
                total_tokens += tokens
                total_files += 1
    
    return directory_tokens, directory_file_counts, total_tokens, total_files

def format_tokens(tokens):
    """Format token count with thousands separator."""
    return f"{tokens:,}"

def print_results(directory_tokens, directory_file_counts, total_tokens, total_files):
    """Print the results in a structured format."""
    print(f"\n{'='*80}")
    print(f"Token Count Analysis for rotkehlchen")
    print(f"{'='*80}\n")
    
    # Get only top-level directories (depth 0)
    top_level_dirs = {}
    for dir_path, tokens in directory_tokens.items():
        if dir_path == '.':
            continue
        parts = dir_path.split('/')
        if len(parts) == 1:  # Top-level directory
            top_level_dirs[dir_path] = tokens
    
    # Sort by token count
    sorted_top_level = sorted(top_level_dirs.items(), key=lambda x: x[1], reverse=True)
    
    # Print summary table
    print(f"{'Directory':<40} {'Files':>10} {'Tokens':>15} {'% of Total':>12}")
    print(f"{'-'*78}")
    
    for dir_path, tokens in sorted_top_level:
        file_count = sum(count for path, count in directory_file_counts.items() 
                        if path.startswith(dir_path))
        percentage = (tokens / total_tokens) * 100
        print(f"{dir_path + '/':<40} {file_count:>10} {format_tokens(tokens):>15} {percentage:>11.1f}%")
    
    print(f"{'-'*78}")
    print(f"{'TOTAL':<40} {total_files:>10} {format_tokens(total_tokens):>15} {'100.0%':>12}")

def main():
    # Get the rotkehlchen directory
    rotkehlchen_path = Path(__file__).parent / "rotkehlchen"
    
    if not rotkehlchen_path.exists():
        print(f"Error: Directory {rotkehlchen_path} does not exist")
        return
    
    print(f"Analyzing token counts in: {rotkehlchen_path}")
    print("This may take a moment...\n")
    
    # Analyze the directory
    directory_tokens, directory_file_counts, total_tokens, total_files = analyze_directory(rotkehlchen_path)
    
    # Print results
    print_results(directory_tokens, directory_file_counts, total_tokens, total_files)

if __name__ == "__main__":
    main()