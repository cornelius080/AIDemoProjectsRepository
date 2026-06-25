import http.server
import socketserver
import os
import sys
import threading
import time

PORT = 8090
DIRECTORY = "useful_files"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Serve files from the specified directory
        super().__init__(*args, directory=DIRECTORY, **kwargs)

if __name__ == "__main__":
    # Ensure the script is run in the correct directory
    # or that the useful_files folder exists in the current path.
    if not os.path.isdir(DIRECTORY):
        print(f"Error: The directory '{DIRECTORY}' does not exist in the current path ({os.getcwd()}).")
    else:
        # Allow port reuse to prevent "Address already in use" errors
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"Server started! You can view the files by opening your browser at:")
            print(f"http://localhost:{PORT}")
            print("Press Ctrl+C to stop the server.")
            
            # Run serve_forever in a daemon thread so the main thread can catch Ctrl+C instantly
            server_thread = threading.Thread(target=httpd.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            
            try:
                # The main thread just sleeps and waits for KeyboardInterrupt
                while True:
                    time.sleep(0.5)
            except KeyboardInterrupt:
                print("\nStopping server...")
                httpd.shutdown()
                httpd.server_close()
                print("Server stopped cleanly.")
                sys.exit(0)
