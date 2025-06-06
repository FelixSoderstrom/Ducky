# Validates code against current documentation and best practices using Context7 MCP.

# Args: new file, warning message

# Returns: enhanced warning message with real-time documentation insights

from typing import Optional, Dict, Any
import json
import re
from datetime import datetime
from anthropic import Anthropic

from .base.mcp_agent import MCPCapableAgent
from ..models.pipeline_models import PipelineResult, WarningMessage, AgentContext
from src.services.documentation_service import DocumentationService


class DocumentationValidator(MCPCapableAgent):
    """Agent that validates code against current documentation and best practices using Context7 MCP."""
    
    def __init__(self, api_key: str):
        super().__init__("DocumentationValidator", "syntax_check")
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"
    
    def analyze(self, context: AgentContext) -> tuple[PipelineResult, Optional[WarningMessage]]:
        """
        Validate code against current documentation and best practices.
        """
        self.logger.info("Starting documentation validation with Context7 MCP")
        
        if not context.current_warning:
            self.logger.warning("No warning message to enhance with documentation validation")
            return PipelineResult.CONTINUE, context.current_warning
        
        try:
            # Get targeted documentation using the service (sync version)
            warning_text = f"{context.current_warning.title} {context.current_warning.description}"
            doc_info = self.doc_service.get_targeted_documentation_sync(
                context.file_path, 
                context.new_version, 
                warning_text
            )
            
            # Perform enhanced analysis with documentation
            enhanced_analysis = self._perform_documentation_analysis(context, doc_info)
            
            # Enhance warning with documentation findings
            enhanced_warning = self._enhance_warning_with_documentation(
                context.current_warning,
                enhanced_analysis,
                bool(doc_info and "UNAVAILABLE" not in doc_info)
            )
            
            return PipelineResult.CONTINUE, enhanced_warning
            
        except Exception as e:
            self.logger.error(f"Documentation validation failed: {str(e)}")
            # On error, continue with original warning but add error info
            if context.current_warning:
                context.current_warning.add_agent_analysis(
                    agent_name="DocumentationValidator",
                    analysis_data={
                        "description": "Documentation validation failed due to an error",
                        "suggestions": ["Manual documentation review recommended due to analysis failure"],
                        "metadata": {"error": str(e), "status": "failed"}
                    }
                )
            return PipelineResult.CONTINUE, context.current_warning
    
    def _perform_documentation_analysis(self, context: AgentContext, doc_info: str) -> dict:
        """Use LLM to perform analysis enhanced with real-time documentation."""
        try:
            system_prompt = self._build_system_prompt()
            
            # Check if we have real documentation or fallback
            has_real_docs = doc_info and "UNAVAILABLE" not in doc_info and "ERROR" not in doc_info
            
            doc_section = ""
            if has_real_docs:
                doc_section = f"\n\nCURRENT DOCUMENTATION (via Context7):\n{doc_info}"
            else:
                doc_section = f"\n\nDOCUMENTATION STATUS:\n{doc_info}"
            
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
{doc_section}

Based on {'the current documentation' if has_real_docs else 'general knowledge'}, analyze this code for:
1. Syntax errors and language-specific issues
2. Deprecated methods, patterns, or approaches  
3. Violations of current best practices and conventions
4. Modern language standard compliance
5. Actionable improvement recommendations

