"""Main UI layout component for the Ducky UI."""

import tkinter as tk
import logging
from typing import Optional, Tuple, Callable

logger = logging.getLogger("ducky.ui.main_layout")


class MainUILayout:
    """Manages the main UI layout including frames, top bar, and controls."""
    
    def __init__(self, root: tk.Tk, top_bar_height: int = 20):
        self.root = root
        self.top_bar_height = top_bar_height
        
        # UI components
        self.main_frame: Optional[tk.Frame] = None
        self.top_bar: Optional[tk.Frame] = None
        self.image_container: Optional[tk.Frame] = None
        self.image_label: Optional[tk.Label] = None
        self.resize_handle: Optional[tk.Label] = None
        self.exit_button: Optional[tk.Label] = None
        
        # Callbacks
        self.close_callback: Optional[Callable] = None
        
    def create_layout(self, width: int, height: int) -> None:
        """Create the main UI layout.
        
        Args:
            width: Width of the image area
            height: Height of the image area
        """
        self._create_main_frame()
        self._create_top_bar(width)
        self._create_image_container(width, height)
        
        logger.info(f"Main UI layout created: {width}x{height}")
    
    def _create_main_frame(self) -> None:
        """Create the main frame that contains all UI elements."""
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill='both', expand=True)
        logger.debug("Main frame created")
    
    def _create_top_bar(self, width: int) -> None:
        """Create the top bar with controls.
        
        Args:
            width: Width of the top bar
        """
        # Top bar with solid background
        self.top_bar = tk.Frame(
            self.main_frame,
            bg='#2c2c2c',  # Dark background for the top bar
            height=self.top_bar_height
        )
        self.top_bar.pack(fill='x', side='top')
        self.top_bar.pack_propagate(False)  # Maintain height
        
        # Create controls
        self._create_resize_handle()
        self._create_exit_button()
        
        logger.debug("Top bar created")
    
    def _create_resize_handle(self) -> None:
        """Create the resize handle control."""
        control_size = min(30, self.top_bar_height - 10)
        
        # Resize handle container
        resize_container = tk.Frame(
            self.top_bar,
            bg='#2c2c2c',
            width=control_size,
            height=self.top_bar_height
        )
        resize_container.pack(side='left', padx=(5, 0))
        resize_container.pack_propagate(False)
        
        # Resize handle label
        self.resize_handle = tk.Label(
            resize_container,
            text="⋰",
            font=("Arial", control_size),
            fg="white",
            bg='#2c2c2c',
            cursor="size_nw_se",
            width=1
        )
        self.resize_handle.place(relx=0.5, rely=0.5, anchor='center')
        
        logger.debug("Resize handle created")
    
    def _create_exit_button(self) -> None:
        """Create the exit button control."""
        control_size = min(30, self.top_bar_height - 10)
        
        # Exit button container
        exit_container = tk.Frame(
            self.top_bar,
            bg='#2c2c2c',
            borderwidth=0,
            highlightthickness=0,
            width=control_size,
            height=self.top_bar_height
        )
        exit_container.pack(side='right', padx=(0, 5))
        exit_container.pack_propagate(False)
        
        # Exit button label
        self.exit_button = tk.Label(
            exit_container,
            text="×",
            font=("Arial", control_size, "bold"),
            fg="white",
            bg='#2c2c2c',
            width=1,
            cursor="hand2"
        )
        self.exit_button.place(relx=0.5, rely=0.5, anchor='center')
        
        # Bind click events and hover effects
        self.exit_button.bind('<Button-1>', self._handle_exit_click)
        self.exit_button.bind('<Enter>', lambda e: self.exit_button.configure(fg='#e81123'))  # Red on hover
        self.exit_button.bind('<Leave>', lambda e: self.exit_button.configure(fg='white'))    # White when not hovering
        
        logger.debug("Exit button created")
    
    def _create_image_container(self, width: int, height: int) -> None:
        """Create the image container and label.
        
        Args:
            width: Width of the image container
            height: Height of the image container
        """
        # Image container
        self.image_container = tk.Frame(
            self.main_frame,
            width=width,
            height=height
        )
        self.image_container.pack(fill='both', expand=False)
        self.image_container.pack_propagate(False)
        
        # Image label
        self.image_label = tk.Label(
            self.image_container,
            borderwidth=0,
            highlightthickness=0,
            cursor="arrow"
        )
        self.image_label.place(x=0, y=0, relwidth=1, relheight=1)
        
        logger.debug(f"Image container created: {width}x{height}")
    
    def update_image(self, image) -> None:
        """Update the image displayed in the image label.
        
        Args:
            image: The image to display (ImageTk.PhotoImage)
        """
        if self.image_label and image:
            self.image_label.configure(image=image)
            logger.debug("Image updated in layout")
    
    def update_size(self, width: int, height: int) -> None:
        """Update the size of UI components.
        
        Args:
            width: New width
            height: New height
        """
        # Update image container size
        if self.image_container:
            self.image_container.configure(width=width, height=height)
        
        # Update top bar width
        if self.top_bar:
            self.top_bar.configure(width=width)
        
        # Update control sizes
        control_size = min(30, self.top_bar_height - 10)
        if self.resize_handle:
            self.resize_handle.configure(font=("Arial", control_size))
        if self.exit_button:
            self.exit_button.configure(font=("Arial", control_size, "bold"))
        
        logger.debug(f"Layout size updated: {width}x{height}")
    
    def set_close_callback(self, callback: Callable) -> None:
        """Set callback function for when exit button is clicked.
        
        Args:
            callback: Function to call when exit is clicked
        """
        self.close_callback = callback
    
    def _handle_exit_click(self, event) -> None:
        """Handle exit button click.
        
        Args:
            event: The click event
        """
        logger.info("Exit button clicked")
        if self.close_callback:
            try:
                self.close_callback()
            except Exception as e:
                logger.error(f"Error in close callback: {str(e)}")
    
    def get_drag_widgets(self) -> list:
        """Get list of widgets that should enable window dragging.
        
        Returns:
            list: List of widgets for dragging
        """
        widgets = []
        if self.top_bar:
            widgets.append(self.top_bar)
        if self.image_label:
            widgets.append(self.image_label)
        return widgets
    
    def get_resize_handle(self) -> Optional[tk.Label]:
        """Get the resize handle widget.
        
        Returns:
            Optional[tk.Label]: The resize handle widget
        """
        return self.resize_handle
    
    def get_image_label(self) -> Optional[tk.Label]:
        """Get the image label widget.
        
        Returns:
            Optional[tk.Label]: The image label widget
        """
        return self.image_label
    
    def get_image_container(self) -> Optional[tk.Frame]:
        """Get the image container widget.
        
        Returns:
            Optional[tk.Frame]: The image container widget
        """
        return self.image_container
    
    def destroy(self) -> None:
        """Clean up the layout components."""
        components = [
            self.main_frame,
            self.top_bar,
            self.image_container,
            self.image_label,
            self.resize_handle,
            self.exit_button
        ]
        
        for component in components:
            if component:
                try:
                    component.destroy()
                except Exception as e:
                    logger.error(f"Error destroying component: {str(e)}")
        
        logger.debug("Main UI layout destroyed") 