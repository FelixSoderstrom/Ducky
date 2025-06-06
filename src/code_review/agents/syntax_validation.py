# Checks the new version of the file for syntax errors.

# Args: new file, warning message

# Returns: enhanced warning message from a syntax standpoint

from typing import Optional, Dict, Any
import json
from datetime import datetime
from anthropic import Anthropic

from .base.mcp_agent import MCPCapableAgent
from ..models.pipeline_models import PipelineResult, WarningMessage, AgentContext


class SyntaxValidation(MCPCapableAgent):
    """Agent that checks syntax and best practices using documentation."""
    
    def __init__(self, api_key: str):
        super().__init__("SyntaxValidation", "syntax_check")
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"
    
    def analyze(self, context: AgentContext) -> tuple[PipelineResult, Optional[WarningMessage]]:
        """
        Check syntax and best practices. Cannot cancel pipeline.
        """
        self.logger.info("Starting syntax check")
        
        if not context.current_warning:
            self.logger.warning("No warning message to enhance with syntax analysis")
            return PipelineResult.CONTINUE, context.current_warning
        
        try:
            # Query documentation if needed (placeholder for MCP integration)
            doc_info = self.query_documentation(f"syntax check for {context.file_path}")
            
            # Perform syntax analysis
            syntax_analysis = self._perform_syntax_analysis(context, doc_info)
            
            # Enhance warning with syntax findings
            enhanced_warning = self._enhance_warning_with_syntax(
                context.current_warning,
                syntax_analysis,
                bool(doc_info)
            )
            
            return PipelineResult.CONTINUE, enhanced_warning
            
        except Exception as e:
            self.logger.error(f"Syntax validation failed: {str(e)}")
            # On error, continue with original warning but add error info
            if context.current_warning:
                # Use additive approach for error metadata
                context.current_warning.add_agent_analysis(
                    agent_name="SyntaxValidation",
                    analysis_data={
                        "description": "Syntax analysis failed due to an error",
                        "suggestions": ["Manual syntax review recommended due to analysis failure"],
                        "metadata": {"error": str(e), "status": "failed"}
                    }
                )
            return PipelineResult.CONTINUE, context.current_warning
    
    def _perform_syntax_analysis(self, context: AgentContext, doc_info: str) -> dict:
        """Use LLM to perform syntax and best practices analysis."""
        try:
            system_prompt = self._build_system_prompt()
            
            doc_context = f"\nRelevant Documentation:\n{doc_info}" if doc_info else ""
            
            messages = [
                {
                    "role": "user",
                    "content": f"""File Path: {context.file_path}

New Code Version:
```
{context.new_version}
```

Current Warning Context:
{context.current_warning.title}: {context.current_warning.description}
{doc_context}

Please analyze this code for:
1. Syntax errors and language-specific issues
2. Deprecated methods, patterns, or approaches  
3. Violations of current best practices and conventions
4. Modern language standard compliance
5. Actionable improvement recommendations

Respond with JSON:
{{
    "syntax_errors": ["list of syntax errors found"],
    "deprecated_patterns": ["list of deprecated patterns"],
    "best_practice_violations": ["list of best practice issues"],
    "recommendations": ["list of specific improvement suggestions"],
    "severity_adjustment": "none/increase/decrease",
    "additional_suggestions": ["specific suggestions to add"]
}}"""
                }
            ]
            
            response = self.client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=messages,
                max_tokens=1000
            )
            
            return self._parse_syntax_analysis(response.content[0].text)
            
        except Exception as e:
            self.logger.error(f"LLM call failed in syntax analysis: {e}")
            return {
                "syntax_errors": [],
                "recommendations": ["Syntax analysis failed - manual review recommended"],
                "severity_adjustment": "none"
            }
    
    def _parse_syntax_analysis(self, response: str) -> dict:
        """Parse LLM response to extract syntax analysis."""
        try:
            import re
            # Try to find JSON block between triple backticks first
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                # Fallback: look for any JSON object
                json_match = re.search(r'\{[^}]*(?:\{[^}]*\}[^}]*)*\}', response, re.DOTALL)
                if json_match:
                    json_text = json_match.group()
                else:
                    # Last resort: try to parse the whole response
                    json_text = response.strip()
            
            response_data = json.loads(json_text)
            
            # Log key findings
            syntax_errors = response_data.get('syntax_errors', [])
            if syntax_errors:
                self.logger.info(f"Syntax errors found: {len(syntax_errors)}")
            
            deprecated = response_data.get('deprecated_patterns', [])
            if deprecated:
                self.logger.info(f"Deprecated patterns found: {len(deprecated)}")
            
            return response_data
            
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.warning(f"Failed to parse syntax analysis: {e}")
            self.logger.debug(f"Raw response: {response[:500]}...")
            return {
                "syntax_errors": [],
                "recommendations": [response[:300] + "..." if len(response) > 300 else response],
                "severity_adjustment": "none"
            }
    
    def _enhance_warning_with_syntax(self, warning: WarningMessage, analysis: dict, doc_consulted: bool) -> WarningMessage:
        """Enhance the warning message with syntax analysis findings."""
        # Add syntax analysis description
        syntax_description = self._build_syntax_description(analysis)
        
        # Get additional suggestions from analysis
        additional_suggestions = analysis.get('additional_suggestions', [])
        if not additional_suggestions:
            additional_suggestions = ["Follow current syntax standards and best practices"]
        
        # Add syntax findings to the existing warning
        enhanced_warning = warning.add_agent_analysis(
            agent_name="SyntaxValidation",
            analysis_data={
                "description": syntax_description,
                "suggestions": additional_suggestions,
                "metadata": {
                    "syntax_checked": True,
                    "documentation_consulted": doc_consulted,
                    "syntax_errors_found": len(analysis.get('syntax_errors', [])),
                    "deprecated_patterns_found": len(analysis.get('deprecated_patterns', [])),
                    "best_practice_violations": len(analysis.get('best_practice_violations', [])),
                    "analysis_timestamp": datetime.now().isoformat()
                }
            }
        )
        
        # Adjust severity if needed
        enhanced_warning.severity = self._adjust_severity(warning.severity, analysis.get('severity_adjustment', 'none'))
        
        return enhanced_warning
    
    def _adjust_severity(self, current_severity: str, adjustment: str) -> str:
        """Adjust severity based on syntax analysis findings."""
        if adjustment == "none":
            return current_severity
        
        severity_levels = ["low", "medium", "high", "critical"]
        try:
            current_index = severity_levels.index(current_severity)
            
            if adjustment == "increase" and current_index < len(severity_levels) - 1:
                return severity_levels[current_index + 1]
            elif adjustment == "decrease" and current_index > 0:
                return severity_levels[current_index - 1]
        except ValueError:
            pass
        
        return current_severity
    
    def _build_syntax_description(self, analysis: dict) -> str:
        """Build description from syntax analysis findings."""
        syntax_issues = []
        
        syntax_errors = analysis.get('syntax_errors', [])
        if syntax_errors:
            syntax_issues.append(f"Syntax errors found: {', '.join(syntax_errors[:3])}")
        
        deprecated = analysis.get('deprecated_patterns', [])
        if deprecated:
            syntax_issues.append(f"Deprecated patterns: {', '.join(deprecated[:2])}")
        
        violations = analysis.get('best_practice_violations', [])
        if violations:
            syntax_issues.append(f"Best practice violations: {', '.join(violations[:2])}")
        
        if syntax_issues:
            return f"Syntax analysis findings: {' | '.join(syntax_issues)}"
        
        return "Code follows current syntax standards and best practices"
    
    def _enhance_description_with_syntax(self, original_description: str, analysis: dict) -> str:
        """Enhance the warning description with syntax findings."""
        syntax_issues = []
        
        syntax_errors = analysis.get('syntax_errors', [])
        if syntax_errors:
            syntax_issues.append(f"Syntax errors: {', '.join(syntax_errors[:3])}")
        
        deprecated = analysis.get('deprecated_patterns', [])
        if deprecated:
            syntax_issues.append(f"Deprecated patterns: {', '.join(deprecated[:2])}")
        
        violations = analysis.get('best_practice_violations', [])
        if violations:
            syntax_issues.append(f"Best practice violations: {', '.join(violations[:2])}")
        
        if syntax_issues:
            return f"{original_description}\n\nSyntax Analysis: {' | '.join(syntax_issues)}"
        
        return original_description
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt from the JSON configuration."""
        return self.system_prompt or "You are a syntax and best practices expert with access to comprehensive programming documentation."