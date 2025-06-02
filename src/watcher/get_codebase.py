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

def get_codebase_metadata(root_path: str, anthropic_key: str = None) -> Dict[str, Any]:
    """Get project metadata with filenames, timestamps, and basic info.
    
    More efficient version of get_codebase() that doesn't read file contents.
    Used for comparisons and change detection.
    
    Args:
        root_path: Root directory path to scan
        anthropic_key: Optional Anthropic API key to include in the response
        
    Returns:
        Dictionary containing project metadata and file information
    """
    return _get_codebase_base(
        root_path=root_path,
        anthropic_key=anthropic_key,
        include_content=False
    )

def get_codebase(root_path: str, anthropic_key: str = None) -> Dict[str, Any]:
    """Get complete project data including file contents.
    
    Full version that reads all file contents. Used for initial project setup.
    
    Args:
        root_path: Root directory path to scan
        anthropic_key: Optional Anthropic API key to include in the response
        
    Returns:
        Dictionary containing complete project and file information
    """
    return _get_codebase_base(
        root_path=root_path,
        anthropic_key=anthropic_key,
        include_content=True
    )

def read_file_content(file_path: str) -> str:
    """
    Read the content of a specific file.
    
    Args:
        file_path: Path to the file to read
        
    Returns:
        File content as string, or empty string if file can't be read
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except (UnicodeDecodeError, PermissionError, OSError):
        return ''

def _get_codebase_base(root_path: str, anthropic_key: str, include_content: bool) -> Dict[str, Any]:
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
                last_edit = datetime.fromtimestamp(os.path.getmtime(full_path)).isoformat()
                
                if include_content:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                else:
                    content = None
                    
                files.append({
                    'filename': file_name,
                    'last_edit': last_edit,
                    'file_contents': content,
                    'full_path': full_path,
                    'is_dir': False
                })
                
            except (UnicodeDecodeError, PermissionError, OSError):
                # Skip binary files or files we can't read
                continue
    
    return {
        'project_name': os.path.basename(os.path.abspath(root_path)),
        'anthropic_key': anthropic_key,
        'files': files
    }