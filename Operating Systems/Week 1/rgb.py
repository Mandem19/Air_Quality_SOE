#!/usr/bin/env python3

import tkinter as tk
import re
import sys

def usage():
    print("Usage: python3 rgb.py <COLOR>")
    print("where <COLOR> is a hex triplet RRGGBB")
    sys.exit(1)

if __name__ == '__main__':

    if len(sys.argv) < 2:
        usage()
    if len(sys.argv) > 2:
        print("error: too many arguments")
        usage()
    color=sys.argv[1]
    
    if len(color) < 6:
        print("error: incorrect argument (too short):",color)
        usage()
        
    if len(color) > 6:
        print("error: incorrect argument (too long):",color)
        usage()
        
    if not re.match("[0-9a-zA-z]{6,6}$", color):
        print("error: incorrect argument format:", color)
        usage()

    root = tk.Tk()
    root.title("RGB "+color)

    canvas = tk.Canvas(root,background="#"+color)
    canvas.pack(fill=tk.BOTH,expand=1)
    
    root.mainloop()
