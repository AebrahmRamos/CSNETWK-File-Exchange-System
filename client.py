import socket
import sys
import select
import os

BUFFER_SIZE = 1024

class FileClient:
    def __init__(self):
        self.client = None
        self.connected = False
        
    def connect(self, host, port):
        try:
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.connect((host, port))
            self.connected = True
            return True
        except Exception as e:
            print("Error: Connection to the Server has failed! Please check IP Address and Port Number.")
            return False

    def disconnect(self):
        if not self.connected:
            print("Error: Disconnection failed. Please connect to the server first.")
            return
            
        try:
            self.client.send("/leave".encode())
            response = self.client.recv(BUFFER_SIZE).decode()
            print(response)
            self.client.close()
            self.connected = False
        except Exception as e:
            print(f"Error during disconnection: {str(e)}")

    def send_file(self, filename):
        """Send file with proper completion detection"""
        try:
            with open(filename, "rb") as f:
                while True:
                    chunk = f.read(BUFFER_SIZE)
                    if not chunk:
                        # Send end marker
                        self.client.send(b"END_OF_FILE")
                        break
                    self.client.send(chunk)
            return True
        except Exception as e:
            print(f"Error sending file: {str(e)}")
            return False

    def receive_file(self, filename):
        """Receive file with proper completion detection"""
        try:
            with open(filename, "wb") as f:
                while True:
                    chunk = self.client.recv(BUFFER_SIZE)
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
            
    def handle_store_command(self, command):
        try:
            parts = command.split()
            if len(parts) != 2:
                print("Error: Command parameters do not match or is not allowed.")
                return
                
            filename = parts[1]
            if not os.path.exists(filename):
                print("Error: File not found.")
                return
                
            # Send store command
            self.client.send(command.encode())
            response = self.client.recv(BUFFER_SIZE).decode()
            
            if "Ready to receive" in response:
                print(response)
                if self.send_file(filename):
                    # Wait for upload confirmation
                    response = self.client.recv(BUFFER_SIZE).decode()
                    print(response)
                else:
                    print("Error: File transfer failed.")
            else:
                print(f"Error: {response}")
                
        except Exception as e:
            print(f"Error processing store command: {str(e)}")
            
    def handle_get_command(self, command):
        try:
            parts = command.split()
            if len(parts) != 2:
                print("Error: Command parameters do not match or is not allowed.")
                return
                
            filename = parts[1]
            self.client.send(command.encode())
            response = self.client.recv(BUFFER_SIZE).decode()
            
            if "Ready to send" in response:
                print(response)
                if self.receive_file(filename):
                    print(f"File received from Server: {filename}")
                else:
                    print("Error: File transfer failed.")
            else:
                print(response)
                
        except Exception as e:
            print(f"Error receiving file: {str(e)}")

    def wait_for_response(self, timeout=5):
        """Wait for server response with timeout"""
        ready = select.select([self.client], [], [], timeout)
        if ready[0]:
            return self.client.recv(BUFFER_SIZE).decode()
        return None
            
    def start(self):
        print("File Exchange Client. Type /? for command list.")
        
        while True:
            try:
                command = input("> ").strip()
                if not command:
                    continue
                    
                parts = command.split()
                cmd = parts[0].lower()
                
                if cmd == "/join":
                    if len(parts) != 3:
                        print("Error: Command parameters do not match or is not allowed.")
                        continue
                        
                    if self.connected:
                        print("Error: Already connected to a server.")
                        continue
                        
                    host = parts[1]
                    try:
                        port = int(parts[2])
                    except ValueError:
                        print("Error: Invalid port number.")
                        continue
                        
                    if self.connect(host, port):
                        self.client.send(command.encode())
                        response = self.wait_for_response()
                        if response:
                            print(response)
                        else:
                            print("Error: No response from server")
                            self.disconnect()
                        
                elif not self.connected:
                    print("Error: Please connect to the server first using /join <server_ip> <port>")
                    continue
                    
                elif cmd == "/leave":
                    self.disconnect()
                    break
                    
                elif cmd == "/store":
                    self.handle_store_command(command)
                    
                elif cmd == "/get":
                    self.handle_get_command(command)
                    
                else:
                    # Handle other commands
                    self.client.send(command.encode())
                    response = self.wait_for_response()
                    if response:
                        print(response)
                    else:
                        print("Error: No response from server")
                        self.disconnect()
                        break
                    
            except KeyboardInterrupt:
                print("\nDisconnecting from server...")
                if self.connected:
                    self.disconnect()
                break
            except Exception as e:
                print(f"Error: {str(e)}")
                if self.connected:
                    self.disconnect()
                break

if __name__ == "__main__":
    client = FileClient()
    client.start()