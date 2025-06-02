"""Text notification system for code review feedback."""

import logging
import asyncio
import tkinter as tk
from typing import Optional

logger = logging.getLogger("ducky.notifications.text")

# Constants for consistent styling
OVERLAY_CONFIG = {
    'bg': '#2c2c2c',
    'fg': 'white',
    'font': ('Arial', 12, 'bold'),
    'button_font': ('Arial', 9, 'bold'),
    'colors': {
        'dismiss': {'normal': '#d32f2f', 'hover': '#b71c1c'},
        'expand': {'normal': '#388e3c', 'hover': '#2e7d32'}
    },
    'dimensions': {
        'width': 300,
        'height': 160,
        'padding': 10,
        'gap': 10
    }
}


async def display_text_overlay(text: str, ui_app) -> None:
    """
    Display text notification as an overlay on the UI.
    
    Args:
        text: The notification text to display
        ui_app: The DuckyUI application instance
    """
    try:
        logger.info(f"Displaying text overlay: {text[:50]}...")
        
        # Add notification to tracking system and get ID
        notification_id = ui_app.add_unhandled_notification(text)
        
        overlay = TextOverlay(ui_app, text, notification_id, sticky=False)
        overlay.show()
        
        # Mark as seen after initial display (no longer first time)
        ui_app.mark_notification_as_seen(notification_id)
        
        # Auto-hide after 15 seconds
        await asyncio.sleep(15)
        
        # If overlay still exists (wasn't manually dismissed), hide it and mark as unhandled
        if overlay.is_visible():
            overlay.hide()
            logger.info(f"Text notification timed out - notification {notification_id} remains unhandled")
        
    except Exception as e:
        logger.error(f"Failed to display text overlay: {str(e)}")


def show_sticky_text_overlay(text: str, ui_app, notification_id: str) -> None:
    """
    Display a sticky text notification that doesn't auto-hide.
    Used when showing notifications from the notification list.
    
    Args:
        text: The notification text to display
        ui_app: The DuckyUI application instance
        notification_id: The notification ID
    """
    try:
        logger.info(f"Displaying sticky text overlay: {text[:50]}...")
        
        overlay = TextOverlay(ui_app, text, notification_id, sticky=True)
        overlay.show()
        
        logger.info("Sticky text notification displayed - will remain until manually dismissed")
        
    except Exception as e:
        logger.error(f"Failed to display sticky text overlay: {str(e)}")


