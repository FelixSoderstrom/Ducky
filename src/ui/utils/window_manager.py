"""Window management utilities for the Ducky UI."""

import tkinter as tk
import logging
from typing import Callable, Optional

logger = logging.getLogger("ducky.ui.window_manager")


class WindowManager:
    """Manages window operations like dragging, resizing, and positioning."""
    
    def __init__(self, root: tk.Tk, min_width: int = 80, min_height: int = 80):
        self.root = root
        self.min_width = min_width
        self.min_height = min_height
        
        # State tracking for window operations
        self.start_x = 0
        self.start_y = 0
        self.dragging = False
        self.resizing = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        # Callbacks for when size changes occur
        self.on_size_change: Optional[Callable[[int, int], None]] = None
        
    def set_size_change_callback(self, callback: Callable[[int, int], None]) -> None:
        """Set callback to be called when window size changes.
        
        Args:
            callback: Function to call with (width, height) when size changes
        """
        self.on_size_change = callback
    
    def setup_window_properties(self, width: int, height: int, top_bar_height: int = 20) -> None:
        """Set up basic window properties and initial size.
        
        Args:
            width: Initial width
            height: Initial height
            top_bar_height: Height of the top bar
        """
        # Remove window decorations and set always on top
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        
        # Make only the main content area transparent, not the top bar
        self.root.attributes('-transparentcolor', '')  # Initially no transparency
        
        # Set initial size and position
        total_height = height + top_bar_height
        self.root.geometry(f"{width}x{total_height}+100+100")
        
        logger.info(f"Window properties set: {width}x{total_height}")
    
    def bind_drag_events(self, widgets: list) -> None:
        """Bind dragging events to specified widgets.
        
        Args:
            widgets: List of widgets that should enable window dragging
        """
        for widget in widgets:
            widget.bind("<Button-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._on_drag)
            widget.bind("<ButtonRelease-1>", self._stop_drag)
        
        logger.debug(f"Drag events bound to {len(widgets)} widgets")
    
    def bind_resize_events(self, resize_widget: tk.Widget) -> None:
        """Bind resizing events to the resize handle widget.
        
        Args:
            resize_widget: Widget that acts as the resize handle
        """
        resize_widget.bind("<Button-1>", self._start_resize)
        resize_widget.bind("<B1-Motion>", self._on_resize)
        resize_widget.bind("<ButtonRelease-1>", self._stop_resize)
        
        logger.debug("Resize events bound to resize handle")
    
    def _start_drag(self, event) -> None:
        """Start dragging the window."""
        if not self.resizing and hasattr(event.widget, 'winfo_name'):
            # Prevent dragging on certain widgets
            widget_name = event.widget.winfo_name()
            if 'resize' in widget_name or 'exit' in widget_name:
                return
                
        self.dragging = True
        self.start_x = event.x_root
        self.start_y = event.y_root
        # Store the initial window position
        self.drag_start_x = self.root.winfo_x()
        self.drag_start_y = self.root.winfo_y()
        
        logger.debug(f"Started dragging at ({event.x_root}, {event.y_root})")
    
    def _on_drag(self, event) -> None:
        """Handle window dragging."""
        if self.dragging and not self.resizing:
            # Calculate the change in position
            dx = event.x_root - self.start_x
            dy = event.y_root - self.start_y
            
            # Update window position
            new_x = self.drag_start_x + dx
            new_y = self.drag_start_y + dy
            
            # Get current geometry to preserve size
            geometry = self.root.geometry()
            size_part = geometry.split('+')[0]  # Get WIDTHxHEIGHT part
            
            # Move the window without changing its size
            self.root.geometry(f"{size_part}+{new_x}+{new_y}")
    
    def _stop_drag(self, event) -> None:
        """Stop dragging the window."""
        if self.dragging:
            logger.debug("Stopped dragging")
        self.dragging = False
    
    def _start_resize(self, event) -> None:
        """Start resizing the window."""
        self.resizing = True
        self.start_x = event.x_root
        self.start_y = event.y_root
        
        logger.debug(f"Started resizing at ({event.x_root}, {event.y_root})")
    
    def _on_resize(self, event) -> None:
        """Handle window resizing."""
        if self.resizing:
            # Calculate the change in position (fixed for top-left resize)
            dx = self.start_x - event.x_root
            dy = self.start_y - event.y_root
            
            # Use the larger of the dimensions to maintain square aspect ratio
            delta = max(dx, dy)
            
            # Get current size from geometry
            geometry = self.root.geometry()
            size_part, pos_part = geometry.split('+', 1)
            current_width, current_height = map(int, size_part.split('x'))
            
            # Calculate new size (respecting minimum size)
            # Assume square image area, so we work with the smaller dimension
            current_image_size = min(current_width, current_height - 20)  # Assume 20px top bar
            new_size = max(self.min_width, current_image_size + delta)
            
            # Update window position to resize from top-left
            x = self.root.winfo_x() - delta
            y = self.root.winfo_y() - delta
            
            # Total height includes top bar (assume 20px)
            total_height = new_size + 20
            
            # Apply new geometry
            self.root.geometry(f"{new_size}x{total_height}+{x}+{y}")
            
            # Notify callback about size change
            if self.on_size_change:
                self.on_size_change(new_size, new_size)
            
            # Update start position for next movement
            self.start_x = event.x_root
            self.start_y = event.y_root
    
    def _stop_resize(self, event) -> None:
        """Stop resizing the window."""
        if self.resizing:
            logger.debug("Stopped resizing")
        self.resizing = False
    
    def is_dragging(self) -> bool:
        """Check if window is currently being dragged.
        
        Returns:
            bool: True if currently dragging
        """
        return self.dragging
    
    def is_resizing(self) -> bool:
        """Check if window is currently being resized.
        
        Returns:
            bool: True if currently resizing
        """
        return self.resizing 