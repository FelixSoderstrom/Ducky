"""RubberDuck agent for conversational code review discussions."""

from typing import Optional, List, Dict, Any
from anthropic import Anthropic

from .base.rag_agent import RAGCapableAgent
from ..models.pipeline_models import PipelineResult, WarningMessage, AgentContext


class RubberDuck(RAGCapableAgent):
    """Conversational agent for discussing code review feedback with developers."""
    
    def __init__(self, api_key: str):
        super().__init__("RubberDuck", "rubberduck")
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"
        self.conversation_history: List[Dict[str, str]] = []
        self.pipeline_data: Optional[Dict[str, Any]] = None
        
        # Define tools for RAG capabilities
        self.tools = [
            {
                "name": "query_file",
                "description": "Query the current content of a specific file from the database. Use this when you need to see the latest version of a file to help the developer.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The exact path of the file to retrieve"
                        }
                    },
                    "required": ["file_path"]
                }
            }
        ]
        
    def initialize_conversation(self, pipeline_data: Dict[str, Any]) -> None:
        """
        Initialize the conversation with pipeline data from code review.
        
        Args:
            pipeline_data: Dictionary containing notification, warning (WarningMessage), solution, 
                          old_version, new_version, file_path, project_id for full context
        """
        self.pipeline_data = pipeline_data
        self.conversation_history = []
        
        # Extract warning data - now it's a dictionary structure
        warning_data = pipeline_data.get("warning", {})
        warning_title = warning_data.get("title", "")
        warning_descriptions = warning_data.get("description", [])
        warning_suggestions = warning_data.get("suggestions", [])
        agent_contributions = warning_data.get("agent_contributions", [])
        
        # Extract other context
        notification_text = pipeline_data.get("notification", "")
        solution = pipeline_data.get("solution", "")
        file_path = pipeline_data.get("file_path", "")
        project_id = pipeline_data.get("project_id", "")
        
        # NEW: We now have access to the actual code!
        old_version = pipeline_data.get("old_version", "")
        new_version = pipeline_data.get("new_version", "")
        
        initial_context = f"""
Code Review Context:
- File: {file_path}
- Project ID: {project_id}
- Warning Title: {warning_title}
- Warning Details: {' | '.join(warning_descriptions)}
- Suggestions: {', '.join(warning_suggestions[:3])}
- Agents Involved: {', '.join(agent_contributions)}
- Notification Sent: {notification_text}
- Solution Available: {'Yes' if solution else 'No'}
- Code Context: Old version ({len(old_version)} chars) vs New version ({len(new_version)} chars)

The developer has chosen to discuss this code review feedback.
"""
        
        self.logger.info("RubberDuck conversation initialized with full pipeline data")
        self.cr_logger.info(f"[{self.name}] Conversation initialized")
        self.cr_logger.info(f"[{self.name}] File: {file_path}")
        self.cr_logger.info(f"[{self.name}] Warning: {warning_title}")
        self.cr_logger.info(f"[{self.name}] Agents: {', '.join(agent_contributions)}")
        self.cr_logger.info(f"[{self.name}] Full context available for RAG")
        
    async def chat(self, user_message: str) -> str:
        """
        Process a chat message from the user and return Ducky's response.
        
        Args:
            user_message: Message from the developer
            
        Returns:
            Ducky's response
        """
        if not self.pipeline_data:
            return "I need to be initialized with pipeline data before we can chat."
        
        try:
            # Add user message to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": user_message
            })
            
            self.logger.info(f"Processing chat message: {user_message[:50]}...")
            self.cr_logger.info(f"[{self.name}] User: {user_message}")
            
            # Build messages for API call
            messages = self._build_conversation_messages()
            
            # Call Claude API with tools
            response = self.client.messages.create(
                model=self.model,
                system=self.system_prompt,
                messages=messages,
                tools=self.tools,
                max_tokens=1000
            )
            
            # Check if any content block contains tool use
            has_tool_calls = any(
                hasattr(block, 'type') and block.type == "tool_use" 
                for block in response.content
            )
            
            if has_tool_calls:
                return await self._handle_tool_calls(response, messages)
            else:
                # Regular text response
                ducky_response = response.content[0].text
                
                # Add Ducky's response to conversation history
                self.conversation_history.append({
                    "role": "assistant", 
                    "content": ducky_response
                })
                
                self.logger.info(f"Generated response: {ducky_response[:50]}...")
                self.cr_logger.info(f"[{self.name}] Ducky: {ducky_response}")
                
                return ducky_response
            
        except Exception as e:
            self.logger.error(f"Chat processing failed: {str(e)}")
            self.cr_logger.error(f"[{self.name}] Chat error: {str(e)}")
            return "I'm having trouble processing your message right now. Could you try again?"
    
    def _build_conversation_messages(self) -> List[Dict[str, str]]:
        """Build the messages array for the Anthropic API call."""
        messages = []
        
        # Add initial context if this is the first exchange
        if len(self.conversation_history) == 1:  # Only user's first message
            context_message = self._build_initial_context_message()
            messages.append({
                "role": "user",
                "content": context_message
            })
        
        # Add conversation history
        messages.extend(self.conversation_history)
        
        return messages
    
    def _build_initial_context_message(self) -> str:
        """Build the initial context message with pipeline data."""
        notification = self.pipeline_data.get("notification", "")
        solution = self.pipeline_data.get(
            "solution", "No solution has been provided during code review. Please provide it during conversation with the DEVELOPER."
        )
        path = self.pipeline_data.get("file_path", "Unknown")
        reviewed_code = self.pipeline_data.get("new_version", "The reviewed code could not be retrieved.")
        w = self.pipeline_data.get("warning", {})
        title = w.get("title", "This code review has no title.")
        severity = w.get("severity", "Unknown")
        confidence = w.get("confidence", 0.0)
        descriptions = w.get("description", [])
        suggestions = w.get("suggestions", [])
        files = w.get("affected_files", [])
        reasoning = [data.get("reasoning", "") for data in self.pipeline_data.get("metadata", {})]

        context = f"""
The following code was reviewed by the CODE REVIEW TEAM:
{reviewed_code}

Brief description of the problem:
{title}

Comments made by the CODE REVIEW TEAM in their area of expertise:
{' - '.join(descriptions)}

This is the reasoning according to the CODE REVIEW TEAM:
{' - '.join(reasoning)}

The CODE REVIEW TEAM has suggested this COMPLETE SOLUTION:
{solution}

DUCKY should, by conversating, steer the DEVELOPER towards the COMPLETE SOLUTION by emphasizing the following suggestions:
{', '.join(suggestions)}

The following AFFECTED FILES were taken into consideration during the code review:
{path}, {', '.join(files)}

Additional information about the code review:
- Path of the reviewed file: {path}
- Project ID: {self.pipeline_data.get("project_id", "Unknown")}
- Code review has declared a severity of: {severity}
- Code review team has a confidence of: {confidence*100}%


DUCKY is now being connected to the DEVELOPER.
"""
        return context
        
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get a summary of the current conversation state."""
        return {
            "message_count": len(self.conversation_history),
            "pipeline_data_available": self.pipeline_data is not None,
            "last_user_message": self.conversation_history[-2]['content'] if len(self.conversation_history) >= 2 else None,
            "last_ducky_response": self.conversation_history[-1]['content'] if len(self.conversation_history) >= 1 and self.conversation_history[-1]['role'] == 'assistant' else None,
            "file_path": self.pipeline_data.get("file_path", "Unknown") if self.pipeline_data else "Unknown",
            "project_id": self.pipeline_data.get("project_id", "Unknown") if self.pipeline_data else "Unknown"
        }
    
    def reset_conversation(self) -> None:
        """Reset the conversation history while keeping pipeline data."""
        self.conversation_history = []
        self.logger.info("Conversation history reset")
        self.cr_logger.info(f"[{self.name}] Conversation reset")
    
    # Required method from CodeReviewAgent (not used in chat mode)
    def analyze(self, context: AgentContext) -> tuple[PipelineResult, Optional[WarningMessage]]:
        """Not used - RubberDuck operates in chat mode, not pipeline mode."""
        return PipelineResult.CONTINUE, context.current_warning

    async def _handle_tool_calls(self, response, messages: List[Dict[str, str]]) -> str:
        """Handle tool calls from Claude and return final response."""
        try:
            # Extract text and tool calls from response
            text_parts = []
            tool_calls = []
            
            for content_block in response.content:
                if hasattr(content_block, 'type'):
                    if content_block.type == "text":
                        text_parts.append(content_block.text)
                    elif content_block.type == "tool_use":
                        tool_calls.append(content_block)
            
            # Build assistant message with both text and tool calls
            assistant_message = {
                "role": "assistant",
                "content": []
            }
            
            # Add text parts
            for text in text_parts:
                assistant_message["content"].append({
                    "type": "text",
                    "text": text
                })
            
            # Add tool use blocks
            for tool_call in tool_calls:
                assistant_message["content"].append({
                    "type": "tool_use",
                    "id": tool_call.id,
                    "name": tool_call.name,
                    "input": tool_call.input
                })
            
            messages.append(assistant_message)
            
            # Process tool calls and create tool results
            tool_result_messages = []
            for tool_call in tool_calls:
                if tool_call.name == "query_file":
                    file_path = tool_call.input.get("file_path")
                    project_id = self.pipeline_data.get("project_id")
                    
                    self.logger.info(f"RAG query requested for file: {file_path}")
                    self.cr_logger.info(f"[{self.name}] RAG: Querying {file_path}")
                    
                    # Query the file from database
                    file_obj = self.query_single_file(project_id, file_path)
                    
                    if file_obj and file_obj.content:
                        tool_result_content = f"File: {file_path}\nContent:\n{file_obj.content}"
                        self.cr_logger.info(f"[{self.name}] RAG: Retrieved {len(file_obj.content)} chars")
                    else:
                        tool_result_content = f"File not found or empty: {file_path}"
                        self.cr_logger.info(f"[{self.name}] RAG: File not found")
                    
                    # Add tool result message
                    tool_result_msg = {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_call.id,
                                "content": tool_result_content
                            }
                        ]
                    }
                    messages.append(tool_result_msg)
                    tool_result_messages.append(tool_result_msg)
            
            # Get final response from Claude with tool results
            final_response = self.client.messages.create(
                model=self.model,
                system=self.system_prompt,
                messages=messages,
                tools=self.tools,
                max_tokens=1000
            )
            
            # Extract final text response
            final_text = ""
            for block in final_response.content:
                if hasattr(block, 'type') and block.type == "text":
                    final_text += block.text
            
            # FIXED: Store the complete tool interaction in conversation history
            # Store the assistant message with tool calls
            initial_text = " ".join(text_parts) if text_parts else ""
            if initial_text:
                self.conversation_history.append({
                    "role": "assistant",
                    "content": initial_text
                })
            
            # Store tool results as assistant context (not system - API doesn't accept system role)
            for tool_call in tool_calls:
                if tool_call.name == "query_file":
                    file_path = tool_call.input.get("file_path")
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": f"[I retrieved and analyzed the file: {file_path}]"
                    })
            
            # Store final response
            self.conversation_history.append({
                "role": "assistant",
                "content": final_text
            })
            
            self.logger.info(f"Generated RAG-enhanced response: {final_text[:50]}...")
            self.cr_logger.info(f"[{self.name}] Ducky (with RAG): {final_text}")
            
            return final_text
            
        except Exception as e:
            self.logger.error(f"Tool call handling failed: {str(e)}")
            self.cr_logger.error(f"[{self.name}] RAG error: {str(e)}")
            return "I had trouble retrieving the file information. Could you try again?"