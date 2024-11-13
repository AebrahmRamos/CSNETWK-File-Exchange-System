import socket
import sys
import threading
import os
import shutil
from datetime import datetime

# Server constants
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 12345
BUFFER_SIZE = 1024

class FileServer:
    def __init__(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients = {}  # {handle: (socket, address)}
        self.connected_sockets = {}  # {socket: handle}
        
        # Ensure uploads directory exists
        if not os.path.exists("uploads"):
            os.makedirs("uploads")
            
    def start(self):
        self.server.bind((SERVER_HOST, SERVER_PORT))
        self.server.listen(5)
        print(f"Server is listening on {SERVER_HOST}:{SERVER_PORT}")
        
        while True:
            client_socket, client_address = self.server.accept()
            client_thread = threading.Thread(
                target=self.handle_client,
                args=(client_socket, client_address)
            )
            client_thread.daemon = True
            client_thread.start()

    def receive_file(self, client_socket, filename):
        """Handle file receiving with proper completion detection"""
        try:
            file_path = os.path.join("uploads", filename)
            with open(file_path, "wb") as f:
                while True:
                    chunk = client_socket.recv(BUFFER_SIZE)
                    if b"END_OF_FILE" in chunk:
                        # Write the part before END_OF_FILE marker
                        f.write(chunk.split(b"END_OF_FILE")[0])
                        break
                    if not chunk:
                        break
                    f.write(chunk)
            return True
        except Exception as e:
            print(f"Error receiving file: {str(e)}")
            return False

    def send_file(self, client_socket, filename):
        """Handle file sending with proper completion detection"""
        try:
            file_path = os.path.join("uploads", filename)
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(BUFFER_SIZE)
                    if not chunk:
                        # Send end marker
                        client_socket.send(b"END_OF_FILE")
                        break
                    client_socket.send(chunk)
            return True
        except Exception as e:
            print(f"Error sending file: {str(e)}")
            return False

    def handle_client(self, client_socket, address):
        print(f"Connection from {address} has been established.")
        
        while True:
            try:
                command = client_socket.recv(BUFFER_SIZE).decode().strip()
                if not command:
                    break
                    
                print(f"Received command from {address}: {command}")
                parts = command.split()
                cmd = parts[0].lower()
                
                if cmd == "/join":
                    client_socket.send("Connection to the File Exchange Server is successful!".encode())
                        
                elif cmd == "/register":
                    if len(parts) != 2:
                        client_socket.send("Error: Command parameters do not match or is not allowed.".encode())
                        continue
                        
                    handle = parts[1]
                    if handle in self.clients:
                        client_socket.send("Error: Registration failed. Handle or alias already exists.".encode())
                    else:
                        self.clients[handle] = (client_socket, address)
                        self.connected_sockets[client_socket] = handle
                        client_socket.send(f"Welcome {handle}!".encode())
                        
                elif cmd == "/store":
                    if len(parts) != 2:
                        client_socket.send("Error: Command parameters do not match or is not allowed.".encode())
                        continue
                        
                    if client_socket not in self.connected_sockets:
                        client_socket.send("Error: Please register first using /register <handle>".encode())
                        continue
                        
                    filename = parts[1]
                    client_socket.send(f"Ready to receive {filename}".encode())
                    
                    if self.receive_file(client_socket, filename):
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        handle = self.connected_sockets[client_socket]
                        response = f"{handle}<{timestamp}>: Uploaded {filename}"
                        client_socket.send(response.encode())
                    else:
                        client_socket.send("Error: File upload failed.".encode())
                        
                elif cmd == "/dir":
                    if client_socket not in self.connected_sockets:
                        client_socket.send("Error: Please register first using /register <handle>".encode())
                        continue

                    try:
                        files = os.listdir("uploads")
                        response = "Server Directory:\n" + "\n".join(files) if files else "Server Directory:\nNo files found."
                        client_socket.send(response.encode())
                    except Exception as e:
                        client_socket.send("Error: Unable to list directory.".encode())
                        
                elif cmd == "/get":
                    if client_socket not in self.connected_sockets:
                        client_socket.send("Error: Please register first using /register <handle>".encode())
                        continue
                    
                    if len(parts) != 2:
                        client_socket.send("Error: Command parameters do not match or is not allowed.".encode())
                        continue
                        
                    filename = parts[1]
                    filepath = os.path.join("uploads", filename)
                    
                    if not os.path.isfile(filepath):
                        client_socket.send("Error: File not found in the server.".encode())
                        continue
                        
                    client_socket.send(f"Ready to send {filename}".encode())
                    if not self.send_file(client_socket, filename):
                        client_socket.send("Error: File transfer failed.".encode())
                        
                elif cmd == "/leave":
                    if client_socket in self.connected_sockets:
                        handle = self.connected_sockets[client_socket]
                        del self.clients[handle]
                        del self.connected_sockets[client_socket]
                    client_socket.send("Connection closed. Thank you!".encode())
                    break
                    
                elif cmd == "/?":
                    help_message = """Available commands:
/join <server_ip> <port> - Join the server
/register <handle> - Register a handle
/store <filename> - Upload a file to the server
/get <filename> - Download a file from the server
/dir - List files available on the server
/leave - Disconnect from the server
/? - Show this help message"""
                    client_socket.send(help_message.encode())
                    
                else:
                    client_socket.send("Error: Command not found.".encode())
                    
            except Exception as e:
                print(f"Error handling client {address}: {str(e)}")
                break
                
        client_socket.close()

if __name__ == "__main__":
    file_server = FileServer()
    try:
        file_server.start()
    except KeyboardInterrupt:
        print("\nServer shutting down...")
        sys.exit(0)