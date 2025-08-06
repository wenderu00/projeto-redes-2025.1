import socket
import datetime
import os
from Fragmentation import Fragmentation
from datetime import datetime

SERVER_IP = "127.0.0.1"
SERVER_PORT = 12345
BUFFER_SIZE = 1024

clients = {}

def write_message(message):
    path_name = f"server_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.txt"
    with open(path_name, "w", encoding="utf-8") as file:
        file.write(message)
    return path_name

def format_message(message, client_address, clients):
    timestamp = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
    return f"{client_address[0]}:{client_address[1]}/~{clients[client_address]}: {message} {timestamp}"

def is_connect_command(message): 
    return message[0:len("hi, meu nome eh ")] == "hi, meu nome eh "

def is_exit_command(message):
    return message == "bye"

def is_client_in_room(client_address, room_clients):
    return client_address in room_clients

def catch_username(message):
    return message[len("hi, meu nome eh "):len(message)] 

def create_server(ip, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((ip, port))
    return server_socket

def send_message(message, server_socket, client_address):
    path = write_message(message)
    try:
        fragments = Fragmentation(path)
        [server_socket.sendto(fragment, client_address) for fragment in fragments]
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")
    finally:
        os.remove(path)

def new_user_connection_message(new_user):
    return f"<{new_user}> foi conectado a sala"

def user_logged_out_message(disconnected_user):
    return f"<{disconnected_user}> saiu da sala"

def connected_message():
    return "conectado"

def not_connected_message():
    return "você não está conectado.\npara conectar digite o seguinte comando: \"hi, meu nome eh <NOME_DE_USUARIO>\""

def disconnected_message():
    return "você foi desconectado"

def server_new_connection_message(client_address):
    return f"Novo cliente conectado: {client_address}"

def server_disconnected_user_message(client_address):
    return f"cliente desconectado: {client_address}"

def server_start_message(server_socket):
    return f"Servidor iniciado em {server_socket.getsockname()[0]}:{server_socket.getsockname()[1]}"

def notify_every_client(clients, message, server_socket):
    for client in clients:
        send_message(message, server_socket, client)

def start_server():
    server_socket = create_server(SERVER_IP, SERVER_PORT)
    print(server_start_message(server_socket))

    while True:
        data, client_address = server_socket.recvfrom(BUFFER_SIZE)
        message = data.decode()
        message_info = message.split("|")
        message_content = message_info[4]
        while message_info[3] == "0":
            data, client_address = server_socket.recvfrom(BUFFER_SIZE)
            message = data.decode()
            message_info = message.split("|")
            message_content += message_info[4]
        message = message_content
        if not is_client_in_room(client_address, clients) and is_connect_command(message):
            print(f"Conexão recebida de {client_address}")
            username = catch_username(message)
            print(server_new_connection_message(client_address))
            send_message(connected_message(), server_socket, client_address)
            notify_every_client(clients, new_user_connection_message(username), server_socket)
            clients[client_address] = username 
            
        elif not is_client_in_room(client_address, clients) and not is_connect_command(message):
            send_message(not_connected_message(),server_socket, client_address)
            
        elif is_exit_command(message):
            disconnected_user = clients[client_address]
            del clients[client_address]
            print(server_disconnected_user_message(client_address))
            send_message(disconnected_message(), server_socket, client_address)
            notify_every_client(clients, user_logged_out_message(disconnected_user),server_socket)

        else:
            formatted_message = format_message(message, client_address, clients)
            notify_every_client(clients, formatted_message, server_socket)

if __name__ == "__main__":
  start_server()