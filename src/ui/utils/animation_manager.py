"""Animation manager for UI background image cycling during pipeline execution."""

import asyncio
import logging
from typing import Optional, Callable, List
from enum import Enum

logger = logging.getLogger("ducky.ui.animation_manager")


class AnimationState(Enum):
    """States for the animation manager."""
    IDLE = "idle"
    CYCLING = "cycling"
    STOPPING = "stopping"


class PipelineAnimationManager:
    """Manages background image cycling during pipeline execution."""
    
    def __init__(self, cycle_interval: float = 1.0):
        """Initialize the animation manager.
        
        Args:
            cycle_interval: Time in seconds between image changes
        """
        self.cycle_interval = cycle_interval
        self.state = AnimationState.IDLE
        self._cycle_task: Optional[asyncio.Task] = None
        self._change_image_callback: Optional[Callable[[str], bool]] = None
        self.logger = logger
        
        # Images to cycle through during pipeline execution
        self.review_images = [
            "review1.png",
            "review2.png", 
            "review3.png",
            "review4.png"
        ]
        
        # Image to return to when pipeline is done
        self.idle_image = "idle.png"
        
        # Current cycling state
        self._current_image_index = 0
        self._active_project_ids: set = set()
    
    def set_image_change_callback(self, callback: Callable[[str], bool]) -> None:
        """Set the callback function for changing images.
        
        Args:
            callback: Function that takes image filename and returns success bool
        """
        self._change_image_callback = callback
        self.logger.debug("Image change callback set")
    
    def set_cycle_interval(self, interval: float) -> None:
        """Set the cycling interval.
        
        Args:
            interval: Time in seconds between image changes
        """
        self.cycle_interval = interval
        self.logger.debug(f"Cycle interval set to {interval}s")
    
    def set_review_images(self, images: List[str]) -> None:
        """Set the list of images to cycle through.
        
        Args:
            images: List of image filenames to cycle through
        """
        if not images:
            raise ValueError("Review images list cannot be empty")
        
        self.review_images = images.copy()
        self.logger.debug(f"Review images set: {self.review_images}")
    
    def start_pipeline_animation(self, project_id: int) -> bool:
        """Start the pipeline animation for a project.
        
        Args:
            project_id: ID of the project whose pipeline is starting
            
        Returns:
            bool: True if animation was started, False if already running
        """
        if not self._change_image_callback:
            self.logger.warning("Cannot start animation: no image change callback set")
            return False
        
        # Add project to active set
        self._active_project_ids.add(project_id)
        
        # If already cycling for another project, just add to the set
        if self.state == AnimationState.CYCLING:
            self.logger.info(f"Added project {project_id} to active pipeline animation")
            return True
        
        # Start cycling if not already active
        if self.state == AnimationState.IDLE:
            self.logger.info(f"Starting pipeline animation for project {project_id}")
            self.state = AnimationState.CYCLING
            self._current_image_index = 0
            
            # Start the cycling task
            self._cycle_task = asyncio.create_task(self._cycle_images())
            return True
        
        return False
    
    def stop_pipeline_animation(self, project_id: int) -> bool:
        """Stop the pipeline animation for a project.
        
        Args:
            project_id: ID of the project whose pipeline is ending
            
        Returns:
            bool: True if animation was stopped, False if not running
        """
        # Remove project from active set
        self._active_project_ids.discard(project_id)
        
        # If there are still active projects, keep cycling
        if self._active_project_ids:
            self.logger.info(f"Removed project {project_id} from pipeline animation, but keeping animation active for other projects")
            return False
        
        # No more active projects, stop the animation
        if self.state == AnimationState.CYCLING:
            self.logger.info(f"Stopping pipeline animation for project {project_id}")
            self.state = AnimationState.STOPPING
            
            # Cancel the cycling task
            if self._cycle_task and not self._cycle_task.done():
                self._cycle_task.cancel()
            
            # Return to idle image
            self._return_to_idle()
            return True
        
        return False
    
    def force_stop(self) -> None:
        """Force stop all animation regardless of active projects."""
        self.logger.info("Force stopping pipeline animation")
        self._active_project_ids.clear()
        
        if self.state == AnimationState.CYCLING:
            self.state = AnimationState.STOPPING
            
            if self._cycle_task and not self._cycle_task.done():
                self._cycle_task.cancel()
            
            self._return_to_idle()
    
    def is_animating(self) -> bool:
        """Check if animation is currently active.
        
        Returns:
            bool: True if currently cycling images
        """
        return self.state == AnimationState.CYCLING
    
    def get_active_projects(self) -> set:
        """Get the set of active project IDs.
        
        Returns:
            set: Set of project IDs with active pipeline animations
        """
        return self._active_project_ids.copy()
    
    async def _cycle_images(self) -> None:
        """Internal method to cycle through review images."""
        try:
            self.logger.debug("Starting image cycling loop")
            
            while self.state == AnimationState.CYCLING:
                # Get current image
                current_image = self.review_images[self._current_image_index]
                
                # Change to current image
                if self._change_image_callback:
                    success = self._change_image_callback(current_image)
                    if not success:
                        self.logger.warning(f"Failed to change to image: {current_image}")
                
                # Move to next image
                self._current_image_index = (self._current_image_index + 1) % len(self.review_images)
                
                # Wait for next cycle
                try:
                    await asyncio.sleep(self.cycle_interval)
                except asyncio.CancelledError:
                    self.logger.debug("Image cycling cancelled")
                    break
                    
        except Exception as e:
            self.logger.error(f"Error in image cycling: {str(e)}")
        finally:
            self.logger.debug("Image cycling loop ended")
            self.state = AnimationState.IDLE
    
    def _return_to_idle(self) -> None:
        """Return to the idle image."""
        if self._change_image_callback:
            success = self._change_image_callback(self.idle_image)
            if success:
                self.logger.info(f"Returned to idle image: {self.idle_image}")
                self.state = AnimationState.IDLE
            else:
                self.logger.warning(f"Failed to return to idle image: {self.idle_image}")
        else:
            self.logger.warning("Cannot return to idle: no image change callback set")
    
    def get_status(self) -> dict:
        """Get current animation status.
        
        Returns:
            dict: Status information about the animation manager
        """
        return {
            "state": self.state.value,
            "active_projects": list(self._active_project_ids),
            "cycle_interval": self.cycle_interval,
            "current_image_index": self._current_image_index,
            "review_images": self.review_images.copy(),
            "idle_image": self.idle_image,
            "has_callback": self._change_image_callback is not None,
            "task_running": self._cycle_task is not None and not self._cycle_task.done()
        } 