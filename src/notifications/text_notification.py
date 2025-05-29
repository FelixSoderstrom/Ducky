"""Text notification system for code review feedback."""

import logging
import asyncio
import tkinter as tk
from typing import Optional

logger = logging.getLogger("ducky.notifications.text")


async def display_text_overlay(text: str, ui_app) -> None:
    """
    Display text notification as an overlay on the UI.
    
    Args:
        text: The notification text to display
        ui_app: The DuckyUI application instance
    """
    try:
        logger.info(f"Displaying text overlay: {text[:50]}...")
        
        # Create overlay in the UI
        overlay = TextOverlay(ui_app, text)
        overlay.show()
        
        # Auto-hide after 10 seconds
        await asyncio.sleep(10)
        overlay.hide()
        
    except Exception as e:
        logger.error(f"Failed to display text overlay: {str(e)}")


class TextOverlay:
    """Text overlay widget for displaying notifications on the UI."""
    
    def __init__(self, ui_app, text: str):
        self.ui_app = ui_app
        self.text = text
        self.overlay_frame: Optional[tk.Frame] = None
        self.overlay_label: Optional[tk.Label] = None
        
    def show(self) -> None:
        """Show the text overlay on the UI."""
        try:
            # Create overlay frame
            self.overlay_frame = tk.Frame(
                self.ui_app.root,
                bg='#2c2c2c',
                relief='raised',
                borderwidth=2
            )
            
            # Create the text label
            self.overlay_label = tk.Label(
                self.overlay_frame,
                text=self.text,
                bg='#2c2c2c',
                fg='white',
                font=('Arial', 10, 'bold'),
                wraplength=250,  # Wrap text to fit overlay
                justify='left',
                padx=10,
                pady=5
            )
            self.overlay_label.pack(fill='both', expand=True)
            
            # Position overlay at the bottom of the UI
            self._position_overlay()
            
            # Add click handler to dismiss
            self.overlay_frame.bind('<Button-1>', lambda e: self.hide())
            self.overlay_label.bind('<Button-1>', lambda e: self.hide())
            
            logger.info("Text overlay displayed successfully")
            
        except Exception as e:
            logger.error(f"Failed to create text overlay: {str(e)}")
    
    def hide(self) -> None:
        """Hide and destroy the text overlay."""
        try:
            if self.overlay_frame:
                self.overlay_frame.destroy()
                self.overlay_frame = None
                self.overlay_label = None
                logger.info("Text overlay hidden")
        except Exception as e:
            logger.error(f"Failed to hide text overlay: {str(e)}")
    
    def _position_overlay(self) -> None:
        """Position the overlay at the bottom of the UI window."""
        try:
            # Update the UI to get current dimensions
            self.ui_app.root.update_idletasks()
            
            # Get current window position and size
            ui_x = self.ui_app.root.winfo_x()
            ui_y = self.ui_app.root.winfo_y()
            ui_width = self.ui_app.root.winfo_width()
            ui_height = self.ui_app.root.winfo_height()
            
            # Calculate overlay dimensions (wrap text and measure)
            self.overlay_label.update_idletasks()
            overlay_width = min(ui_width, 280)  # Max width of 280px or UI width
            overlay_height = self.overlay_label.winfo_reqheight() + 20  # Add padding
            
            # Position overlay below the UI window
            overlay_x = ui_x
            overlay_y = ui_y + ui_height + 5  # 5px gap below UI
            
            # Place the overlay
            self.overlay_frame.place(
                x=0, y=0,  # Will be repositioned by geometry
                width=overlay_width,
                height=overlay_height
            )
            
            # Set overlay window geometry to position it correctly
            self.overlay_frame.place_forget()  # Remove place first
            
            # Use a separate toplevel window for the overlay
            self._create_overlay_window(overlay_x, overlay_y, overlay_width, overlay_height)
            
        except Exception as e:
            logger.error(f"Failed to position overlay: {str(e)}")
    
    def _create_overlay_window(self, x: int, y: int, width: int, height: int) -> None:
        """Create a separate overlay window positioned relative to the main UI."""
        try:
            # Destroy the frame we created earlier
            if self.overlay_frame:
                self.overlay_frame.destroy()
            
            # Create a new toplevel window for the overlay
            self.overlay_window = tk.Toplevel(self.ui_app.root)
            self.overlay_window.overrideredirect(True)  # Remove window decorations
            self.overlay_window.attributes('-topmost', True)  # Keep on top
            self.overlay_window.geometry(f"{width}x{height}+{x}+{y}")
            
            # Create the frame in the new window
            self.overlay_frame = tk.Frame(
                self.overlay_window,
                bg='#2c2c2c',
                relief='raised',
                borderwidth=2
            )
            self.overlay_frame.pack(fill='both', expand=True)
            
            # Recreate the label in the new frame
            self.overlay_label = tk.Label(
                self.overlay_frame,
                text=self.text,
                bg='#2c2c2c',
                fg='white',
                font=('Arial', 10, 'bold'),
                wraplength=width - 20,  # Account for padding
                justify='left',
                padx=10,
                pady=5
            )
            self.overlay_label.pack(fill='both', expand=True)
            
            # Add click handlers
            self.overlay_window.bind('<Button-1>', lambda e: self.hide())
            self.overlay_frame.bind('<Button-1>', lambda e: self.hide())
            self.overlay_label.bind('<Button-1>', lambda e: self.hide())
            
        except Exception as e:
            logger.error(f"Failed to create overlay window: {str(e)}")
    
    def hide(self) -> None:
        """Hide and destroy the text overlay."""
        try:
            if hasattr(self, 'overlay_window') and self.overlay_window:
                self.overlay_window.destroy()
                self.overlay_window = None
            if self.overlay_frame:
                self.overlay_frame.destroy()
                self.overlay_frame = None
                self.overlay_label = None
            logger.info("Text overlay hidden")
        except Exception as e:
            logger.error(f"Failed to hide text overlay: {str(e)}") 