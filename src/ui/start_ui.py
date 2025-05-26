import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import os
from typing import Optional


class DuckyUI:
    """A resizable UI window that displays the idle.png image with custom controls."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Ducky")
        
        # Remove window decorations and set always on top
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        
        # Make the window background transparent
        self.root.attributes('-transparentcolor', 'white')
        
        # Set initial size and position
        self.width = 200  # Starting larger than 20x20 for visibility
        self.height = 200
        self.top_bar_height = 40  # Height of the top bar
        self.root.geometry(f"{self.width}x{self.height+self.top_bar_height}+100+100")
        
        # Variables for dragging and resizing
        self.start_x = 0
        self.start_y = 0
        self.dragging = False
        self.resizing = False
        
        # Load and prepare the image
        self.original_image: Optional[Image.Image] = None
        self.photo_image: Optional[ImageTk.PhotoImage] = None
        self.load_image()
        
        # Create the UI elements
        self.setup_ui()
        
        # Bind events for dragging and resizing
        self.bind_events()
    
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
            # Resize image to fill the window below the top bar
            resized_image = self.original_image.resize((self.width, self.height), Image.Resampling.LANCZOS)
            self.photo_image = ImageTk.PhotoImage(resized_image)
            
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
        self.main_frame = tk.Frame(self.root, bg='white')
        self.main_frame.pack(fill='both', expand=True)
        
        # Top bar
        self.top_bar = tk.Frame(
            self.main_frame,
            bg='#2c2c2c',  # Dark background for the top bar
            height=self.top_bar_height
        )
        self.top_bar.pack(fill='x', side='top')
        self.top_bar.pack_propagate(False)  # Maintain height
        
        # Resize handle in top bar (left side)
        self.resize_handle = tk.Label(
            self.top_bar,
            text="⋰",
            font=("Arial", 24),
            fg="white",
            bg='#2c2c2c',
            cursor="size_nw_se"
        )
        self.resize_handle.pack(side='left', padx=10)
        
        # Exit button (X) in top bar (right side)
        self.exit_button = tk.Button(
            self.top_bar,
            text="×",
            font=("Arial", 24, "bold"),
            fg="white",
            bg='#2c2c2c',
            relief="flat",
            command=self.close_app,
            borderwidth=0,
            activebackground='#e81123',  # Red highlight on hover
            activeforeground='white'
        )
        self.exit_button.pack(side='right', padx=10)
        
        # Image container
        self.image_container = tk.Frame(
            self.main_frame,
            bg='white'
        )
        self.image_container.pack(fill='both', expand=True)
        
        # Image label
        self.image_label = tk.Label(self.image_container, bg='white')
        if self.photo_image:
            self.image_label.configure(image=self.photo_image)
        self.image_label.pack(fill='both', expand=True)
    
    def bind_events(self) -> None:
        """Bind mouse events for dragging and resizing."""
        # Dragging events (on main frame and image)
        self.main_frame.bind("<Button-1>", self.start_drag)
        self.main_frame.bind("<B1-Motion>", self.on_drag)
        self.main_frame.bind("<ButtonRelease-1>", self.stop_drag)
        
        self.image_label.bind("<Button-1>", self.start_drag)
        self.image_label.bind("<B1-Motion>", self.on_drag)
        self.image_label.bind("<ButtonRelease-1>", self.stop_drag)
        
        # Resizing events (on resize handle)
        self.resize_handle.bind("<Button-1>", self.start_resize)
        self.resize_handle.bind("<B1-Motion>", self.on_resize)
        self.resize_handle.bind("<ButtonRelease-1>", self.stop_resize)
    
    def start_drag(self, event) -> None:
        """Start dragging the window."""
        if not self.resizing and event.widget != self.resize_handle:
            self.dragging = True
            self.start_x = event.x_root
            self.start_y = event.y_root
    
    def on_drag(self, event) -> None:
        """Handle window dragging."""
        if self.dragging and not self.resizing:
            dx = event.x_root - self.start_x
            dy = event.y_root - self.start_y
            
            x = self.root.winfo_x() + dx
            y = self.root.winfo_y() + dy
            
            self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")
            
            self.start_x = event.x_root
            self.start_y = event.y_root
    
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
            
            # Use the larger of the dimensions to maintain square aspect ratio
            delta = max(dx, dy)
            
            # Calculate new size (minimum 60x60 pixels to accommodate controls)
            new_size = max(60, self.width + delta)
            
            # Update window size (maintaining square aspect ratio)
            self.width = new_size
            self.height = new_size
            
            # Update window position to resize from top-left
            x = self.root.winfo_x() - delta
            y = self.root.winfo_y() - delta
            
            # Apply new geometry (including top bar height)
            self.root.geometry(f"{new_size}x{new_size + self.top_bar_height}+{x}+{y}")
            
            # Update image and control sizes
            self.update_image_size()
            
            # Update start position for next movement
            self.start_x = event.x_root
            self.start_y = event.y_root
    
    def stop_resize(self, event) -> None:
        """Stop resizing the window."""
        self.resizing = False
    
    def close_app(self) -> None:
        """Close the application."""
        self.root.quit()
        self.root.destroy()
    
    def run(self) -> None:
        """Start the UI main loop."""
        self.root.mainloop()


def start_ui() -> None:
    """Start the Ducky UI application."""
    app = DuckyUI()
    app.run()
