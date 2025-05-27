from typing import Optional
import json
from anthropic import Anthropic

from ..utils.pipeline import CodeReviewAgent, PipelineResult, WarningMessage, AgentContext


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
        
        # Check for trivial changes that should cancel pipeline
        if self._is_trivial_change(context.old_version, context.new_version):
            self.logger.info("Trivial change detected, cancelling pipeline")
            return PipelineResult.CANCEL, None
        
        try:
            # Call LLM with system prompt
            response = self._call_llm(context)
            
            # Parse response and create warning message
            warning = self._parse_response(response, context)
            
            if warning is None:
                self.logger.info("No issues found, cancelling pipeline")
                return PipelineResult.CANCEL, None
            
            return PipelineResult.CONTINUE, warning
            
        except Exception as e:
            self.logger.error(f"LLM call failed: {str(e)}")
            # Return a basic warning on failure
            warning = WarningMessage(
                title="Code change requires review",
                description="Unable to perform detailed analysis, manual review recommended",
                affected_files=[context.file_path],
                confidence=0.3,
                metadata={"agent": self.name, "error": str(e)}
            )
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

Please analyze these code changes and determine if they warrant further review. Focus on functional changes that could introduce bugs, security issues, or performance problems. Ignore trivial changes like formatting, comments, or cosmetic improvements.

Respond with JSON in this format:
{{
    "should_continue": true/false,
    "title": "Brief issue title",
    "description": "Detailed description of the problem",
    "severity": "low/medium/high/critical",
    "confidence": 0.0-1.0,
    "reasoning": "Why this change needs attention"
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
        """Parse LLM response into a WarningMessage."""
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
            
            return WarningMessage(
                title=response_data.get('title', 'Code change requires review'),
                description=response_data.get('description', 'Potential issues detected'),
                severity=response_data.get('severity', 'medium'),
                confidence=response_data.get('confidence', 0.5),
                affected_files=[context.file_path],
                metadata={
                    "agent": self.name,
                    "reasoning": response_data.get('reasoning', ''),
                    "raw_response": response
                }
            )
            
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.warning(f"Failed to parse LLM response: {e}")
            # Fallback: create warning from raw response
            return WarningMessage(
                title="Code change requires review",
                description=response[:500] + "..." if len(response) > 500 else response,
                affected_files=[context.file_path],
                confidence=0.5,
                metadata={"agent": self.name, "parse_error": str(e)}
            )
    
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