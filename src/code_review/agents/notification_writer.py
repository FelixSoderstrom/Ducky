# Summarizes the warning message into a more user friendly message

# Args: New file, old file, path to new file, warning message(from initial_assessment.py)

# Returns: User friendly warning message

from typing import Optional
from anthropic import Anthropic

class NotificationWriter:
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"

    async def process(
        self,
        new_file: str,
        old_file: str,
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
                        Old File: {old_file}
                        New File: {new_file}
                        Technical Warning: {warning_message}
                        
                        Please convert this technical warning into a user-friendly message that explains the issues clearly."""
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
