# Follows the pipeline backwards to gain better contextual understanding of the issue.

# Args: new version, old version, path to new version, warning message

from typing import Optional, List, Dict, Any
import json
import datetime
from anthropic import Anthropic

from .base.rag_agent import RAGCapableAgent
from ..models.pipeline_models import PipelineResult, WarningMessage, AgentContext
from ...database.models import File


class RAGState:
    """Manages state across iterative RAG conversations."""
    
    def __init__(self):
        self.retrieved_files: List[File] = []
        self.conversation_history: List[Dict[str, str]] = []
        self.complete: bool = False
        self.iteration_count: int = 0
        self.max_iterations: int = 3
        self.max_files_total: int = 10
        self.max_files_per_request: int = 3
    
    def add_files(self, files: List[File]) -> None:
        """Add retrieved files to state."""
        self.retrieved_files.extend(files)
    
    def can_continue(self) -> bool:
        """Check if more iterations are allowed."""
        return (self.iteration_count < self.max_iterations and 
                len(self.retrieved_files) < self.max_files_total and 
                not self.complete)
    
    def get_file_paths(self) -> List[str]:
        """Get list of currently retrieved file paths."""
        return [f.path for f in self.retrieved_files]


class ContextAwareness(RAGCapableAgent):
    """Agent that analyzes broader codebase context to understand the change."""
    
    def __init__(self, api_key: str):
        super().__init__("ContextAwareness", "context_awareness")
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"
    
    def analyze(self, context: AgentContext) -> tuple[PipelineResult, Optional[WarningMessage]]:
        """
        Iterative analysis with intelligent RAG.
        Uses multi-phase approach: assess → request files → analyze → repeat if needed → complete
        """
        self.logger.info("Starting intelligent context awareness analysis")
        
        if not context.current_warning:
            self.logger.warning("No warning message to enhance with context")
            return PipelineResult.CONTINUE, context.current_warning
        
        try:
            # Phase 1: Assess if RAG is needed
            if not self._needs_rag_analysis(context):
                self.logger.info("No broader context needed for this warning")
                return PipelineResult.CONTINUE, context.current_warning
            
            # Phase 2-N: Iterative RAG until agent is satisfied
            rag_state = RAGState()
            
            while rag_state.can_continue():
                rag_state.iteration_count += 1
                self.logger.info(f"RAG iteration {rag_state.iteration_count}/{rag_state.max_iterations}")
                
                # Get next request from agent
                agent_request = self._get_next_rag_request(context, rag_state)
                
                if agent_request.get("action") == "request_files":
                    # Retrieve requested files
                    requested_paths = agent_request.get("files", [])[:rag_state.max_files_per_request]
                    files = self._retrieve_requested_files(context.project_id, requested_paths)
                    rag_state.add_files(files)
                    self.logger.info(f"Retrieved {len(files)} files: {[f.path for f in files]}")
                    
                elif agent_request.get("action") == "complete":
                    rag_state.complete = True
                    self.logger.info("Agent signaled completion")
                    break
                    
                else:
                    self.logger.warning(f"Unknown action: {agent_request.get('action')}")
                    break
            
            # Final synthesis
            return self._synthesize_final_result(context, rag_state)
            
        except Exception as e:
            self.logger.error(f"Context awareness analysis failed: {str(e)}")
            self.cr_logger.error(f"[{self.name}] Context analysis failed: {str(e)}")
            return PipelineResult.CONTINUE, context.current_warning
    
    def _needs_rag_analysis(self, context: AgentContext) -> bool:
        """Phase 1: Determine if broader context analysis is needed."""
        try:
            current_description = " | ".join(context.current_warning.description)
            
            messages = [
                {
                    "role": "user",
                    "content": f"""Analyze this code review warning to determine if broader codebase context is needed:

File: {context.file_path}
Warning: {context.current_warning.title}
Description: {current_description}
Severity: {context.current_warning.severity}

Code Change:
OLD:
```
{context.old_version[:1000]}{'...' if len(context.old_version) > 1000 else ''}
```

NEW:
```
{context.new_version[:1000]}{'...' if len(context.new_version) > 1000 else ''}
```

Consider if this warning might be:
1. Part of a larger refactoring effort
2. Justified by architectural patterns in other files
3. Related to changes in calling code or dependencies
4. Experimental or work-in-progress code
5. Following patterns established elsewhere

Respond with JSON:
{{
    "needs_context": true/false,
    "reasoning": "Brief explanation of why context is/isn't needed"
}}"""
                }
            ]
            
            response = self.client.messages.create(
                model=self.model,
                system=self._build_assessment_system_prompt(),
                messages=messages,
                max_tokens=300
            )
            
            result = self._parse_needs_analysis(response.content[0].text)
            self.logger.info(f"RAG assessment: {result.get('needs_context')} - {result.get('reasoning')}")
            return result.get('needs_context', False)
            
        except Exception as e:
            self.logger.error(f"RAG assessment failed: {e}")
            # Default to needing context on error
            return True
    
    def _get_next_rag_request(self, context: AgentContext, rag_state: RAGState) -> Dict[str, Any]:
        """Get next RAG request from agent based on current state."""
        try:
            # Build context for the request
            if rag_state.iteration_count == 1:
                # First iteration - file selection
                prompt_context = self._build_file_selection_context(context)
            else:
                # Subsequent iterations - analyze retrieved files and decide next steps
                prompt_context = self._build_iteration_context(context, rag_state)
            
            messages = [
                {
                    "role": "user", 
                    "content": prompt_context
                }
            ]
            
            response = self.client.messages.create(
                model=self.model,
                system=self._build_rag_system_prompt(),
                messages=messages,
                max_tokens=500
            )
            
            return self._parse_rag_request(response.content[0].text)
            
        except Exception as e:
            self.logger.error(f"RAG request failed: {e}")
            return {"action": "complete", "analysis": {"error": str(e)}}
    
    def _build_file_selection_context(self, context: AgentContext) -> str:
        """Build context for initial file selection."""
        current_description = " | ".join(context.current_warning.description)
        
        return f"""You need to gather broader codebase context for this warning:

File Being Changed: {context.file_path}
Warning: {context.current_warning.title}
Description: {current_description}

Code Change:
OLD:
```
{context.old_version}
```

NEW:  
```
{context.new_version}
```

Which specific files do you need to see to understand if this change is justified by broader context? 
Provide exact file paths or patterns. Focus on:
- Files that might call this code
- Related utility/helper files
- Configuration or setup files
- Test files that might reveal intent
- Files with similar patterns

Respond with JSON:
{{
    "action": "request_files",
    "files": ["exact/path/to/file1.py", "path/to/file2.py"],
    "reasoning": "Why each file is needed for context"
}}

Limit to {RAGState().max_files_per_request} most important files."""
    
    def _build_iteration_context(self, context: AgentContext, rag_state: RAGState) -> str:
        """Build context for subsequent iterations."""
        files_summary = self._format_retrieved_files_summary(rag_state.retrieved_files)
        
        return f"""You've retrieved these files for context analysis:

{files_summary}

Original Warning: {context.current_warning.title}
Changed File: {context.file_path}

Based on what you've seen, do you need additional files, or do you have enough context to complete your analysis?

If you need more files, respond with:
{{
    "action": "request_files", 
    "files": ["path1.py", "path2.py"],
    "reasoning": "Why these additional files are needed"
}}

If you have enough context, respond with:
{{
    "action": "complete",
    "analysis": {{
        "cancel_pipeline": true/false,
        "context_insights": "What the broader context reveals",
        "justification": "Why the change might be justified",
        "additional_context": "Additional warning description with context",
        "new_suggestions": ["suggestion1", "suggestion2"],
        "architectural_notes": "Relevant architectural observations"
    }}
}}"""
    
    def _retrieve_requested_files(self, project_id: int, file_paths: List[str]) -> List[File]:
        """Retrieve specific files requested by the agent."""
        retrieved_files = []
        
        for file_path in file_paths:
            try:
                # Try exact path first
                file_obj = self.query_single_file(project_id, file_path)
                if file_obj and file_obj.content:
                    retrieved_files.append(file_obj)
                    continue
                
                # If exact path fails, try pattern matching
                pattern_matches = self.search_files_by_pattern(project_id, file_path, max_results=3)
                for match in pattern_matches:
                    if match.path != file_path:  # Don't retrieve the same file being changed
                        full_match = self.query_single_file(project_id, match.path)
                        if full_match and full_match.content:
                            retrieved_files.append(full_match)
                            break  # Only take first match per pattern
                
            except Exception as e:
                self.logger.warning(f"Failed to retrieve {file_path}: {e}")
        
        return retrieved_files
    
    def _synthesize_final_result(self, context: AgentContext, rag_state: RAGState) -> tuple[PipelineResult, Optional[WarningMessage]]:
        """Synthesize final result from RAG analysis."""
        if not rag_state.retrieved_files:
            self.logger.info("No files retrieved, continuing with original warning")
            return PipelineResult.CONTINUE, context.current_warning
        
        # Get final analysis from the last conversation
        try:
            final_analysis = self._get_final_analysis(context, rag_state)
            
            if final_analysis.get('cancel_pipeline', False):
                self.logger.info("Change justified by broader context, cancelling pipeline")
                self.cr_logger.info(f"[{self.name}] Change justified by context - cancelling pipeline")
                return PipelineResult.CANCEL, None
            
            # Enhance warning with context insights
            enhanced_warning = self._enhance_warning_with_context(
                context.current_warning,
                final_analysis,
                len(rag_state.retrieved_files)
            )
            
            self.cr_logger.info(f"[{self.name}] Enhanced warning with context from {len(rag_state.retrieved_files)} files")
            return PipelineResult.CONTINUE, enhanced_warning
            
        except Exception as e:
            self.logger.error(f"Final synthesis failed: {e}")
            return PipelineResult.CONTINUE, context.current_warning
    
    def _get_final_analysis(self, context: AgentContext, rag_state: RAGState) -> Dict[str, Any]:
        """Get comprehensive final analysis from agent."""
        files_context = self._format_retrieved_files(rag_state.retrieved_files)
        current_description = " | ".join(context.current_warning.description)
        
        messages = [
            {
                "role": "user",
                "content": f"""Provide your final analysis based on all retrieved context:

Original Warning: {context.current_warning.title}: {current_description}
Changed File: {context.file_path}

Retrieved Context Files:
{files_context}

Code Change:
OLD:
```
{context.old_version}
```

NEW:
```
{context.new_version}
```

Provide comprehensive analysis:
{{
    "cancel_pipeline": true/false,
    "context_insights": "What the broader context reveals about this change",
    "justification": "Why the change might be justified (if applicable)", 
    "additional_context": "Additional warning description with context",
    "architectural_notes": "Relevant architectural observations",
    "new_suggestions": ["context-based suggestion1", "suggestion2"],
    "confidence_impact": 0.0 to 0.3
}}"""
            }
        ]
        
        response = self.client.messages.create(
            model=self.model,
            system=self._build_analysis_system_prompt(),
            messages=messages,
            max_tokens=800
        )
        
        return self._parse_context_analysis(response.content[0].text)
    
    def _format_retrieved_files_summary(self, files: List[File]) -> str:
        """Format retrieved files summary for iteration context."""
        if not files:
            return "No files retrieved yet."
        
        summary_lines = []
        for i, file in enumerate(files, 1):
            summary_lines.append(f"{i}. {file.path} ({len(file.content)} chars)")
        
        return "\n".join(summary_lines)
    
    def _format_retrieved_files(self, files: List[File]) -> str:
        """Format retrieved files with full content for final analysis."""
        if not files:
            return "No files retrieved."
        
        formatted = []
        for i, file in enumerate(files, 1):
            content_preview = file.content[:2000] + ('...' if len(file.content) > 2000 else '')
            formatted.append(f"""
== File #{i}: {file.path} ==
Size: {len(file.content)} characters
Content:
```
{content_preview}
```
""")
        
        return "\n".join(formatted)
    
    def _parse_needs_analysis(self, response: str) -> Dict[str, Any]:
        """Parse initial needs assessment response."""
        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return json.loads(response)
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.warning(f"Failed to parse needs analysis: {e}")
            return {"needs_context": True, "reasoning": "Parse error - defaulting to needing context"}
    
    def _parse_rag_request(self, response: str) -> Dict[str, Any]:
        """Parse RAG request from agent."""
        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return json.loads(response)
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.warning(f"Failed to parse RAG request: {e}")
            return {"action": "complete", "analysis": {"error": f"Parse error: {e}"}}
    
    def _parse_context_analysis(self, response: str) -> Dict[str, Any]:
        """Parse final context analysis response."""
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
    
    def _enhance_warning_with_context(self, warning: WarningMessage, analysis: Dict[str, Any], file_count: int) -> WarningMessage:
        """Enhance warning message with context insights using ADDITIVE approach."""
        # Add context-enhanced descriptions
        if analysis.get('additional_context'):
            warning.description.append(f"Context: {analysis['additional_context']}")
        
        if analysis.get('context_insights'):
            warning.description.append(f"Broader insights: {analysis['context_insights']}")
        
        # Add context-based suggestions
        new_suggestions = analysis.get('new_suggestions', [])
        if new_suggestions:
            warning.suggestions.extend(new_suggestions)
        
        # Add architectural justification
        if analysis.get('justification'):
            warning.suggestions.append(f"Architectural context: {analysis['justification']}")
        
        # Add agent analysis
        warning.add_agent_analysis(self.name, {
            "timestamp": datetime.datetime.now().isoformat(),
            "reasoning": analysis.get('context_insights', ''),
            "confidence_impact": analysis.get('confidence_impact', 0.1),
            "files_analyzed": file_count,
            "architectural_notes": analysis.get('architectural_notes', ''),
            "justification": analysis.get('justification', '')
        })
        
        # Adjust confidence based on analysis
        confidence_impact = analysis.get('confidence_impact', 0.1)
        warning.confidence = min(1.0, warning.confidence + confidence_impact)
        
        self.cr_logger.info(f"[{self.name}] Enhanced warning with intelligent context from {file_count} files")
        return warning
    
    def _build_assessment_system_prompt(self) -> str:
        """System prompt for initial RAG needs assessment."""
        return """You are a senior software architect analyzing code review warnings. Your job is to determine if a warning needs broader codebase context to be properly understood.

Consider warnings that might need context:
- Unused variables/functions (might be WIP or future use)
- Code quality issues (might follow project patterns)
- Architectural violations (might be justified by larger refactoring)
- Performance concerns (might be intentional for specific use cases)

Consider warnings that DON'T need context:
- Clear syntax errors
- Obvious security vulnerabilities  
- Simple formatting issues
- Basic logic errors

Be selective - only request context when it could genuinely change the assessment."""
    
    def _build_rag_system_prompt(self) -> str:
        """System prompt for RAG file selection and iteration."""
        return """You are a senior software architect performing intelligent code analysis. Your goal is to gather just enough context to understand if a code change is justified by broader architectural patterns.

When selecting files:
- Be specific with exact paths when possible
- Focus on high-signal files (callers, tests, related modules)
- Avoid bulk retrieval - select purposefully
- Consider architectural relationships, not just file proximity

When deciding if you need more files:
- Only request additional files if current context is insufficient
- Stop when you have enough information to make a judgment
- Prefer depth over breadth in analysis"""
    
    def _build_analysis_system_prompt(self) -> str:
        """System prompt for final comprehensive analysis."""
        return """You are a senior software architect providing final analysis of code changes in broader context.

Your analysis should:
- Determine if the change is justified by architectural patterns
- Provide concrete insights based on retrieved context
- Give specific, actionable suggestions when improvements are needed  
- Consider the change within the larger system design

Be decisive - either the context justifies the change (cancel pipeline) or it provides valuable insights to enhance the warning."""
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt from the JSON configuration."""
        return self.system_prompt or "You are a senior software architect with deep understanding of codebase context."