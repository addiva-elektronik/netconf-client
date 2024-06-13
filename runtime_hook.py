import sys
import os

if not sys.stderr:
    sys.stderr = open(os.devnull, 'w')

if not sys.stdout:
    sys.stdout = open(os.devnull, 'w')