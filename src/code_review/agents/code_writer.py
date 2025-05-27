# Writes the code to fix the issue.

# args: new version, old version, warning message

# Returns: the complete working version of the file.

from typing import Optional
from anthropic import Anthropic

class CodeWriter:
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"

    async def process(
        self,
        new_version: str,
        old_version: str,
        warning_message: str
    ) -> str:
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""Old Version: {old_version}
                        New Version: {new_version}
                        Warning: {warning_message}
                        
                        Please provide a complete working version of the file that fixes the issues."""
                    }
                ]
            }
        ]
        
        response = await self.client.messages.create(
            model=self.model,
            messages=messages,
            max_tokens=2000
        )
        
        # Extract text from the first content block
        return response.content[0].text