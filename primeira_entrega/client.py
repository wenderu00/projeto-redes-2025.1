import socket
import threading
import os
from datetime import datetime
from Fragmentation import Fragmentation

SERVER_IP = "127.0.0.1"
SERVER_PORT = 12345
BUFFER_SIZE = 1024

def write_message(message):
    path_name = f"user_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.txt"
    with open(path_name, "w", encoding="utf-8") as file:
        file.write(message)
    return path_name

def receive_message(client_socket):
    while True:
        try:
            data, _ = client_socket.recvfrom(BUFFER_SIZE)
            message = data.decode()
            message_info = message.split("|")
            message_content = message_info[4]
            while message_info[3] == "0":
                data, client_address = client_socket.recvfrom(BUFFER_SIZE)
                message = data.decode()
                message_info = message.split("|")
                message_content += message_info[4]
            message = message_content
            print(f"{message}")
        except Exception as e:
            print(f"Erro ao receber mensagem: {e}")
            break

def send_message(client_socket):
    while True:
        message = input("Digite a mensagem para enviar: ")
        path = write_message(message)
        try:
            fragments = Fragmentation(path)
            [client_socket.sendto(fragment, (SERVER_IP, SERVER_PORT)) for fragment in fragments]
        except Exception as e:
            print(f"Erro ao enviar mensagem: {e}")
            break
        finally:
            os.remove(path)

if __name__ == "__main__":
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.bind(('', 0))  
    threading.Thread(target=receive_message, args=(client_socket,), daemon=True).start()
    send_message(client_socket)