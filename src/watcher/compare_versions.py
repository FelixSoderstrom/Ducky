from datetime import datetime
from typing import List, Dict, Any, TypedDict, Optional
from src.database.models.projects import Project
from src.database.models.files import File
from src.watcher.get_codebase import get_codebase_metadata, read_file_content
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


def get_changes(project_db: Project, root_path: str, last_scan_timestamp: Optional[datetime] = None) -> List[FileChange]:
    """Compare database version of project with local filesystem version using timestamp-based comparison.
    
    Args:
        project_db: Project instance from database containing current stored state
        root_path: Path to the local project directory to scan
        last_scan_timestamp: Timestamp of the last scan (None for initial scan)
        
    Returns:
        List of FileChange dictionaries containing files modified since last scan
    """
    # If no last scan timestamp, skip the scan to avoid processing thousands of files
    # The regular scanning loop will detect actual changes efficiently
    if last_scan_timestamp is None:
        print("Skipping initial scan - regular monitoring will detect changes")
        return []
    
    # Get local codebase metadata scan (more efficient - no file content reading)
    local_codebase = get_codebase_metadata(root_path, project_db.api_key)
    
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
        
        # Parse the file's last edit timestamp
        file_last_edit = datetime.fromisoformat(file_data['last_edit'])
        
        # Determine if file should be included based on timestamp comparison
        should_include = False
        
        if is_new:
            # New files are always included
            should_include = True
        elif not file_data['is_dir']:
            # For existing files, check if modified since last scan
            should_include = file_last_edit > last_scan_timestamp
        
        if should_include:
            # Only read file content when we know the file has changed
            old_version = '' if is_new else (db_file.content or '')
            
            # Read new content only for files (not directories) that have actually changed
            if file_data['is_dir']:
                new_version = ''
            else:
                new_version = read_file_content(file_data['full_path'])
            
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