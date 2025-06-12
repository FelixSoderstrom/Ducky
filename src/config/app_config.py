from dataclasses import dataclass
from typing import Optional


@dataclass
class AppConfig:
    """Central configuration for the Ducky application."""
    
    # Scanning configuration
    scan_interval_seconds: int = 10
    max_concurrent_pipelines: int = 1
    
    # Logging configuration  
    log_level: str = "INFO"
    
    # Database configuration
    enable_code_review_logging: bool = True
    
    # UI configuration
    startup_timeout_seconds: int = 30
    
    # Animation configuration
    enable_pipeline_animation: bool = True
    animation_cycle_interval: float = 1.0
    
    @classmethod
    def default(cls) -> "AppConfig":
        """Get default application configuration."""
        return cls()
    
    @classmethod
    def from_env(cls) -> "AppConfig":
        """Load configuration from environment variables."""
        import os
        
        return cls(
            scan_interval_seconds=int(os.getenv("DUCKY_SCAN_INTERVAL", "10")),
            max_concurrent_pipelines=int(os.getenv("DUCKY_MAX_PIPELINES", "1")),
            log_level=os.getenv("DUCKY_LOG_LEVEL", "INFO"),
            enable_code_review_logging=os.getenv("DUCKY_CODE_REVIEW_LOGGING", "true").lower() == "true",
            startup_timeout_seconds=int(os.getenv("DUCKY_STARTUP_TIMEOUT", "30")),
            enable_pipeline_animation=os.getenv("DUCKY_PIPELINE_ANIMATION", "true").lower() == "true",
            animation_cycle_interval=float(os.getenv("DUCKY_ANIMATION_INTERVAL", "1.0"))
        ) 