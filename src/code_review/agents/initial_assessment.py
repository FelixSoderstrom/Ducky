from typing import Optional
from anthropic import Anthropic

class InitialAssessment:
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"

    async def process(
        self,
        new_file: str,
        old_file: str,
        file_path: str
    ) -> str:
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""File Path: {file_path}
                        Old Version: {old_file}
                        New Version: {new_file}
                        """
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