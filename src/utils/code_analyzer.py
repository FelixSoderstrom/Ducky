"""Code analysis utilities for detecting languages, libraries, and patterns."""

import re
from typing import List, Optional
from pathlib import Path


class CodeAnalyzer:
    """Analyzes code to detect programming language, libraries, and patterns."""
    
    # Common programming libraries and frameworks
    COMMON_LIBRARIES = [
        "python", "fastapi", "sqlalchemy", "django", "flask", "requests", "numpy", "pandas",
        "react", "nextjs", "vue", "angular", "typescript", "javascript", "node",
        "mongodb", "postgresql", "mysql", "redis"
    ]
    
    # Built-in modules to exclude
    BUILTIN_MODULES = ['os', 'sys', 'json', 'time', 'datetime', 're', 'math', 'random']
    
    @staticmethod
    def detect_language(file_path: str, code: str) -> str:
        """Detect programming language from file path and code content."""
        # File extension detection
        path_obj = Path(file_path)
        extension = path_obj.suffix.lower()
        
        extension_map = {
            '.py': "Python",
            '.js': "JavaScript", 
            '.jsx': "JavaScript",
            '.ts': "TypeScript",
            '.tsx': "TypeScript", 
            '.java': "Java",
            '.cpp': "C++",
            '.cc': "C++", 
            '.cxx': "C++",
            '.c': "C",
            '.rs': "Rust",
            '.go': "Go"
        }
        
        if extension in extension_map:
            return extension_map[extension]
        
        # Fallback to code content analysis
        if any(keyword in code for keyword in ['def ', 'import ', 'from ', '__init__']):
            return "Python"
        elif any(keyword in code for keyword in ['function ', 'const ', 'let ', 'var ']):
            return "JavaScript"
        
        return "Unknown"
    
    @staticmethod  
    def extract_libraries(code: str, language: str) -> List[str]:
        """Extract libraries and frameworks from code content."""
        libraries = []
        
        if language == "Python":
            libraries = CodeAnalyzer._extract_python_libraries(code)
        elif language in ["JavaScript", "TypeScript"]:
            libraries = CodeAnalyzer._extract_js_libraries(code)
        
        # Remove duplicates and built-ins, limit results
        libraries = list(set(lib for lib in libraries if lib not in CodeAnalyzer.BUILTIN_MODULES))
        return libraries[:5]  # Limit to top 5 to avoid overloading
    
    @staticmethod
    def _extract_python_libraries(code: str) -> List[str]:
        """Extract Python libraries from import statements and patterns."""
        libraries = []
        
        # Import statement patterns
        import_patterns = [
            r'import\s+(\w+)',
            r'from\s+(\w+)',
            r'import\s+(\w+)\.',
            r'from\s+(\w+)\.'
        ]
        
        for pattern in import_patterns:
            matches = re.findall(pattern, code)
            libraries.extend(matches)
        
        # Framework-specific detection
        framework_patterns = {
            'fastapi': ['fastapi', 'router', '@app'],
            'sqlalchemy': ['sqlalchemy', 'session', 'query'],
            'django': ['django', 'models.model'],
            'flask': ['flask', '@app.route']
        }
        
        code_lower = code.lower()
        for framework, keywords in framework_patterns.items():
            if any(keyword in code_lower for keyword in keywords):
                libraries.append(framework)
        
        return libraries
    
    @staticmethod
    def _extract_js_libraries(code: str) -> List[str]:
        """Extract JavaScript/TypeScript libraries from import/require statements."""
        libraries = []
        
        # Import/require patterns  
        import_patterns = [
            r'import.*from\s+[\'"](\w+)[\'"]',
            r'require\([\'"](\w+)[\'"]\)',
            r'import\s+(\w+)',
        ]
        
        for pattern in import_patterns:
            matches = re.findall(pattern, code)
            libraries.extend(matches)
        
        return libraries
    
    @staticmethod
    def extract_libraries_from_query(query: str) -> List[str]:
        """Extract potential library names from natural language query."""
        query_lower = query.lower()
        detected = []
        
        # Check against known libraries
        for lib in CodeAnalyzer.COMMON_LIBRARIES:
            if lib in query_lower:
                detected.append(lib)
        
        # Special case: detect Python from file extensions or keywords
        if "python" not in detected and (".py" in query or "python" in query_lower):
            detected.append("python")
        
        return detected 