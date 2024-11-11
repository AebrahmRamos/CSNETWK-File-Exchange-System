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
            client_thread.daemon = True  # Make thread daemon so it exits when main thread exits
            client_thread.start()

    def handle_client(self, client_socket, address):
        print(f"Connection from {address} has been established.")
        
        while True:
            try:
                command = client_socket.recv(BUFFER_SIZE).decode().strip()
                if not command:
                    break
                    
                print(f"Received command from {address}: {command}")  # Debug print
                parts = command.split()
                cmd = parts[0].lower()
                
                if cmd == "/join":
                    # Immediately send success response for /join
                    response = "Connection to the File Exchange Server is successful!"
                    print(f"Sending response to {address}: {response}")  # Debug print
                    client_socket.send(response.encode())
                        
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
                    
                    try:

                        with open(os.path.join("uploads", filename), "wb") as f:
                            print(f"Receiving file {filename} from {address}")  # Debug print
                            while True:
                                bytes_read = client_socket.recv(BUFFER_SIZE)
                                if bytes_read == b'DONE':
                                    print(f"Finished receiving file {filename} from {address}")  # Debug print
                                    break
                                f.write(bytes_read)
                                print(f"Received {len(bytes_read)} bytes for file {filename} from {address}")  # Debug print
                                
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        handle = self.connected_sockets[client_socket]
                        response = f"{handle}<{timestamp}>: Uploaded {filename}"
                        client_socket.send(response.encode())
                        
                    except Exception as e:
                        client_socket.send(f"Error: File upload failed - {str(e)}".encode())
                        
                elif cmd == "/dir":
                    try:
                        files = os.listdir("uploads")
                        response = "Server Directory:\n" + "\n".join(files) if files else "Server Directory:\nNo files found."
                        client_socket.send(response.encode())
                    except Exception as e:
                        client_socket.send("Error: Unable to list directory.".encode())
                        
                elif cmd == "/get":
                    if len(parts) != 2:
                        client_socket.send("Error: Command parameters do not match or is not allowed.".encode())
                        continue
                        
                    filename = parts[1]
                    filepath = os.path.join("uploads", filename)
                    
                    if not os.path.isfile(filepath):
                        client_socket.send("Error: File not found in the server.".encode())
                        continue
                        
                    try:
                        with open(filepath, "rb") as f:
                            client_socket.send(f"Ready to send {filename}".encode())
                            while True:
                                bytes_read = f.read(BUFFER_SIZE)
                                if not bytes_read:
                                    break
                                client_socket.send(bytes_read)
                            client_socket.send(b'DONE')
                    except Exception as e:
                        client_socket.send(f"Error: File download failed - {str(e)}".encode())
                        
                elif cmd == "/leave":
                    if client_socket in self.connected_sockets:
                        handle = self.connected_sockets[client_socket]
                        del self.clients[handle]
                        del self.connected_sockets[client_socket]
                    client_socket.send("Connection closed. Thank you!".encode())
                    client_socket.close()
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
                
        try:
            if client_socket in self.connected_sockets:
                handle = self.connected_sockets[client_socket]
                del self.clients[handle]
                del self.connected_sockets[client_socket]
            client_socket.close()
        except:
            pass

if __name__ == "__main__":
    file_server = FileServer()
    try:
        file_server.start()
    except KeyboardInterrupt:
        print("\nServer shutting down...")
        sys.exit(0)