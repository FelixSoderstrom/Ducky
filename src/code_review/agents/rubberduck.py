# An open chat with claude.
# Used to talk to, not for code generation.

# Args: warning message, new file, code solution suggestion

# returns: response from claude

from typing import Optional
from anthropic import Anthropic

class RubberDuck:
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"

    async def process(
        self,
        warning_message: str,
        new_file: str,
        code_solution_suggestion: str
    ) -> str:
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""Warning: {warning_message}
                        New File: {new_file}
                        Suggested Solution: {code_solution_suggestion}"""
                    }
                ]
            }
        ]
        
        response = await self.client.messages.create(
            model=self.model,
            messages=messages,
            max_tokens=1000
        )
        
        # Extract text from the first content block
        return response.content[0].text