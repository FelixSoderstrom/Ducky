from tkinter import filedialog
import tkinter as tk

def get_dir_path() -> str:
    """Open a directory selection dialog and return the selected path.
    
    Returns:
        str: The selected directory path or empty string if cancelled.
    """
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    dir_path = filedialog.askdirectory(
        title="Select Directory to Monitor",
        mustexist=True
    )
    
    root.destroy()
    return dir_path