Respond with JSON:
{{
    "documentation_consulted": {str(has_real_docs).lower()},
    "syntax_errors": ["list of syntax errors found"],
    "deprecated_patterns": ["list of deprecated patterns with current alternatives"],
    "best_practice_violations": ["list of best practice issues"],
    "modern_alternatives": ["list of modern approaches to replace current code"],
    "recommendations": ["list of specific improvement suggestions"],
    "severity_adjustment": "none/increase/decrease",
    "additional_suggestions": ["specific context-aware suggestions"]
}}"""
                }
            ]
            
            response = self.client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=messages,
                max_tokens=1500
            )
            
            return self._parse_documentation_analysis(response.content[0].text)
            
        except Exception as e:
            self.logger.error(f"LLM call failed in documentation analysis: {e}")
            return {
                "documentation_consulted": False,
                "syntax_errors": [],
                "recommendations": ["Documentation analysis failed - manual review recommended"],
                "severity_adjustment": "none"
            }
    
    def _parse_documentation_analysis(self, response: str) -> dict:
        """Parse LLM response to extract documentation analysis."""
        try:
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
            if response_data.get('documentation_consulted'):
                self.logger.info("Analysis enhanced with real-time Context7 documentation")
            else:
                self.logger.info("Analysis performed with general knowledge (Context7 unavailable)")
            
            syntax_errors = response_data.get('syntax_errors', [])
            if syntax_errors:
                self.logger.info(f"Documentation-verified syntax errors: {len(syntax_errors)}")
            
            deprecated = response_data.get('deprecated_patterns', [])
            if deprecated:
                self.logger.info(f"Documentation-verified deprecated patterns: {len(deprecated)}")
            
            return response_data
            
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.warning(f"Failed to parse documentation analysis: {e}")
            self.logger.debug(f"Raw response: {response[:500]}...")
            return {
                "documentation_consulted": False,
                "syntax_errors": [],
                "recommendations": [response[:300] + "..." if len(response) > 300 else response],
                "severity_adjustment": "none"
            }
    
    def _enhance_warning_with_documentation(self, warning: WarningMessage, analysis: dict, doc_consulted: bool) -> WarningMessage:
        """Enhance the warning message with documentation-based analysis findings."""
        # Build documentation-enhanced description
        doc_description = self._build_documentation_description(analysis, doc_consulted)
        
        # Get suggestions from analysis
        suggestions = analysis.get('additional_suggestions', [])
        if not suggestions:
            suggestions = analysis.get('recommendations', [])
        if not suggestions:
            suggestions = ["Follow current documentation standards and best practices"]
        
        # Add documentation findings to the existing warning
        enhanced_warning = warning.add_agent_analysis(
            agent_name="DocumentationValidator",
            analysis_data={
                "description": doc_description,
                "suggestions": suggestions,
                "metadata": {
                    "documentation_consulted": doc_consulted,
                    "context7_accessed": doc_consulted,
                    "syntax_errors_found": len(analysis.get('syntax_errors', [])),
                    "deprecated_patterns_found": len(analysis.get('deprecated_patterns', [])),
                    "best_practice_violations": len(analysis.get('best_practice_violations', [])),
                    "modern_alternatives": len(analysis.get('modern_alternatives', [])),
                    "analysis_timestamp": datetime.now().isoformat()
                }
            }
        )
        
        # Adjust severity based on documentation findings
        enhanced_warning.severity = self._adjust_severity(warning.severity, analysis.get('severity_adjustment', 'none'))
        
        return enhanced_warning
    
    def _build_documentation_description(self, analysis: dict, doc_consulted: bool) -> str:
        """Build description from documentation analysis findings."""
        doc_status = "Context7 MCP" if doc_consulted else "General knowledge"
        
        findings = []
        
        syntax_errors = analysis.get('syntax_errors', [])
        if syntax_errors:
            findings.append(f"Syntax issues: {', '.join(syntax_errors[:2])}")
        
        deprecated = analysis.get('deprecated_patterns', [])
        if deprecated:
            findings.append(f"Deprecated patterns: {', '.join(deprecated[:2])}")
        
        violations = analysis.get('best_practice_violations', [])
        if violations:
            findings.append(f"Best practice violations: {', '.join(violations[:2])}")
        
        modern_alts = analysis.get('modern_alternatives', [])
        if modern_alts:
            findings.append(f"Modern alternatives available: {len(modern_alts)} suggestions")
        
        if findings:
            return f"Documentation validation ({doc_status}): {' | '.join(findings)}"
        
        return f"Code validated against current documentation ({doc_status}) - follows established patterns"
    
    def _adjust_severity(self, current_severity: str, adjustment: str) -> str:
        """Adjust severity based on documentation analysis findings."""
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
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for documentation validation."""
        return self.system_prompt or """You are a documentation validation expert with access to real-time programming documentation.
        
Your role is to validate code against current best practices, syntax standards, and documentation. 
When provided with Context7 documentation, use it as the authoritative source.
When Context7 is unavailable, rely on your general programming knowledge but indicate this limitation.

Focus on:
- Current syntax standards and conventions
- Deprecated patterns and their modern replacements  
- Best practice violations with specific fixes
- Security and performance considerations
- Type safety and error handling improvements"""