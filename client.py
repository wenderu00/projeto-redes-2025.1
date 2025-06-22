import socket
import threading
import os

SERVER_IP = "127.0.0.1"
SERVER_PORT = 12345
BUFFER_SIZE = 1024

def receive_message(client_socket):
    while True:
        try:
            data, _ = client_socket.recvfrom(BUFFER_SIZE)
            print(f"{data.decode()}")
        except Exception as e:
            print(f"Erro ao receber mensagem: {e}")
            break

def send_message(client_socket):
    while True:
        message = input("Digite a mensagem para enviar: ")
        try:
            client_socket.sendto(message.encode(), (SERVER_IP, SERVER_PORT))
        except Exception as e:
            print(f"Erro ao enviar mensagem: {e}")
            break

if __name__ == "__main__":
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.bind(('', 0))  
    threading.Thread(target=receive_message, args=(client_socket,), daemon=True).start()
    send_message(client_socket)