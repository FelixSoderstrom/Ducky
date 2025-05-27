from datetime import datetime
from typing import List, Dict, Any, TypedDict
from src.database.models.projects import Project
from src.database.models.files import File
from src.watcher.get_codebase import get_codebase
from src.database.utils.path_utils import normalize_path


class FileChange(TypedDict):
    filename: str
    path: str
    old_version: str
    new_version: str
    last_edit: str
    is_dir: bool
    is_new_file: bool
    project_id: int


def get_changes(project_db: Project, root_path: str) -> List[FileChange]:
    """Compare database version of project with local filesystem version.
    
    Args:
        project_db: Project instance from database containing current stored state
        root_path: Path to the local project directory to scan
        
    Returns:
        List of FileChange dictionaries containing differences between versions
    """
    # Get local codebase scan
    local_codebase = get_codebase(root_path, project_db.api_key)
    
    # Create lookup dict of database files by path
    db_files: Dict[str, File] = {
        file.path: file for file in project_db.files
    }
    
    changes: List[FileChange] = []
    
    # Compare each local file with database version
    for file_data in local_codebase['files']:
        normalized_path = normalize_path(file_data['full_path'])
        
        # Check if file exists in database
        db_file = db_files.get(normalized_path)
        is_new = db_file is None
        
        # Skip directory comparisons unless it's a new directory
        if file_data['is_dir'] and not is_new:
            continue
            
        # For files, compare content. For directories, only track new ones
        old_version = '' if is_new else (db_file.content or '')
        new_version = file_data['file_contents'] or ''  # Convert None to '' for comparison
        
        change: FileChange = {
            'filename': file_data['filename'],
            'path': normalized_path,
            'old_version': old_version,
            'new_version': new_version,
            'last_edit': file_data['last_edit'],
            'is_dir': file_data['is_dir'],
            'is_new_file': is_new,
            'project_id': project_db.id
        }
        
        # Only add to changes if:
        # 1. It's a new file/directory
        # 2. It's a file (not directory) and content has changed
        if is_new or (not file_data['is_dir'] and old_version != new_version):
            changes.append(change)
            
    # Check for files that exist in DB but not locally (deleted files)
    for db_path, db_file in db_files.items():
        if not any(normalize_path(f['full_path']) == db_path for f in local_codebase['files']):
            changes.append({
                'filename': db_file.name,
                'path': db_path,
                'old_version': db_file.content or '',
                'new_version': '',  # Empty content indicates deletion
                'last_edit': datetime.now().isoformat(),
                'is_dir': db_file.is_dir,
                'is_new_file': False,
                'project_id': project_db.id
            })
    
    return changes