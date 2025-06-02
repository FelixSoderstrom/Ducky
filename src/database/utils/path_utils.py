import os

def normalize_path(path: str) -> str:
    """Normalize a path for consistent database storage and comparison.
    
    Args:
        path: The path to normalize
        
    Returns:
        Normalized path with forward slashes and absolute path
    """
    # Convert to absolute path and normalize separators
    abs_path = os.path.abspath(path)
    # Convert all backslashes to forward slashes
    norm_path = abs_path.replace('\\', '/')
    return norm_path 