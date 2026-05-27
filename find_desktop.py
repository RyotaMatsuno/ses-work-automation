import subprocess, sys, os

# 実際のパスを確認
import pathlib
p = pathlib.Path(r'C:\Users\ma_py\OneDrive') 
for child in p.iterdir():
    if 'desk' in child.name.lower() or 'デスク' in child.name:
        print(repr(child))
