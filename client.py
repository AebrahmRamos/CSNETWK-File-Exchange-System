import os
import socket
import sys
import select

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
            
    def handle_store_command(self, command):
        try:
            parts = command.split()
            if len(parts) != 2:
                print("Error: Command parameters do not match or is not allowed.")
                return
                
            filename = parts[1]
            
            try:
                with open(filename, "rb") as f:
                    # Send store command
                    self.client.send(command.encode())
                    response = self.client.recv(BUFFER_SIZE).decode()
                    
                    if "Ready to receive" in response:
                        print(response)
                        # Send file data
                        while True:
                            bytes_read = f.read(BUFFER_SIZE)
                            if not bytes_read:
                                self.client.send(b'DONE')
                                break
                            self.client.send(bytes_read)
                        
                        # Get upload confirmation
                        response = self.client.recv(BUFFER_SIZE).decode()
                        print(response)
                        if "Upload confirmed" in response:
                            os.remove(filename)
                            print(f"File {filename} removed from root directory.")
                    else:
                        print(f"Error: {response}")
                        
            except FileNotFoundError:
                print("Error: File not found.")
            except Exception as e:
                print(f"Error while sending file: {str(e)}")
                
        except Exception as e:
            print(f"Error processing store command: {str(e)}")
            
    def handle_get_command(self, command):
        try:
            self.client.send(command.encode())
            response = self.client.recv(BUFFER_SIZE).decode()
            
            if "Ready to send" in response:
                filename = command.split()[1]
                with open(filename, "wb") as f:
                    while True:
                        bytes_read = self.client.recv(BUFFER_SIZE)
                        if bytes_read == b'DONE':
                            break
                        f.write(bytes_read)
                print(f"File received from Server: {filename}")
            else:
                print(response)
                
        except Exception as e:
            print(f"Error receiving file: {str(e)}")

    def wait_for_response(self):
        """Wait for server response with timeout"""
        ready = select.select([self.client], [], [], 5)  # 5 second timeout
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