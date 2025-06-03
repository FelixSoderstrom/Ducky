"""Image management utilities for the Ducky UI."""

import os
import logging
from typing import Optional, Tuple
from PIL import Image, ImageTk

logger = logging.getLogger("ducky.ui.image_manager")


class ImageManager:
    """Manages image loading, resizing, and display for the Ducky UI."""
    
    def __init__(self):
        self.png_image: Optional[ImageTk.PhotoImage] = None
        self.original_image_path: Optional[str] = None
        self.photo_image: Optional[ImageTk.PhotoImage] = None
        
    def load_image(self, image_name: str = "idle.png") -> None:
        """Load an image from the assets directory.
        
        Args:
            image_name: Name of the image file to load (default: idle.png)
        """
        try:
            # Get the path to the image
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            image_path = os.path.join(current_dir, "assets", image_name)
            
            # Use PIL to load PNG with proper transparency handling
            pil_image = Image.open(image_path).convert('RGBA')
            self.png_image = ImageTk.PhotoImage(pil_image)
            self.original_image_path = image_path
            
            logger.info(f"Successfully loaded image: {image_name}")
            
        except Exception as e:
            logger.warning(f"Error loading image {image_name}: {e}")
            # Create a fallback transparent image if loading fails
            self.png_image = None
            self.original_image_path = None
    
    def update_image_size(self, width: int, height: int) -> ImageTk.PhotoImage:
        """Update the image size to fit the specified dimensions.
        
        Args:
            width: Target width for the image
            height: Target height for the image
            
        Returns:
            ImageTk.PhotoImage: The resized image ready for display
        """
        if self.png_image and self.original_image_path:
            # Load the original PNG and resize with PIL for better quality and transparency
            pil_image = Image.open(self.original_image_path).convert('RGBA')
            resized_image = pil_image.resize((width, height), Image.Resampling.LANCZOS)
            self.photo_image = ImageTk.PhotoImage(resized_image)
                
        elif self.png_image is None:
            # Fallback: create a simple transparent placeholder
            placeholder = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            self.photo_image = ImageTk.PhotoImage(placeholder)
        
        return self.photo_image
    
    def get_current_image(self) -> Optional[ImageTk.PhotoImage]:
        """Get the current processed image.
        
        Returns:
            Optional[ImageTk.PhotoImage]: Current image or None if not loaded
        """
        return self.photo_image
    
    def is_image_loaded(self) -> bool:
        """Check if an image has been successfully loaded.
        
        Returns:
            bool: True if image is loaded, False otherwise
        """
        return self.png_image is not None
    
    def get_image_path(self) -> Optional[str]:
        """Get the path of the currently loaded image.
        
        Returns:
            Optional[str]: Path to the current image file, or None if not loaded
        """
        return self.original_image_path 