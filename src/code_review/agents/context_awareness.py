# Follows the pipeline backwards to gain betetr contextual understanding of the issue.

# Args: new version, old version, path to new version, warning message

from typing import Optional
from anthropic import Anthropic

class ContextAwareness:
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"

    async def process(
        self,
        new_version: str,
        old_version: str,
        file_path: str,
        warning_message: str
    ) -> str:
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""File Path: {file_path}
                        Old Version: {old_version}
                        New Version: {new_version}
                        Current Warning: {warning_message}
                        
                        Please analyze the changes in context of the file location and provide enhanced contextual understanding."""
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