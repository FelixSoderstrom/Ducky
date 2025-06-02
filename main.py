import asyncio
import logging

# Initialize logging first before other imports
from src.utils.logging_config import setup_logging, setup_code_review_logger
from src.config.app_config import AppConfig
from src.app.application_orchestrator import ApplicationOrchestrator

# Initialize logging with configuration
config = AppConfig.from_env()
setup_logging(log_level=config.log_level)
if config.enable_code_review_logging:
    setup_code_review_logger()

logger = logging.getLogger("ducky.main")


async def main():
    """Main entry point for the Ducky application."""
    orchestrator = ApplicationOrchestrator(config)
    
    try:
        # Initialize application components
        if not await orchestrator.initialize():
            logger.error("Failed to initialize application")
            return
        
        # Set up project (existing or new)
        if not await orchestrator.setup_project():
            logger.warning("Project setup cancelled or failed")
            return
        
        # Run the main application loop
        await orchestrator.run()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error in main: {str(e)}")
    finally:
        # Graceful shutdown
        await orchestrator.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
