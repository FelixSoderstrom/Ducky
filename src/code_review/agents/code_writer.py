# Writes the code to fix the issue.

# args: new version, old version, warning message

# Returns: the complete working version of the file.

from typing import Optional
import json
from anthropic import Anthropic

from .base.base_agent import CodeReviewAgent
from ..models.pipeline_models import PipelineResult, WarningMessage, AgentContext


class CodeWriter(CodeReviewAgent):
    """Agent that creates improved code examples addressing identified issues."""
    
    def __init__(self, api_key: str):
        super().__init__("CodeWriter", "code_writer")
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"
    
    def analyze(self, context: AgentContext) -> tuple[PipelineResult, str]:
        """
        Write corrected code example. Cannot cancel pipeline.
        Returns code solution string instead of warning message.
        """
        self.logger.info("Writing code solution")
        
        if not context.current_warning:
            self.logger.warning("No warning message to base code solution on")
            return PipelineResult.CONTINUE, f"# Original code\n{context.new_version}"
        
        try:
            # Generate improved code using LLM
            solution = self._generate_code_solution(context)
            return PipelineResult.CONTINUE, solution
            
        except Exception as e:
            self.logger.error(f"Code writing failed: {str(e)}")
            # Fallback to commented version of new code
            return PipelineResult.CONTINUE, f"# Code solution generation failed: {str(e)}\n# Original code:\n{context.new_version}"
    
    def _generate_code_solution(self, context: AgentContext) -> str:
        """Use LLM to generate improved code solution."""
        try:
            system_prompt = self._build_system_prompt()
            
            # Prepare suggestions summary
            suggestions_text = "\n".join([f"- {s}" for s in context.current_warning.suggestions]) if context.current_warning.suggestions else "No specific suggestions provided"
            
            messages = [
                {
                    "role": "user",
                    "content": f"""File Path: {context.file_path}

Original Version:
```
{context.old_version}
```

Current Version (with issues):
```
{context.new_version}
```

Warning Analysis:
Title: {context.current_warning.title}
Description: {context.current_warning.description}
Severity: {context.current_warning.severity}

Suggested Improvements:
{suggestions_text}

Metadata: {context.current_warning.metadata}

Please provide a corrected version of the code that addresses all identified issues while:

Respond with the complete corrected code and nothing else."""
                }
            ]
            
            response = self.client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=messages,
                max_tokens=2000
            )
            
            solution = response.content[0].text.strip()
            
            # Add header comment if not already present
            if not solution.startswith("#"):
                header = f"# Corrected version addressing: {context.current_warning.title}\n# Improvements made based on code analysis\n\n"
                solution = header + solution
            
            self.logger.info(f"Generated code solution ({len(solution)} characters)")
            return solution
            
        except Exception as e:
            self.logger.error(f"LLM call failed in code writing: {e}")
            # Create a basic solution with comments
            return f"""# Corrected version based on analysis
# Original issue: {context.current_warning.title}
# Description: {context.current_warning.description}

# TODO: Apply the following improvements:
{chr(10).join([f"# - {s}" for s in context.current_warning.suggestions]) if context.current_warning.suggestions else "# - Manual review required"}

{context.new_version}"""
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt from the JSON configuration."""
        return self.system_prompt or "You are an expert programmer who writes clean, educational code examples."