from typing import Optional
import json
from anthropic import Anthropic
import datetime

from .base.base_agent import CodeReviewAgent
from ..models.pipeline_models import PipelineResult, WarningMessage, AgentContext


class InitialAssessment(CodeReviewAgent):
    """Agent that performs initial code comparison and identifies problems."""
    
    def __init__(self, api_key: str):
        super().__init__("InitialAssessment", "initial_assessment")
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"
    
    def analyze(self, context: AgentContext) -> tuple[PipelineResult, Optional[WarningMessage]]:
        """
        Compare old and new versions to identify potential issues.
        Can cancel pipeline for minor changes like comments, formatting, etc.
        """
        self.logger.info("Starting initial assessment")
        self.cr_logger.info(f"[{self.name}] Analyzing code changes...")
        
        # Check for trivial changes that should cancel pipeline
        if self._is_trivial_change(context.old_version, context.new_version):
            self.logger.info("Trivial change detected, cancelling pipeline")
            self.cr_logger.info(f"[{self.name}] Trivial change detected - cancelling pipeline")
            self.cr_logger.info(f"[{self.name}] Decision: CANCEL (No significant functional changes)")
            return PipelineResult.CANCEL, None
        
        try:
            # Call LLM with system prompt
            self.cr_logger.info(f"[{self.name}] Calling LLM for analysis...")
            response = self._call_llm(context)
            self._log_llm_output(self.name, response)
            
            # Parse response and create warning message using ADDITIVE approach
            warning = self._parse_response(response, context)
            
            if warning is None:
                self.logger.info("No issues found, cancelling pipeline")
                self.cr_logger.info(f"[{self.name}] No issues found - cancelling pipeline")
                self.cr_logger.info(f"[{self.name}] Decision: CANCEL (No problems detected)")
                return PipelineResult.CANCEL, None
            
            self.cr_logger.info(f"[{self.name}] Issue identified: {warning.title}")
            self.cr_logger.info(f"[{self.name}] Severity: {warning.severity} (Confidence: {warning.confidence:.2f})")
            self._log_warning_state(f"{self.name} - CREATED", warning, "CONTINUE")
            
            return PipelineResult.CONTINUE, warning
            
        except Exception as e:
            self.logger.error(f"LLM call failed: {str(e)}")
            self.cr_logger.error(f"[{self.name}] LLM call failed: {str(e)}")
            # Return a basic warning on failure using ADDITIVE approach
            warning = WarningMessage()
            warning.title = "Code change requires review"  # SET ONCE by InitialAssessment
            warning.description.append("Unable to perform detailed analysis, manual review recommended")
            warning.affected_files.append(context.file_path)
            warning.confidence = 0.3
            warning.add_agent_analysis(self.name, {
                "timestamp": datetime.datetime.now().isoformat(),
                "reasoning": f"LLM analysis failed: {str(e)}",
                "confidence_impact": 0.3
            })
            
            self.cr_logger.info(f"[{self.name}] Generated fallback warning due to error")
            self._log_warning_state(f"{self.name} - FALLBACK", warning, "CONTINUE")
            return PipelineResult.CONTINUE, warning
    
    def _call_llm(self, context: AgentContext) -> str:
        """Make the LLM call with proper system prompt."""
        system_prompt = self._build_system_prompt()
        
        messages = [
            {
                "role": "user",
                "content": f"""File Path: {context.file_path}

Old Version:
```
{context.old_version}
```

New Version:
```
{context.new_version}
```

Analyze the code change and determine if it needs further review. Provide a brief description to where and why the code needs correction.

Respond with JSON in this format:
{{
    "should_continue": true/false,
    "title": "Brief issue title",
    "description": "Brief description of the problem",
    "severity": "low/medium/high/critical",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation on why the code needs correction",
    "suggestions": ["suggestion1", "suggestion2"]
}}

If the change is trivial or doesn't need attention, set should_continue to false."""
            }
        ]
        
        response = self.client.messages.create(
            model=self.model,
            system=system_prompt,
            messages=messages,
            max_tokens=1000
        )
        
        return response.content[0].text
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt from the JSON configuration."""
        return self.system_prompt or "You are an expert code reviewer."
    
    def _parse_response(self, response: str, context: AgentContext) -> Optional[WarningMessage]:
        """Parse LLM response into a WarningMessage using ADDITIVE approach."""
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                response_data = json.loads(json_match.group())
            else:
                response_data = json.loads(response)
            
            if not response_data.get('should_continue', True):
                return None
            
            # Create warning using ADDITIVE approach
            warning = WarningMessage()
            
            # SET ONCE by InitialAssessment
            warning.title = response_data.get('title', 'Code change requires review')
            warning.severity = response_data.get('severity', 'medium')
            warning.confidence = response_data.get('confidence', 0.5)
            
            # APPEND to lists
            warning.description.append(response_data.get('description', 'Potential issues detected'))
            warning.affected_files.append(context.file_path)
            
            # Add suggestions if provided
            suggestions = response_data.get('suggestions', [])
            if suggestions:
                warning.suggestions.extend(suggestions)
            
            # Add agent analysis using helper method
            warning.add_agent_analysis(self.name, {
                "timestamp": datetime.datetime.now().isoformat(),
                "reasoning": response_data.get('reasoning', ''),
                "confidence_impact": response_data.get('confidence', 0.5),
                "raw_response": response[:200] + "..." if len(response) > 200 else response
            })
            
            return warning
            
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.warning(f"Failed to parse LLM response: {e}")
            # Fallback: create warning from raw response using ADDITIVE approach
            warning = WarningMessage()
            warning.title = "Code change requires review"
            warning.description.append(response[:500] + "..." if len(response) > 500 else response)
            warning.affected_files.append(context.file_path)
            warning.confidence = 0.5
            warning.add_agent_analysis(self.name, {
                "timestamp": datetime.datetime.now().isoformat(),
                "reasoning": "Failed to parse structured response",
                "confidence_impact": 0.5,
                "parse_error": str(e)
            })
            return warning
    
    def _is_trivial_change(self, old: str, new: str) -> bool:
        """Check if the change is trivial (comments, whitespace, etc.)."""
        # Quick heuristics for trivial changes
        if old.strip() == new.strip():
            return True
        
        # Remove comments and whitespace for comparison
        import re
        
        def clean_code(code):
            # Remove single-line comments
            code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
            # Remove multi-line comments (Python docstrings)
            code = re.sub(r'""".*?"""', '', code, flags=re.DOTALL)
            code = re.sub(r"'''.*?'''", '', code, flags=re.DOTALL)
            # Normalize whitespace
            return ' '.join(code.split())
        
        clean_old = clean_code(old)
        clean_new = clean_code(new)
        
        return clean_old == clean_new