# Follows the pipeline backwards to gain betetr contextual understanding of the issue.

# Args: new version, old version, path to new version, warning message

from typing import Optional, List
import json
from anthropic import Anthropic

from ..utils.pipeline import RAGCapableAgent, PipelineResult, WarningMessage, AgentContext
from ...database.models import File


class ContextAwareness(RAGCapableAgent):
    """Agent that analyzes broader codebase context to understand the change."""
    
    def __init__(self, api_key: str):
        super().__init__("ContextAwareness", "context_awareness")
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"
    
    def analyze(self, context: AgentContext) -> tuple[PipelineResult, Optional[WarningMessage]]:
        """
        Analyze broader codebase context to understand why the change was made.
        Can cancel pipeline if change is justified by context.
        """
        self.logger.info("Starting context awareness analysis")
        
        if not context.current_warning:
            self.logger.warning("No warning message to enhance with context")
            return PipelineResult.CONTINUE, context.current_warning
        
        try:
            # Query related files from the project
            related_files = self.query_project_files(context.project_id, context.file_path)
            
            # Analyze context and determine if change is justified
            context_analysis = self._analyze_broader_context(context, related_files)
            
            if context_analysis.get('cancel_pipeline', False):
                self.logger.info("Change justified by broader context, cancelling pipeline")
                return PipelineResult.CANCEL, None
            
            # Enhance warning with context information
            enhanced_warning = self._enhance_warning_with_context(
                context.current_warning, 
                context_analysis,
                len(related_files)
            )
            
            return PipelineResult.CONTINUE, enhanced_warning
            
        except Exception as e:
            self.logger.error(f"Context awareness analysis failed: {str(e)}")
            # On error, continue with original warning
            return PipelineResult.CONTINUE, context.current_warning
    
    def _analyze_broader_context(self, context: AgentContext, related_files: List[File]) -> dict:
        """Use LLM to analyze the broader codebase context."""
        try:
            system_prompt = self._build_system_prompt()
            
            # Prepare related files context
            files_context = self._format_related_files(related_files)
            
            messages = [
                {
                    "role": "user",
                    "content": f"""File Being Changed: {context.file_path}

Old Version:
```
{context.old_version}
```

New Version:
```
{context.new_version}
```

Current Warning:
{context.current_warning.title}: {context.current_warning.description}

Related Files in Project:
{files_context}

Please analyze the broader context to understand if this change is justified. Consider:
1. Is this part of a larger refactoring effort?
2. Are there related changes in other files that explain this?
3. Could this be experimental or work-in-progress code?
4. Does the broader architecture explain why this change was made?

Respond with JSON:
{{
    "cancel_pipeline": true/false,
    "context_insights": "What the broader context reveals",
    "justification": "Why the change might be justified (if applicable)",
    "enhanced_description": "Enhanced warning description with context",
    "architectural_notes": "Relevant architectural observations"
}}"""
                }
            ]
            
            response = self.client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=messages,
                max_tokens=1000
            )
            
            return self._parse_context_analysis(response.content[0].text)
            
        except Exception as e:
            self.logger.error(f"LLM call failed in context analysis: {e}")
            return {"cancel_pipeline": False, "context_insights": "Context analysis failed"}
    
    def _format_related_files(self, files: List[File], max_files: int = 20) -> str:
        """Format related files for LLM context (limit for token efficiency)."""
        if not files:
            return "No related files found in project."
        
        # Sort by relevance (recently modified first, then by name)
        sorted_files = sorted(files, key=lambda f: (f.last_edit or f.created_at), reverse=True)
        
        formatted = []
        for i, file in enumerate(sorted_files[:max_files], 1):
            # Include a snippet of file content if available
            content_preview = ""
            if file.content:
                content_preview = file.content[:300] + "..." if len(file.content) > 300 else file.content
            
            formatted.append(f"""
File #{i}: {file.path}
- Last modified: {file.last_edit or file.created_at}
- Is directory: {file.is_dir}
- Content preview: {content_preview}
""")
        
        if len(files) > max_files:
            formatted.append(f"\n... and {len(files) - max_files} more files")
        
        return "\n".join(formatted)
    
    def _parse_context_analysis(self, response: str) -> dict:
        """Parse LLM response to extract context analysis."""
        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                response_data = json.loads(json_match.group())
            else:
                response_data = json.loads(response)
            
            self.logger.info(f"Context analysis: {response_data.get('context_insights', '')}")
            return response_data
            
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.warning(f"Failed to parse context analysis: {e}")
            return {
                "cancel_pipeline": False,
                "context_insights": response[:500] if response else "Analysis failed",
                "enhanced_description": ""
            }
    
    def _enhance_warning_with_context(self, warning: WarningMessage, analysis: dict, file_count: int) -> WarningMessage:
        """Enhance the warning message with context insights."""
        # Create a copy of the warning to avoid mutating the original
        enhanced_warning = WarningMessage(
            title=warning.title,
            severity=warning.severity,
            description=analysis.get('enhanced_description', warning.description) or warning.description,
            suggestions=warning.suggestions.copy(),
            affected_files=warning.affected_files.copy(),
            confidence=warning.confidence,
            metadata=warning.metadata.copy()
        )
        
        # Add context metadata
        enhanced_warning.metadata.update({
            "context_analyzed": True,
            "related_files_count": file_count,
            "context_insights": analysis.get('context_insights', ''),
            "architectural_notes": analysis.get('architectural_notes', ''),
            "agent": "ContextAwareness"
        })
        
        # Add context-based suggestions if available
        if analysis.get('justification'):
            enhanced_warning.suggestions.append(f"Context: {analysis['justification']}")
        
        return enhanced_warning
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt from the JSON configuration."""
        return self.system_prompt or "You are a senior software architect with deep understanding of codebase context."