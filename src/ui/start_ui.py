import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import os
import asyncio
import sys
from typing import Optional, Tuple

class APIKeyDialog:
    """Dialog window for collecting the Anthropic API key."""
    
    def __init__(self, parent):
        self.api_key = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("API Key Required")
        
        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        window_width = 400
        window_height = 150
        screen_width = parent.winfo_screenwidth()
        screen_height = parent.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.dialog.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Add widgets
        label = ttk.Label(
            self.dialog,
            text="Please enter your Anthropic API key:",
            wraplength=350,
            justify="center",
            padding=(10, 10)
        )
        label.pack(pady=10)
        
        self.entry = ttk.Entry(self.dialog, width=40, show="*")
        self.entry.pack(pady=10)
        
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=10)
        
        ttk.Button(
            button_frame,
            text="Submit",
            command=self.submit
        ).pack(side="left", padx=5)
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=self.cancel
        ).pack(side="left", padx=5)
        
        # Bind Enter key to submit
        self.dialog.bind("<Return>", lambda e: self.submit())
        self.dialog.bind("<Escape>", lambda e: self.cancel())
        
        # Focus the entry widget
        self.entry.focus_set()
        
        # Wait for dialog to close
        parent.wait_window(self.dialog)
    
    def submit(self) -> None:
        """Submit the API key and close the dialog."""
        self.api_key = self.entry.get().strip()
        self.dialog.destroy()
    
    def cancel(self) -> None:
        """Cancel the operation and close the dialog."""
        self.dialog.destroy()

