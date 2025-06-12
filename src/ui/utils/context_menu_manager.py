"""Context menu management utilities for the Ducky UI."""

import tkinter as tk
import logging
from typing import Callable, Optional

logger = logging.getLogger("ducky.ui.context_menu")


class ContextMenuManager:
    """Manages context menu creation and display for the Ducky UI."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.context_menu: Optional[tk.Menu] = None
        self.settings_callback: Optional[Callable] = None
        
    def setup_context_menu(self, settings_callback: Callable) -> None:
        """Set up the context menu for the UI.
        
        Args:
            settings_callback: Function to call when settings menu item is clicked
        """
        self.settings_callback = settings_callback
        
        # Create context menu
        self.context_menu = tk.Menu(
            self.root, 
            tearoff=0, 
            bg='#2c2c2c', 
            fg='white', 
            font=('Arial', 10), 
            relief='flat', 
            bd=1
        )
        self.context_menu.add_command(label="Settings", command=self._handle_settings_click)
        
        # Configure context menu appearance
        self.context_menu.config(
            activebackground='#404040',
            activeforeground='white',
            selectcolor='white'
        )
        
        logger.info("Context menu setup completed")
    
    def bind_context_menu(self, widget: tk.Widget) -> None:
        """Bind right-click context menu to a widget.
        
        Args:
            widget: Widget to bind the context menu to
        """
        widget.bind("<Button-3>", self._show_context_menu)
        logger.debug(f"Context menu bound to {widget}")
    
    def _show_context_menu(self, event) -> None:
        """Show the context menu at the cursor position.
        
        Args:
            event: The mouse event that triggered the context menu
        """
        if not self.context_menu:
            logger.warning("Context menu not initialized")
            return
            
        try:
            # Show the context menu at the event position
            self.context_menu.post(event.x_root, event.y_root)
            logger.debug(f"Context menu displayed at ({event.x_root}, {event.y_root})")
        except Exception as e:
            logger.error(f"Failed to show context menu: {str(e)}")
        finally:
            # Make sure to grab release when context menu is closed
            self.context_menu.grab_release()
    
    def _handle_settings_click(self) -> None:
        """Handle settings menu item click."""
        if self.settings_callback:
            try:
                self.settings_callback()
                logger.info("Settings callback executed from context menu")
            except Exception as e:
                logger.error(f"Error in settings callback: {str(e)}")
        else:
            logger.warning("No settings callback configured")
    
    def add_menu_item(self, label: str, command: Callable, separator_before: bool = False) -> None:
        """Add a custom menu item to the context menu.
        
        Args:
            label: Text label for the menu item
            command: Function to call when menu item is clicked
            separator_before: Whether to add a separator before this item
        """
        if not self.context_menu:
            logger.warning("Context menu not initialized")
            return
            
        if separator_before:
            self.context_menu.add_separator()
            
        self.context_menu.add_command(label=label, command=command)
        logger.debug(f"Added menu item: {label}")
    
    def destroy(self) -> None:
        """Clean up the context menu."""
        if self.context_menu:
            try:
                self.context_menu.destroy()
                self.context_menu = None
                logger.debug("Context menu destroyed")
            except Exception as e:
                logger.error(f"Error destroying context menu: {str(e)}")
    
    def is_initialized(self) -> bool:
        """Check if the context menu has been initialized.
        
        Returns:
            bool: True if context menu is initialized
        """
        return self.context_menu is not None 