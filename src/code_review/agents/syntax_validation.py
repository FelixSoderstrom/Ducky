# Checks the new version of the file for syntax errors.

# Args: new file, warning message

# Returns: enhanced warning message from a syntax standpoint

from typing import Optional
from anthropic import Anthropic

class SyntaxValidation:
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"

    async def process(
        self,
        new_file: str,
        warning_message: str
    ) -> str:
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""New File Content: {new_file}
                        Current Warning: {warning_message}
                        
                        Please analyze the code for syntax errors and enhance the warning message from a syntax perspective."""
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