class TextOverlay:
    """Simplified text overlay widget for displaying notifications."""
    
    def __init__(self, ui_app, text: str, notification_id: str, sticky: bool = False):
        self.ui_app = ui_app
        self.text = text
        self.notification_id = notification_id
        self.sticky = sticky  # If True, notification doesn't auto-hide
        self.window: Optional[tk.Toplevel] = None
        self._update_job: Optional[str] = None
        self._is_visible = False
        
    def show(self) -> None:
        """Show the text overlay positioned to the left of the UI."""
        try:
            self._create_window()
            self._create_content()
            self._position_window()
            self._start_position_tracking()
            self._is_visible = True
            
            logger.info("Text overlay displayed successfully")
            
        except Exception as e:
            logger.error(f"Failed to create text overlay: {str(e)}")
    
    def hide(self) -> None:
        """Hide and destroy the text overlay."""
        try:
            self._stop_position_tracking()
            
            if self.window:
                self.window.destroy()
                self.window = None
            
            self._is_visible = False
            logger.info("Text overlay hidden")
        except Exception as e:
            logger.error(f"Failed to hide text overlay: {str(e)}")
    
    def is_visible(self) -> bool:
        """Check if the overlay is currently visible."""
        return self._is_visible and self.window is not None
    
    def _create_window(self) -> None:
        """Create the overlay window with basic configuration."""
        self.window = tk.Toplevel(self.ui_app.root)
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        
        config = OVERLAY_CONFIG['dimensions']
        self.window.geometry(f"{config['width']}x{config['height']}")
        
        # Main frame
        self.main_frame = tk.Frame(
            self.window,
            bg=OVERLAY_CONFIG['bg'],
            relief='raised',
            borderwidth=1
        )
        self.main_frame.pack(fill='both', expand=True)
    
    def _create_content(self) -> None:
        """Create the content of the overlay (buttons and text)."""
        config = OVERLAY_CONFIG
        
        # Button frame at top
        button_frame = tk.Frame(self.main_frame, bg=config['bg'])
        button_frame.pack(fill='x', padx=config['dimensions']['padding'], 
                         pady=(config['dimensions']['padding'], 5))
        
        # Create buttons
        self._create_button(button_frame, "Dismiss", config['colors']['dismiss'], 
                          self._dismiss, 'left')
        self._create_button(button_frame, "Expand", config['colors']['expand'], 
                          self._expand, 'right')
        
        # Text display
        self._create_text_display()
    
    def _create_button(self, parent: tk.Frame, text: str, colors: dict, 
                      command: callable, side: str) -> None:
        """Create a styled button with hover effects."""
        button = tk.Button(
            parent,
            text=text,
            bg=colors['normal'],
            fg=OVERLAY_CONFIG['fg'],
            font=OVERLAY_CONFIG['button_font'],
            relief='flat',
            padx=10,
            pady=3,
            command=command,
            cursor='hand2'
        )
        
        padding = (0, 5) if side == 'left' else (5, 0)
        button.pack(side=side, padx=padding)
        
        # Add hover effects
        button.bind('<Enter>', lambda e: button.config(bg=colors['hover']))
        button.bind('<Leave>', lambda e: button.config(bg=colors['normal']))
    
    def _create_text_display(self) -> None:
        """Create the text display area with scrolling if needed."""
        config = OVERLAY_CONFIG
        text_frame = tk.Frame(self.main_frame, bg=config['bg'])
        text_frame.pack(fill='both', expand=True, 
                       padx=config['dimensions']['padding'], 
                       pady=(0, config['dimensions']['padding']))
        
        # Create text widget with scrollbar
        self.text_widget = tk.Text(
            text_frame,
            bg=config['bg'],
            fg=config['fg'],
            font=config['font'],
            wrap='word',
            relief='flat',
            borderwidth=0,
            highlightthickness=0,
            padx=15,
            pady=10,
            state='normal'
        )
        
        scrollbar = tk.Scrollbar(
            text_frame,
            orient='vertical',
            command=self.text_widget.yview,
            bg='#404040',
            troughcolor=config['bg'],
            activebackground='#606060',
            width=12
        )
        
        self.text_widget.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        scrollbar.pack(side='right', fill='y')
        self.text_widget.pack(side='left', fill='both', expand=True)
        
        # Insert text and make read-only
        self.text_widget.insert('1.0', self.text)
        self.text_widget.configure(state='disabled', insertwidth=0)
    
    def _position_window(self) -> None:
        """Position the overlay intelligently based on available screen space."""
        try:
            self.ui_app.root.update_idletasks()
            
            # Get UI position and dimensions
            ui_x = self.ui_app.root.winfo_x()
            ui_y = self.ui_app.root.winfo_y()
            ui_width = self.ui_app.root.winfo_width()
            
            # Get screen dimensions
            screen_width = self.ui_app.root.winfo_screenwidth()
            
            config = OVERLAY_CONFIG['dimensions']
            overlay_width = config['width']
            gap = config['gap']
            
            # Check if there's space on the left for the overlay
            space_on_left = ui_x
            space_needed_on_left = overlay_width + gap + 10  # Extra margin for safety
            
            # Check if there's space on the right for the overlay
            space_on_right = screen_width - (ui_x + ui_width)
            space_needed_on_right = overlay_width + gap + 10  # Extra margin for safety
            
            # Determine positioning based on available space
            if space_on_left >= space_needed_on_left:
                # Position on the left (preferred)
                overlay_x = ui_x - overlay_width - gap
                position_side = "left"
            elif space_on_right >= space_needed_on_right:
                # Position on the right (fallback)
                overlay_x = ui_x + ui_width + gap
                position_side = "right"
            else:
                # If neither side has enough space, try to position on the side with more space
                if space_on_left > space_on_right:
                    # Force on left with reduced gap
                    overlay_x = max(10, ui_x - overlay_width - 5)
                    position_side = "left (forced)"
                else:
                    # Force on right with reduced gap
                    overlay_x = min(screen_width - overlay_width - 10, ui_x + ui_width + 5)
                    position_side = "right (forced)"
            
            overlay_y = ui_y
            
            # Apply positioning
            self.window.geometry(f"{overlay_width}x{config['height']}+{overlay_x}+{overlay_y}")
            
            logger.debug(f"Positioned overlay on {position_side} side at ({overlay_x}, {overlay_y})")
            
        except Exception as e:
            logger.error(f"Failed to position overlay: {str(e)}")
            # Fallback to simple left positioning
            try:
                ui_x = self.ui_app.root.winfo_x()
                ui_y = self.ui_app.root.winfo_y()
                config = OVERLAY_CONFIG['dimensions']
                overlay_x = max(10, ui_x - config['width'] - config['gap'])
                self.window.geometry(f"{config['width']}x{config['height']}+{overlay_x}+{ui_y}")
            except:
                pass
    
    def _start_position_tracking(self) -> None:
        """Start tracking UI movement to keep overlay positioned correctly."""
        self._last_ui_pos = (self.ui_app.root.winfo_x(), self.ui_app.root.winfo_y())
        self._check_position()
    
    def _stop_position_tracking(self) -> None:
        """Stop tracking UI movement."""
        if self._update_job:
            try:
                self.ui_app.root.after_cancel(self._update_job)
            except:
                pass
            self._update_job = None
    
    def _check_position(self) -> None:
        """Check if UI has moved and update overlay position accordingly."""
        if not self.window:
            return
            
        try:
            current_pos = (self.ui_app.root.winfo_x(), self.ui_app.root.winfo_y())
            
            if current_pos != self._last_ui_pos:
                self._position_window()
                self._last_ui_pos = current_pos
            
            # Schedule next check
            self._update_job = self.ui_app.root.after(50, self._check_position)
            
        except Exception as e:
            logger.error(f"Error updating overlay position: {str(e)}")
    
    def _dismiss(self) -> None:
        """Handle dismiss button click."""
        logger.info("Dismiss button clicked - removing from unhandled notifications")
        
        # Remove from unhandled notifications since user actively dismissed it
        self.ui_app.remove_unhandled_notification(self.notification_id)
        
        self.hide()
    
    def _expand(self) -> None:
        """Handle expand button click - placeholder for future functionality."""
        logger.info("Expand button clicked - removing from unhandled notifications")
        
        # For now, treat expand as dismiss (remove from unhandled notifications)
        self.ui_app.remove_unhandled_notification(self.notification_id)
        
        logger.info("Expand functionality not implemented yet - notification marked as handled")
        # TODO: Implement expand functionality 