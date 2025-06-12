"""Notification list dialog for displaying unhandled notifications."""

import tkinter as tk
from tkinter import ttk
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Callable

logger = logging.getLogger("ducky.ui.notification_list")

class NotificationListDialog:
    """Dialog that displays a list of unhandled notifications with time elapsed."""
    
    def __init__(self, ui_app):
        self.ui_app = ui_app
        self.window: Optional[tk.Toplevel] = None
        self.notification_items: List[Tuple[str, str, str]] = []  # (id, time_text, preview)
        self._update_job: Optional[str] = None
        self._last_ui_pos: Optional[Tuple[int, int]] = None
        self._last_ui_size: Optional[Tuple[int, int]] = None
        self.close_callback: Optional[Callable] = None  # Callback for when dialog is closed
        
    def show(self) -> None:
        """Show the notification list dialog."""
        try:
            self._create_window()
            self._populate_notifications()
            self._create_content()
            self._position_window()
            self._start_position_tracking()
            
            logger.info("Notification list dialog displayed")
            
        except Exception as e:
            logger.error(f"Failed to show notification list dialog: {str(e)}")
    
    def hide(self) -> None:
        """Hide and destroy the notification list dialog."""
        self._stop_position_tracking()
        
        if self.window:
            self.window.destroy()
            self.window = None
            logger.info("Notification list dialog hidden")
        
        # Notify the callback that dialog was closed
        if self.close_callback:
            try:
                self.close_callback()
            except Exception as e:
                logger.error(f"Error in dialog close callback: {str(e)}")
    
    def _create_window(self) -> None:
        """Create the dialog window."""
        self.window = tk.Toplevel(self.ui_app.root)
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        
        # Window dimensions
        width = 280
        height = min(400, max(150, len(self.ui_app.unhandled_notifications) * 60 + 80))
        self.window.geometry(f"{width}x{height}")
        
        # Main frame with dark styling
        self.main_frame = tk.Frame(
            self.window,
            bg='#2c2c2c',
            relief='raised',
            borderwidth=2
        )
        self.main_frame.pack(fill='both', expand=True)
    
    def _populate_notifications(self) -> None:
        """Populate the notification items list with time formatting."""
        self.notification_items = []
        
        # Sort notifications by timestamp (newest first)
        sorted_notifications = sorted(
            self.ui_app.unhandled_notifications.values(),
            key=lambda x: x['timestamp'],
            reverse=True
        )
        
        now = datetime.now()
        
        for notification in sorted_notifications:
            notification_id = notification['id']
            timestamp = notification['timestamp']
            text = notification['text']
            
            # Calculate time elapsed
            time_elapsed = now - timestamp
            time_text = self._format_time_elapsed(time_elapsed)
            
            # Create preview text (first 40 characters)
            preview = text[:40] + "..." if len(text) > 40 else text
            
            self.notification_items.append((notification_id, time_text, preview))
    
    def _format_time_elapsed(self, time_elapsed: timedelta) -> str:
        """Format time elapsed into human readable format."""
        total_seconds = int(time_elapsed.total_seconds())
        
        if total_seconds < 60:
            return "less than 1 min ago"
        elif total_seconds < 3600:  # Less than 1 hour
            minutes = total_seconds // 60
            return f"{minutes} min ago"
        elif total_seconds < 86400:  # Less than 1 day
            hours = total_seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        else:  # 1 day or more
            days = total_seconds // 86400
            return f"{days} day{'s' if days > 1 else ''} ago"
    
    def _create_content(self) -> None:
        """Create the dialog content."""
        # Header
        header_frame = tk.Frame(self.main_frame, bg='#2c2c2c')
        header_frame.pack(fill='x', padx=10, pady=(10, 5))
        
        title_label = tk.Label(
            header_frame,
            text="Unhandled Notifications",
            bg='#2c2c2c',
            fg='white',
            font=('Arial', 12, 'bold')
        )
        title_label.pack(side='left')
        
        close_button = tk.Button(
            header_frame,
            text="×",
            bg='#d32f2f',
            fg='white',
            font=('Arial', 12, 'bold'),
            relief='flat',
            padx=8,
            pady=2,
            command=self.hide,
            cursor='hand2'
        )
        close_button.pack(side='right')
        
        # Add hover effect for close button
        close_button.bind('<Enter>', lambda e: close_button.config(bg='#b71c1c'))
        close_button.bind('<Leave>', lambda e: close_button.config(bg='#d32f2f'))
        
        # Notifications list
        if not self.notification_items:
            # No notifications
            no_notif_label = tk.Label(
                self.main_frame,
                text="No unhandled notifications",
                bg='#2c2c2c',
                fg='#888888',
                font=('Arial', 10)
            )
            no_notif_label.pack(pady=20)
        else:
            # Create scrollable list
            self._create_scrollable_list()
    
    def _create_scrollable_list(self) -> None:
        """Create scrollable list of notifications."""
        # Frame for scrollable content
        list_frame = tk.Frame(self.main_frame, bg='#2c2c2c')
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Create canvas and scrollbar for scrolling
        canvas = tk.Canvas(
            list_frame,
            bg='#2c2c2c',
            highlightthickness=0,
            borderwidth=0
        )
        scrollbar = tk.Scrollbar(
            list_frame,
            orient='vertical',
            command=canvas.yview,
            bg='#404040',
            troughcolor='#2c2c2c',
            activebackground='#606060'
        )
        scrollable_frame = tk.Frame(canvas, bg='#2c2c2c')
        
        # Configure scrolling
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Add notification items
        for i, (notification_id, time_text, preview) in enumerate(self.notification_items):
            self._create_notification_item(scrollable_frame, notification_id, time_text, preview, i)
    
    def _create_notification_item(self, parent: tk.Frame, notification_id: str, 
                                time_text: str, preview: str, index: int) -> None:
        """Create a single notification item in the list."""
        # Item frame
        item_frame = tk.Frame(
            parent,
            bg='#404040',
            relief='flat',
            borderwidth=1,
            cursor='hand2'
        )
        item_frame.pack(fill='x', pady=2, padx=2)
        
        # Time label
        time_label = tk.Label(
            item_frame,
            text=time_text,
            bg='#404040',
            fg='#bbbbbb',
            font=('Arial', 9, 'bold'),
            cursor='hand2'
        )
        time_label.pack(anchor='w', padx=8, pady=(6, 2))
        
        # Preview label
        preview_label = tk.Label(
            item_frame,
            text=preview,
            bg='#404040',
            fg='white',
            font=('Arial', 9),
            wraplength=250,
            justify='left',
            cursor='hand2'
        )
        preview_label.pack(anchor='w', padx=8, pady=(0, 6))
        
        # Bind click events to all parts of the item
        for widget in [item_frame, time_label, preview_label]:
            widget.bind('<Button-1>', lambda e, nid=notification_id: self._on_notification_click(nid))
            widget.bind('<Enter>', lambda e, frame=item_frame: frame.config(bg='#505050'))
            widget.bind('<Leave>', lambda e, frame=item_frame: frame.config(bg='#404040'))
    
    def _on_notification_click(self, notification_id: str) -> None:
        """Handle clicking on a notification item."""
        logger.info(f"Notification clicked: {notification_id}")
        
        # Get notification data
        notification_data = self.ui_app.get_notification_by_id(notification_id)
        if not notification_data:
            logger.error(f"Notification not found: {notification_id}")
            return
        
        # Mark as seen (no longer first time)
        self.ui_app.mark_notification_as_seen(notification_id)
        
        # Hide the list dialog
        self.hide()
        
        # Show the text notification in sticky mode
        try:
            from src.notifications.text_notification import show_sticky_text_overlay
            show_sticky_text_overlay(notification_data['text'], self.ui_app, notification_id)
        except ImportError:
            logger.error("show_sticky_text_overlay function not implemented yet")
        except Exception as e:
            logger.error(f"Failed to show sticky notification: {str(e)}")
    
    def _position_window(self) -> None:
        """Position the dialog relative to the UI."""
        try:
            self.ui_app.root.update_idletasks()
            
            # Get UI position and dimensions
            ui_x = self.ui_app.root.winfo_x()
            ui_y = self.ui_app.root.winfo_y()
            ui_width = self.ui_app.root.winfo_width()
            ui_height = self.ui_app.root.winfo_height()
            
            # Get dialog dimensions
            dialog_width = self.window.winfo_reqwidth()
            dialog_height = self.window.winfo_reqheight()
            
            # Get screen dimensions
            screen_width = self.ui_app.root.winfo_screenwidth()
            
            # Position to the right of the UI with some spacing
            gap = 10
            dialog_x = ui_x + ui_width + gap
            dialog_y = ui_y
            
            # Make sure it fits on screen
            if dialog_x + dialog_width > screen_width:
                # Position to the left instead
                dialog_x = ui_x - dialog_width - gap
                if dialog_x < 0:
                    # If neither side has enough space, force it to the left with minimal gap
                    dialog_x = max(10, ui_x - dialog_width - 5)
            
            self.window.geometry(f"{dialog_width}x{dialog_height}+{dialog_x}+{dialog_y}")
            
            logger.debug(f"Positioned notification list dialog at ({dialog_x}, {dialog_y})")
            
        except Exception as e:
            logger.error(f"Failed to position notification list dialog: {str(e)}")
    
    def _start_position_tracking(self) -> None:
        """Start tracking UI movement to keep dialog positioned correctly."""
        if not self.window:
            return
            
        self._last_ui_pos = (self.ui_app.root.winfo_x(), self.ui_app.root.winfo_y())
        self._last_ui_size = (self.ui_app.root.winfo_width(), self.ui_app.root.winfo_height())
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
        """Check if UI has moved or resized and update dialog position accordingly."""
        if not self.window:
            return
            
        try:
            current_pos = (self.ui_app.root.winfo_x(), self.ui_app.root.winfo_y())
            current_size = (self.ui_app.root.winfo_width(), self.ui_app.root.winfo_height())
            
            # Check if position or size changed
            pos_changed = current_pos != self._last_ui_pos
            size_changed = current_size != self._last_ui_size
            
            if pos_changed or size_changed:
                self._position_window()
                self._last_ui_pos = current_pos
                self._last_ui_size = current_size
                
                if pos_changed and size_changed:
                    logger.debug(f"Updated notification list position due to UI movement and resize")
                elif pos_changed:
                    logger.debug(f"Updated notification list position due to UI movement")
                elif size_changed:
                    logger.debug(f"Updated notification list position due to UI resize")
            
            # Schedule next check
            self._update_job = self.ui_app.root.after(50, self._check_position)
            
        except Exception as e:
            logger.error(f"Error updating notification list position: {str(e)}")
            # Stop tracking on error to prevent spam
            self._stop_position_tracking()
    
    def set_close_callback(self, callback: Callable) -> None:
        """Set callback function to be called when dialog is closed.
        
        Args:
            callback: Function to call when dialog is closed
        """
        self.close_callback = callback 