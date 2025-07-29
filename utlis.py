import sys
import os

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller .exe"""
    #base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    full_path= os.path.join(base_path, relative_path)
    return os.path.normpath(full_path)