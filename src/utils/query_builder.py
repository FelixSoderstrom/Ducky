"""Query building utilities for Context7 documentation requests."""

from typing import List, Optional


class QueryBuilder:
    """Builds intelligent Context7 documentation queries."""
    
    # Topic keyword mappings for intelligent query construction
    TOPIC_KEYWORDS = {
        "best practices": ["best practices", "practices", "conventions"],
        "syntax": ["syntax", "syntax errors", "syntax error"],
        "validation": ["validation", "validate", "validator"],
        "deprecated": ["deprecated", "deprecation", "outdated"],
        "migration": ["migration", "migrate", "upgrade"],
        "security": ["security", "secure", "vulnerability"]
    }
    
    @staticmethod
    def build_documentation_query(language: str, libraries: List[str], issue_types: List[str]) -> str:
        """
        Build intelligent Context7 query from analysis components.
        
        Args:
            language: Programming language detected
            libraries: List of libraries/frameworks detected
            issue_types: List of issue categories from warning
            
        Returns:
            Natural language query for Context7 with 'use context7' trigger
        """
        query_parts = [
            f"I need current documentation for {language} code validation."
        ]
        
        if libraries:
            query_parts.append(f"Libraries used: {', '.join(libraries)}.")
        
        if issue_types:
            query_parts.append(f"Focus areas: {', '.join(issue_types)}.")
        
        # Add Context7 trigger
        query_parts.append("use context7")
        
        return " ".join(query_parts)
    
    @staticmethod
    def categorize_warning_issues(warning_text: str) -> List[str]:
        """
        Categorize types of issues in warning text for targeted documentation.
        
        Args:
            warning_text: Combined warning title and description
            
        Returns:
            List of issue categories for Context7 topic queries
        """
        issue_types = []
        warning_lower = warning_text.lower()
        
        # Map warning content to documentation topics
        issue_mappings = {
            'syntax errors': ['syntax', 'syntax error', 'invalid syntax'],
            'deprecated patterns': ['deprecated', 'deprecation', 'outdated'],
            'validation best practices': ['validation', 'validate', 'invalid'],
            'security best practices': ['security', 'vulnerability', 'insecure'],
            'performance optimization': ['performance', 'slow', 'inefficient'],
            'type annotations': ['type', 'typing', 'annotation']
        }
        
        for issue_type, keywords in issue_mappings.items():
            if any(keyword in warning_lower for keyword in keywords):
                issue_types.append(issue_type)
        
        # Default fallback
        if not issue_types:
            issue_types.append('best practices')
        
        return issue_types
    
    @staticmethod
    def extract_topic_from_query(query: str, library: str) -> Optional[str]:
        """
        Extract topic focus from query for specific library Context7 requests.
        
        Args:
            query: Natural language query text
            library: Specific library to extract topic for
            
        Returns:
            Topic string for Context7 get-library-docs or None
        """
        query_lower = query.lower()
        
        for topic, keywords in QueryBuilder.TOPIC_KEYWORDS.items():
            if any(keyword in query_lower for keyword in keywords):
                return topic
        
        return None 