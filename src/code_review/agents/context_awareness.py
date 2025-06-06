# Follows the pipeline backwards to gain betetr contextual understanding of the issue.

# Args: new version, old version, path to new version, warning message

from typing import Optional, List, Dict, Any
import json
import datetime
from anthropic import Anthropic

from .base.rag_agent import RAGCapableAgent
from ..models.pipeline_models import PipelineResult, WarningMessage, AgentContext
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
        Uses ADDITIVE approach - appends context insights to existing warning.
        """
        self.logger.info("Starting context awareness analysis")
        
        if not context.current_warning:
            self.logger.warning("No warning message to enhance with context")
            return PipelineResult.CONTINUE, context.current_warning
        
        try:
            # Intelligent file exploration - start with discovering relevant files
            relevant_files = self._discover_relevant_files(context)
            
            # Analyze context and determine if change is justified
            context_analysis = self._analyze_broader_context(context, relevant_files)
            
            if context_analysis.get('cancel_pipeline', False):
                self.logger.info("Change justified by broader context, cancelling pipeline")
                self.cr_logger.info(f"[{self.name}] Change justified by context - cancelling pipeline")
                return PipelineResult.CANCEL, None
            
            # Enhance warning with context information using ADDITIVE approach
            enhanced_warning = self._enhance_warning_with_context(
                context.current_warning, 
                context_analysis,
                len(relevant_files)
            )
            
            self.cr_logger.info(f"[{self.name}] Added context insights from {len(relevant_files)} related files")
            return PipelineResult.CONTINUE, enhanced_warning
            
        except Exception as e:
            self.logger.error(f"Context awareness analysis failed: {str(e)}")
            self.cr_logger.error(f"[{self.name}] Context analysis failed: {str(e)}")
            # On error, continue with original warning
            return PipelineResult.CONTINUE, context.current_warning
    
    def _discover_relevant_files(self, context: AgentContext, max_files: int = 5) -> List[File]:
        """
        Intelligently discover and retrieve relevant files with full content.
        
        Args:
            context: Current analysis context
            max_files: Maximum number of files to explore
            
        Returns:
            List of File objects with full content
        """
        explored_files = []
        current_file_dir = "/".join(context.file_path.split("/")[:-1])  # Get directory
        
        # Strategy 1: Look for files in same directory
        same_dir_files = self.search_files_by_pattern(context.project_id, current_file_dir)
        same_dir_files = [f for f in same_dir_files if f.path != context.file_path and not f.is_dir]
        
        # Strategy 2: Look for files with similar names (e.g., calculator.py, calculator_utils.py)
        base_name = context.file_path.split("/")[-1].split(".")[0]  # Extract base filename
        similar_name_files = self.search_files_by_pattern(context.project_id, base_name)
        similar_name_files = [f for f in similar_name_files if f.path != context.file_path and not f.is_dir]
        
        # Combine and prioritize (same dir first, then similar names)
        candidate_files = []
        candidate_files.extend(same_dir_files[:3])  # Up to 3 from same directory
        candidate_files.extend([f for f in similar_name_files if f not in candidate_files][:2])  # Up to 2 more with similar names
        
        # Get full content for the most promising candidates
        for file_metadata in candidate_files[:max_files]:
            full_file = self.query_single_file(context.project_id, file_metadata.path)
            if full_file and full_file.content:  # Only include files with content
                explored_files.append(full_file)
                self.logger.info(f"RAG: Retrieved full content for {file_metadata.path} ({len(full_file.content)} chars)")
        
        self.logger.info(f"RAG: Explored {len(explored_files)} files with full content")
        return explored_files
    
    def _analyze_broader_context(self, context: AgentContext, related_files: List[File]) -> dict:
        """Use LLM to analyze the broader codebase context."""
        try:
            system_prompt = self._build_system_prompt()
            
            # Prepare related files context
            files_context = self._format_related_files(related_files)
            
            # Get current warning description as string
            current_description = " | ".join(context.current_warning.description)
            
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
{context.current_warning.title}: {current_description}

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
    "additional_context": "Additional warning description with context",
    "architectural_notes": "Relevant architectural observations",
    "new_suggestions": ["context-based suggestion1", "suggestion2"],
    "additional_files": ["file1.py", "file2.py"]
}}"""
                }
            ]
            
            response = self.client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=messages,
                max_tokens=1000
            )
            
            self._log_llm_output(self.name, response.content[0].text)
            return self._parse_context_analysis(response.content[0].text)
            
        except Exception as e:
            self.logger.error(f"LLM call failed in context analysis: {e}")
            return {"cancel_pipeline": False, "context_insights": "Context analysis failed"}
    
    def _format_related_files(self, files: List[File]) -> str:
        """Format related files for LLM context with full content."""
        if not files:
            return "No related files found in project."
        
        formatted = []
        for i, file in enumerate(files, 1):
            # Include FULL file content since we've already limited the number of files
            content_section = ""
            if file.content:
                content_section = f"""
Full Content:
```
{file.content}
```"""
            else:
                content_section = "\nContent: (No content available)"
            
            formatted.append(f"""
== File #{i}: {file.path} ==
- Last modified: {file.last_edit or file.created_at}
- Size: {len(file.content) if file.content else 0} characters
{content_section}
""")
        
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
                "additional_context": ""
            }
    
    def _enhance_warning_with_context(self, warning: WarningMessage, analysis: dict, file_count: int) -> WarningMessage:
        """Enhance the warning message with context insights using ADDITIVE approach."""
        # ADDITIVE APPROACH: Append to existing lists, don't replace
        
        # Add context-enhanced description
        if analysis.get('additional_context'):
            warning.description.append(f"Context: {analysis['additional_context']}")
        
        if analysis.get('context_insights'):
            warning.description.append(f"Broader insights: {analysis['context_insights']}")
        
        # Add context-based suggestions
        new_suggestions = analysis.get('new_suggestions', [])
        if new_suggestions:
            warning.suggestions.extend(new_suggestions)
        
        # Add architectural justification as suggestion if available
        if analysis.get('justification'):
            warning.suggestions.append(f"Architectural context: {analysis['justification']}")
        
        # Add additional affected files if discovered
        additional_files = analysis.get('additional_files', [])
        if additional_files:
            for file_path in additional_files:
                if file_path not in warning.affected_files:
                    warning.affected_files.append(file_path)
        
        # Add agent analysis using helper method
        warning.add_agent_analysis(self.name, {
            "timestamp": datetime.datetime.now().isoformat(),
            "reasoning": analysis.get('context_insights', ''),
            "confidence_impact": 0.1,  # Context slightly increases confidence
            "related_files_analyzed": file_count,
            "architectural_notes": analysis.get('architectural_notes', ''),
            "justification": analysis.get('justification', '')
        })
        
        # Slightly increase confidence since we have more context
        if file_count > 0:
            warning.confidence = min(1.0, warning.confidence + 0.1)
        
        self.cr_logger.info(f"[{self.name}] Enhanced warning with context from {file_count} files")
        return warning
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt from the JSON configuration."""
        return self.system_prompt or "You are a senior software architect with deep understanding of codebase context."