class DuckyUI:
    """A resizable UI window that displays the idle.png image with custom controls."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Ducky")
        
        # Initialize API key
        self.api_key: Optional[str] = None
        
        # Set minimum size constants
        self.MIN_WIDTH = 80
        self.MIN_HEIGHT = 80
        self.top_bar_height = 40
        
        # Remove window decorations and set always on top
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        
        # Make only the main content area transparent, not the top bar
        self.root.attributes('-transparentcolor', '')  # Initially no transparency
        
        # Set initial size and position (width and height are for the image only)
        self.width = max(200, self.MIN_WIDTH)
        self.height = max(200, self.MIN_HEIGHT)
        # Total window height includes top bar
        total_height = self.height + self.top_bar_height
        self.root.geometry(f"{self.width}x{total_height}+100+100")
        
        # Variables for dragging and resizing
        self.start_x = 0
        self.start_y = 0
        self.dragging = False
        self.resizing = False
        
        # For asyncio integration
        self.running = True
        
        # Load and prepare the image
        self.original_image: Optional[Image.Image] = None
        self.photo_image: Optional[ImageTk.PhotoImage] = None
        self.load_image()
        
        # Create the UI elements
        self.setup_ui()
        
        # Bind events for dragging and resizing
        self.bind_events()
        
        # Set transparency for the main content area only after UI is set up
        self.root.attributes('-transparentcolor', 'white')
    
    def load_image(self) -> None:
        """Load the idle.png image from assets."""
        try:
            # Get the path to the image
            current_dir = os.path.dirname(os.path.abspath(__file__))
            image_path = os.path.join(current_dir, "assets", "idle.png")
            
            # Load the image and convert to RGBA to preserve transparency
            self.original_image = Image.open(image_path).convert('RGBA')
            self.update_image_size()
            
        except Exception as e:
            print(f"Error loading image: {e}")
            # Create a transparent placeholder if image fails to load
            self.original_image = Image.new('RGBA', (100, 100), (0, 0, 0, 0))
            self.update_image_size()
    
    def update_image_size(self) -> None:
        """Update the image size to fit the current window size while maintaining aspect ratio."""
        if self.original_image:
            # Resize image to exactly match the specified dimensions
            resized_image = self.original_image.resize((self.width, self.height), Image.Resampling.LANCZOS)
            self.photo_image = ImageTk.PhotoImage(resized_image)
            
            # Update the image container size
            if hasattr(self, 'image_container'):
                self.image_container.configure(width=self.width, height=self.height)
            
            # Update the label if it exists
            if hasattr(self, 'image_label'):
                self.image_label.configure(image=self.photo_image)
            
            # Update the top bar size
            if hasattr(self, 'top_bar'):
                self.top_bar.configure(width=self.width)
            
            # Update control sizes
            control_size = min(30, self.top_bar_height - 10)  # Leave some padding
            if hasattr(self, 'resize_handle'):
                self.resize_handle.configure(font=("Arial", control_size))
            if hasattr(self, 'exit_button'):
                self.exit_button.configure(font=("Arial", control_size, "bold"))

    def setup_ui(self) -> None:
        """Create the UI elements."""
        # Main frame with transparent background
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill='both', expand=True)
        
        # Top bar with solid background
        self.top_bar = tk.Frame(
            self.main_frame,
            bg='#2c2c2c',  # Dark background for the top bar
            height=self.top_bar_height
        )
        self.top_bar.pack(fill='x', side='top')
        self.top_bar.pack_propagate(False)  # Maintain height
        
        # Container for controls to ensure proper spacing
        control_size = min(30, self.top_bar_height - 10)
        
        # Resize handle in top bar (left side)
        resize_container = tk.Frame(
            self.top_bar,
            bg='#2c2c2c',
            width=control_size,  # Set explicit width
            height=self.top_bar_height
        )
        resize_container.pack(side='left', padx=(5, 0))  # Reduced left padding
        resize_container.pack_propagate(False)  # Maintain size
        
        self.resize_handle = tk.Label(
            resize_container,
            text="⋰",
            font=("Arial", control_size),
            fg="white",
            bg='#2c2c2c',
            cursor="size_nw_se",
            width=1  # Reduced width
        )
        self.resize_handle.place(relx=0.5, rely=0.5, anchor='center')  # Center in container
        
        # Exit button container frame (right side)
        exit_container = tk.Frame(
            self.top_bar,
            bg='#2c2c2c',
            borderwidth=0,
            highlightthickness=0,
            width=control_size,  # Set explicit width
            height=self.top_bar_height
        )
        exit_container.pack(side='right', padx=(0, 5))  # Reduced right padding
        exit_container.pack_propagate(False)  # Maintain size
        
        # Exit button (X) - completely opaque
        self.exit_button = tk.Label(
            exit_container,
            text="×",
            font=("Arial", control_size, "bold"),
            fg="white",
            bg='#2c2c2c',
            width=1,  # Reduced width
            cursor="hand2"  # Show pointer cursor on hover
        )
        self.exit_button.place(relx=0.5, rely=0.5, anchor='center')  # Center in container
        
        # Bind click events for the exit button
        self.exit_button.bind('<Button-1>', lambda e: self.close_app())
        self.exit_button.bind('<Enter>', lambda e: self.exit_button.configure(fg='#e81123'))  # Red on hover
        self.exit_button.bind('<Leave>', lambda e: self.exit_button.configure(fg='white'))    # White when not hovering
        
        # Image container (with transparent background)
        self.image_container = tk.Frame(
            self.main_frame,
            bg='white',  # This will be transparent
            width=self.width,
            height=self.height  # Exact image height
        )
        self.image_container.pack(fill='both', expand=False)
        self.image_container.pack_propagate(False)  # Maintain exact size
        
        # Image label
        self.image_label = tk.Label(
            self.image_container,
            bg='white',  # This will be transparent
            borderwidth=0,
            highlightthickness=0
        )
        if self.photo_image:
            self.image_label.configure(image=self.photo_image)
        self.image_label.place(x=0, y=0, relwidth=1, relheight=1)  # Fill container exactly
    
    def bind_events(self) -> None:
        """Bind mouse events for dragging and resizing."""
        # Dragging events (on top bar and image)
        for widget in (self.top_bar, self.image_label):
            widget.bind("<Button-1>", self.start_drag)
            widget.bind("<B1-Motion>", self.on_drag)
            widget.bind("<ButtonRelease-1>", self.stop_drag)
        
        # Resizing events (on resize handle)
        self.resize_handle.bind("<Button-1>", self.start_resize)
        self.resize_handle.bind("<B1-Motion>", self.on_resize)
        self.resize_handle.bind("<ButtonRelease-1>", self.stop_resize)
        
        # Make sure the image label shows a normal cursor
        self.image_label.configure(cursor="arrow")
    
    def start_drag(self, event) -> None:
        """Start dragging the window."""
        if not self.resizing and event.widget != self.resize_handle and event.widget != self.exit_button:
            self.dragging = True
            self.start_x = event.x_root
            self.start_y = event.y_root
            # Store the initial window position
            self.drag_start_x = self.root.winfo_x()
            self.drag_start_y = self.root.winfo_y()
    
    def on_drag(self, event) -> None:
        """Handle window dragging."""
        if self.dragging and not self.resizing:
            # Calculate the change in position
            dx = event.x_root - self.start_x
            dy = event.y_root - self.start_y
            
            # Update window position
            new_x = self.drag_start_x + dx
            new_y = self.drag_start_y + dy
            
            # Move the window without changing its size
            self.root.geometry(f"{self.width}x{self.height + self.top_bar_height}+{new_x}+{new_y}")
    
    def stop_drag(self, event) -> None:
        """Stop dragging the window."""
        self.dragging = False
    
    def start_resize(self, event) -> None:
        """Start resizing the window."""
        self.resizing = True
        self.start_x = event.x_root
        self.start_y = event.y_root
    
    def on_resize(self, event) -> None:
        """Handle window resizing."""
        if self.resizing:
            # Calculate the change in position (fixed for top-left resize)
            dx = self.start_x - event.x_root
            dy = self.start_y - event.y_root
            
            # Use the larger of the dimensions to maintain square aspect ratio for the image only
            delta = max(dx, dy)
            
            # Calculate new size (respecting minimum size)
            new_size = max(self.MIN_WIDTH, self.width + delta)
            
            # Update image dimensions (maintaining square aspect ratio)
            self.width = new_size
            self.height = new_size
            
            # Update window position to resize from top-left
            x = self.root.winfo_x() - delta
            y = self.root.winfo_y() - delta
            
            # Total height includes top bar
            total_height = self.height + self.top_bar_height
            
            # Apply new geometry
            self.root.geometry(f"{new_size}x{total_height}+{x}+{y}")
            
            # Update image and control sizes
            self.update_image_size()
            
            # Update start position for next movement
            self.start_x = event.x_root
            self.start_y = event.y_root
    
    def stop_resize(self, event) -> None:
        """Stop resizing the window."""
        self.resizing = False
    
    def close_app(self) -> None:
        """Close the application and exit the program."""
        self.running = False
        self.root.quit()
        self.root.destroy()
        sys.exit(0)  # Exit the entire program
    
    async def update(self) -> None:
        """Update the UI asynchronously."""
        try:
            while self.running:
                self.root.update()
                await asyncio.sleep(0.01)  # Small sleep to prevent CPU hogging
        except tk.TclError:  # Handle case when window is closed directly
            sys.exit(0)

    async def get_api_key(self) -> Optional[str]:
        """Show API key dialog and return the entered key.
        
        Returns:
            Optional[str]: The API key if provided, None if cancelled.
        """
        dialog = APIKeyDialog(self.root)
        self.api_key = dialog.api_key
        return self.api_key

async def start_ui() -> DuckyUI:
    """Start the Ducky UI application asynchronously.
    
    Returns:
        DuckyUI: The initialized UI instance.
    """
    app = DuckyUI()
    return app
