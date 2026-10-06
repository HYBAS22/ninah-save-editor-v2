"""Entry point: `python ninah_tool.py find|dec|info|get|set|enc|verify ...`"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ninah.cli import main

if __name__ == "__main__":
    sys.exit(main())
