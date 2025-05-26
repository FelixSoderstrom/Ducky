from typing import Dict, Any, List
import os
from datetime import datetime
from pathlib import Path
import fnmatch
from src.watcher.default_ignore_patterns import DEFAULT_IGNORE_PATTERNS


def read_gitignore(root_path: str) -> list[str]:
    """
    Read .gitignore file and return list of patterns to ignore.
    
    Args:
        root_path: Root directory path where .gitignore is located
        
    Returns:
        List of gitignore patterns
    """
    gitignore_path = os.path.join(root_path, '.gitignore')
    patterns = DEFAULT_IGNORE_PATTERNS.copy()
    
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    patterns.append(line)
    
    return patterns

def should_ignore(path: str, ignore_patterns: list[str]) -> bool:
    """
    Check if a path should be ignored based on ignore patterns.
    
    Args:
        path: Path to check
        ignore_patterns: List of patterns to ignore
        
    Returns:
        True if path should be ignored, False otherwise
    """
    path = path.replace('\\', '/')  # Normalize path separators
    for pattern in ignore_patterns:
        if fnmatch.fnmatch(path, pattern):
            return True
    return False

def get_codebase(root_path: str, api_key: str = None) -> Dict[str, Any]:
    """
    Recursively scan directory and return dict with file information.
    
    Args:
        root_path: Root directory path to scan
        api_key: Optional API key to include in the response
        
    Returns:
        Dict containing project and file information with structure:
        {
            project_name: str,
            api_key: str,
            files: [
                {
                    filename: str,
                    last_edit: timestamp,
                    file_contents: str,
                    full_path: str,
                    is_dir: bool
                },
                ...
            ]
        }
    """
    files = []
    ignore_patterns = read_gitignore(root_path)
    
    for root, dirs, filenames in os.walk(root_path):
        # Convert absolute path to relative path
        rel_root = os.path.relpath(root, root_path)
        if rel_root == '.':
            rel_root = ''
            
        # Check directories
        dirs[:] = [d for d in dirs if not should_ignore(os.path.join(rel_root, d).replace('\\', '/'), ignore_patterns)]
        
        # Process directories
        for dir_name in dirs:
            full_path = os.path.join(root, dir_name)
            rel_path = os.path.join(rel_root, dir_name).replace('\\', '/')
            
            files.append({
                'filename': dir_name,
                'last_edit': datetime.fromtimestamp(os.path.getmtime(full_path)).isoformat(),
                'file_contents': None,
                'full_path': full_path,
                'is_dir': True
            })
        
        # Process files
        for file_name in filenames:
            rel_path = os.path.join(rel_root, file_name).replace('\\', '/')
            if should_ignore(rel_path, ignore_patterns):
                continue
                
            full_path = os.path.join(root, file_name)
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except (UnicodeDecodeError, PermissionError):
                # Skip binary files or files we can't read
                continue
                
            files.append({
                'filename': file_name,
                'last_edit': datetime.fromtimestamp(os.path.getmtime(full_path)).isoformat(),
                'file_contents': content,
                'full_path': full_path,
                'is_dir': False
            })
    
    return {
        'project_name': os.path.basename(os.path.abspath(root_path)),
        'api_key': api_key,
        'files': files
    }