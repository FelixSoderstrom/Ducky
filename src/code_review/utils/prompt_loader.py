"""System prompt loading utilities for code review agents."""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger("ducky.utils.prompt_loader")


class PromptLoader:
    """Utility class for loading system prompts from configuration."""
    
    _prompts_cache: Optional[Dict[str, str]] = None
    _prompts_file_path = Path("src/code_review/utils/system_prompts.json")
    
    @classmethod
    def load_prompt(cls, agent_type: str) -> str:
        """
        Load system prompt for a specific agent type.
        
        Args:
            agent_type: Type of agent (e.g., "initial_assessment", "notification_writer")
            
        Returns:
            System prompt string or empty string if not found
        """
        if cls._prompts_cache is None:
            cls._load_prompts_cache()
        
        return cls._prompts_cache.get(agent_type, "")
    
    @classmethod
    def _load_prompts_cache(cls) -> None:
        """Load and cache all system prompts from JSON file."""
        try:
            with open(cls._prompts_file_path, 'r', encoding='utf-8') as f:
                cls._prompts_cache = json.load(f)
            logger.debug(f"Loaded {len(cls._prompts_cache)} system prompts")
        except FileNotFoundError:
            logger.warning(f"System prompts file not found at {cls._prompts_file_path}")
            cls._prompts_cache = {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in system prompts file: {e}")
            cls._prompts_cache = {}
        except Exception as e:
            logger.error(f"Error loading system prompts: {e}")
            cls._prompts_cache = {}
    
    @classmethod
    def reload_prompts(cls) -> None:
        """Reload prompts from file (useful for development/testing)."""
        cls._prompts_cache = None
        cls._load_prompts_cache()
    
    @classmethod
    def get_available_agent_types(cls) -> list[str]:
        """Get list of available agent types with prompts."""
        if cls._prompts_cache is None:
            cls._load_prompts_cache()
        return list(cls._prompts_cache.keys()) 