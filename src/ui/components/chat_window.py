"""Chat window UI component for conversational code review discussions."""

import logging
import tkinter as tk
from typing import Optional, Callable, List, Dict, Any
from datetime import datetime

from ..utils.notification_styles import OVERLAY_CONFIG

logger = logging.getLogger("ducky.ui.components.chat_window")

# Chat window specific configuration
CHAT_CONFIG = {
    'bg': OVERLAY_CONFIG['bg'],
    'fg': OVERLAY_CONFIG['fg'],
    'font': OVERLAY_CONFIG['font'],
    'button_font': OVERLAY_CONFIG['button_font'],
    'colors': {
        'close': {'normal': '#d32f2f', 'hover': '#b71c1c'},
        'send': {'normal': '#1976d2', 'hover': '#1565c0'},
        'user_bubble': '#1976d2',
        'ducky_bubble': '#388e3c',
        'input_bg': '#3c3c3c',
        'typing': '#666666'
    },
    'dimensions': {
        'width': 500,
        'height': 600,
        'padding': 15,
        'gap': 10,
        'bubble_padding': 10,
        'max_bubble_width': 300
    }
}


class ChatWindow:
    """Pure UI component for chat interface with Ducky."""
    
    def __init__(self, parent_root: tk.Tk, 
                 on_message_send: Optional[Callable[[str], None]] = None,
                 on_close: Optional[Callable[[], None]] = None):
        """
        Initialize the chat window component.
        
        Args:
            parent_root: The parent tkinter root window
            on_message_send: Callback when user sends a message
            on_close: Callback when chat window is closed
        """
        self.parent_root = parent_root
        self.on_message_send = on_message_send
        self.on_close = on_close
        self.window: Optional[tk.Toplevel] = None
        self.messages: List[Dict[str, Any]] = []
        self._is_visible = False
        self._typing_indicator_visible = False
        
        # Dragging functionality
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._is_dragging = False
        
        # UI components
        self.messages_frame: Optional[tk.Frame] = None
        self.input_var: Optional[tk.StringVar] = None
        self.input_entry: Optional[tk.Entry] = None
        self.send_button: Optional[tk.Button] = None
        self.typing_label: Optional[tk.Label] = None
        
    def show(self) -> None:
        """Show the chat window."""
        try:
            self._create_window()
            self._create_header()
            self._create_messages_area()
            self._create_input_area()
            self._position_window()
            self._is_visible = True
            
            # Focus on input field
            if self.input_entry:
                self.input_entry.focus_set()
            
            logger.info("Chat window displayed successfully")
            
        except Exception as e:
            logger.error(f"Failed to create chat window: {str(e)}")
    
    def hide(self) -> None:
        """Hide and destroy the chat window."""
        try:
            if self.window:
                self.window.destroy()
                self.window = None
            
            self._is_visible = False
            logger.info("Chat window hidden")
        except Exception as e:
            logger.error(f"Failed to hide chat window: {str(e)}")
    
    def is_visible(self) -> bool:
        """Check if the chat window is currently visible."""
        return self._is_visible and self.window is not None
    
    def add_message(self, sender: str, content: str, timestamp: datetime = None) -> None:
        """Add a message to the chat window."""
        if not timestamp:
            timestamp = datetime.now()
        
        message = {
            'id': f"{sender}_{len(self.messages)}_{timestamp.timestamp()}",
            'sender': sender,
            'content': content,
            'timestamp': timestamp,
            'status': 'delivered'
        }
        
        self.messages.append(message)
        self._display_message(message)
        logger.info(f"Added {sender} message: {content[:50]}...")
    
    def show_typing_indicator(self) -> None:
        """Show typing indicator when Ducky is responding."""
        if self.typing_label and not self._typing_indicator_visible:
            self.typing_label.config(text="🦆 Ducky is typing...")
            self.typing_label.pack(side='bottom', pady=(5, 0))
            self._typing_indicator_visible = True
            self._scroll_to_bottom()
    
    def hide_typing_indicator(self) -> None:
        """Hide typing indicator."""
        if self.typing_label and self._typing_indicator_visible:
            self.typing_label.pack_forget()
            self._typing_indicator_visible = False
    
    def _create_window(self) -> None:
        """Create the chat window with basic configuration."""
        self.window = tk.Toplevel(self.parent_root)
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        
        config = CHAT_CONFIG['dimensions']
        self.window.geometry(f"{config['width']}x{config['height']}")
        
        # Main frame
        self.main_frame = tk.Frame(
            self.window,
            bg=CHAT_CONFIG['bg'],
            relief='raised',
            borderwidth=1
        )
        self.main_frame.pack(fill='both', expand=True)
    
    def _create_header(self) -> None:
        """Create the header with title and close button."""
        header_frame = tk.Frame(self.main_frame, bg=CHAT_CONFIG['bg'])
        header_frame.pack(fill='x', padx=CHAT_CONFIG['dimensions']['padding'], 
                         pady=(CHAT_CONFIG['dimensions']['padding'], 5))
        
        # Title (make it draggable)
        title_label = tk.Label(
            header_frame,
            text="💬 Chat with Ducky",
            bg=CHAT_CONFIG['bg'],
            fg=CHAT_CONFIG['fg'],
            font=('Arial', 14, 'bold'),
            cursor='hand2'  # Show hand cursor to indicate draggable
        )
        title_label.pack(side='left')
        
        # Make the title label draggable
        self._make_draggable(title_label)
        
        # Also make the header frame itself draggable
        header_frame.configure(cursor='hand2')
        self._make_draggable(header_frame)
        
        # Close button
        self._create_button(header_frame, "Close", CHAT_CONFIG['colors']['close'], 
                          self._close, 'right')
    
    def _create_messages_area(self) -> None:
        """Create scrollable messages display area."""
        # Container frame
        messages_container = tk.Frame(self.main_frame, bg=CHAT_CONFIG['bg'])
        messages_container.pack(fill='both', expand=True, 
                              padx=CHAT_CONFIG['dimensions']['padding'],
                              pady=(0, 5))
        
        # Create canvas and scrollbar for scrolling
        canvas = tk.Canvas(messages_container, bg=CHAT_CONFIG['bg'], 
                          highlightthickness=0)
        scrollbar = tk.Scrollbar(messages_container, orient='vertical', 
                               command=canvas.yview)
        
        self.messages_frame = tk.Frame(canvas, bg=CHAT_CONFIG['bg'])
        
        # Configure scrolling
        canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas_window = canvas.create_window((0, 0), window=self.messages_frame, anchor='nw')
        
        # Pack components
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        
        # Store references for scrolling
        self.canvas = canvas
        self.scrollbar = scrollbar
        
        # Typing indicator
        self.typing_label = tk.Label(
            self.messages_frame,
            bg=CHAT_CONFIG['bg'],
            fg=CHAT_CONFIG['colors']['typing'],
            font=('Arial', 10, 'italic')
        )
        
        # Update scroll region when frame changes
        self.messages_frame.bind('<Configure>', self._on_frame_configure)
        
        # Configure canvas to update scroll region when it resizes
        canvas.bind('<Configure>', self._on_canvas_configure)
        
        # Add mouse wheel scrolling to key components
        self._bind_mousewheel(self.window)  # Bind to entire window
        self._bind_mousewheel(canvas)
        self._bind_mousewheel(self.messages_frame)
        self._bind_mousewheel(messages_container)
    
    def _bind_mousewheel(self, widget) -> None:
        """Bind mouse wheel scrolling to a widget."""
        def _on_mousewheel(event):
            # Only scroll if we have scrollable content
            if self.canvas.bbox("all"):
                # Much slower scrolling - just 1 unit at a time
                scroll_direction = -1 if event.delta > 0 else 1
                self.canvas.yview_scroll(scroll_direction, "units")
        
        widget.bind("<MouseWheel>", _on_mousewheel)  # Windows
        widget.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))  # Linux
        widget.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))   # Linux
    
    def _on_canvas_configure(self, event) -> None:
        """Update the canvas window width when canvas is resized."""
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)
    
    def _on_frame_configure(self, event) -> None:
        """Update scroll region when messages frame changes."""
        # Update the scroll region to encompass the whole frame
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # Force canvas to update its scrollbar
        self.canvas.update_idletasks()
    
    def _scroll_to_bottom(self) -> None:
        """Scroll to the bottom of the messages."""
        def do_scroll():
            # Update the scroll region first
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            # Then scroll to bottom
            self.canvas.yview_moveto(1.0)
        
        # Use after_idle to ensure UI has been updated before scrolling
        self.parent_root.after_idle(do_scroll)
    
    def _create_input_area(self) -> None:
        """Create input field and send button."""
        input_frame = tk.Frame(self.main_frame, bg=CHAT_CONFIG['bg'])
        input_frame.pack(fill='x', padx=CHAT_CONFIG['dimensions']['padding'],
                        pady=(0, CHAT_CONFIG['dimensions']['padding']))
        
        # Input field
        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(
            input_frame,
            textvariable=self.input_var,
            bg=CHAT_CONFIG['colors']['input_bg'],
            fg=CHAT_CONFIG['fg'],
            font=CHAT_CONFIG['font'],
            relief='flat',
            borderwidth=5
        )
        self.input_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        # Send button
        self.send_button = self._create_button(
            input_frame, "Send", CHAT_CONFIG['colors']['send'], 
            self._send_message, 'right'
        )
        
        # Bind Enter key to send message
        self.input_entry.bind('<Return>', lambda e: self._send_message())
    
    def _create_button(self, parent: tk.Frame, text: str, colors: dict,
                      command: callable, side: str) -> tk.Button:
        """Create a styled button with hover effects."""
        button = tk.Button(
            parent,
            text=text,
            bg=colors['normal'],
            fg=CHAT_CONFIG['fg'],
            font=CHAT_CONFIG['button_font'],
            relief='flat',
            padx=15,
            pady=5,
            command=command,
            cursor='hand2'
        )
        
        button.pack(side=side)
        
        # Add hover effects
        button.bind('<Enter>', lambda e: button.config(bg=colors['hover']))
        button.bind('<Leave>', lambda e: button.config(bg=colors['normal']))
        
        return button
    
    def _display_message(self, message: Dict[str, Any]) -> None:
        """Display a message bubble in the chat."""
        sender = message['sender']
        content = message['content']
        
        # Create message container
        msg_container = tk.Frame(self.messages_frame, bg=CHAT_CONFIG['bg'])
        msg_container.pack(fill='x', pady=2)
        
        # Determine alignment and color
        if sender == 'user':
            anchor = 'e'
            bubble_color = CHAT_CONFIG['colors']['user_bubble']
            prefix = "🧑‍💻 You:"
        else:
            anchor = 'w'
            bubble_color = CHAT_CONFIG['colors']['ducky_bubble']
            prefix = "🦆 Ducky:"
        
        # Create message bubble
        bubble = tk.Label(
            msg_container,
            text=f"{prefix}\n{content}",
            bg=bubble_color,
            fg='white',
            font=('Arial', 10),
            wraplength=CHAT_CONFIG['dimensions']['max_bubble_width'],
            justify='left',
            padx=CHAT_CONFIG['dimensions']['bubble_padding'],
            pady=CHAT_CONFIG['dimensions']['bubble_padding']
        )
        bubble.pack(anchor=anchor, padx=10)
        
        # Bind mousewheel scrolling to message components
        self._bind_mousewheel(msg_container)
        self._bind_mousewheel(bubble)
        
        # Force UI update then scroll to bottom
        self.messages_frame.update_idletasks()
        self._scroll_to_bottom()
    
    def _position_window(self) -> None:
        """Position the chat window in the center of the screen."""
        self.parent_root.update_idletasks()
        
        # Get screen dimensions
        screen_width = self.parent_root.winfo_screenwidth()
        screen_height = self.parent_root.winfo_screenheight()
        
        # Calculate position (center of screen)
        config = CHAT_CONFIG['dimensions']
        x = (screen_width - config['width']) // 2
        y = (screen_height - config['height']) // 2
        
        self.window.geometry(f"{config['width']}x{config['height']}+{x}+{y}")
    
    def _send_message(self) -> None:
        """Handle send button click or Enter press."""
        if not self.input_var or not self.input_entry:
            return
        
        message = self.input_var.get().strip()
        if not message:
            return
        
        # Clear input
        self.input_var.set("")
        
        # Add user message to display
        self.add_message('user', message)
        
        # Call callback if provided
        if self.on_message_send:
            self.on_message_send(message)
    
    def _close(self) -> None:
        """Handle close button click."""
        # Call callback if provided
        if self.on_close:
            self.on_close()
        
        self.hide()
    
    def _make_draggable(self, widget: tk.Widget) -> None:
        """Make a widget draggable by binding mouse events."""
        widget.bind('<Button-1>', self._start_drag)
        widget.bind('<B1-Motion>', self._on_drag)
        widget.bind('<ButtonRelease-1>', self._stop_drag)
    
    def _start_drag(self, event) -> None:
        """Start dragging the window."""
        if not self.window:
            return
        
        self._is_dragging = True
        self._drag_start_x = event.x_root
        self._drag_start_y = event.y_root
        
        # Get current window position
        window_x = self.window.winfo_x()
        window_y = self.window.winfo_y()
        
        # Calculate offset from mouse to window origin
        self._drag_offset_x = self._drag_start_x - window_x
        self._drag_offset_y = self._drag_start_y - window_y
    
    def _on_drag(self, event) -> None:
        """Handle dragging motion."""
        if not self.window or not self._is_dragging:
            return
        
        # Calculate new window position
        new_x = event.x_root - self._drag_offset_x
        new_y = event.y_root - self._drag_offset_y
        
        # Ensure window stays on screen
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        window_width = self.window.winfo_width()
        window_height = self.window.winfo_height()
        
        # Constrain to screen bounds
        new_x = max(0, min(new_x, screen_width - window_width))
        new_y = max(0, min(new_y, screen_height - window_height))
        
        # Move the window
        self.window.geometry(f"+{new_x}+{new_y}")
    
    def _stop_drag(self, event) -> None:
        """Stop dragging the window."""
        self._is_dragging = False 