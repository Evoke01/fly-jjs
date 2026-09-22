import sys
import threading
from .web import start_server

def main():
    print("="*55)
    print("  FLY JJS - Local Web Dashboard Starting...")
    print("  Open http://127.0.0.1:5000 in your browser")
    print("="*55)
    start_server(host="127.0.0.1", port=5000)

if __name__ == "__main__":
    main()
