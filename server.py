import socket
import threading
import datetime
import os
from Fragmentation import Fragmentation
from datetime import datetime
import zlib

# Configurações do servidor
SERVER_IP = "127.0.0.1"
SERVER_PORT = 12345
BUFFER_SIZE = 1024

# Dicionário de clientes conectados: {endereço: nome}
clients = {}

# Função utilitária para salvar mensagens em arquivo temporário
# (usado para fragmentação)
def write_message(message):
    path_name = f"server_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.txt"
    with open(path_name, "w", encoding="utf-8") as file:
        file.write(message)
    return path_name

# Formata a mensagem para exibição no chat
def format_message(message, client_address, clients):
    timestamp = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
    return f"{client_address[0]}:{client_address[1]}/~{clients[client_address]}: {message} {timestamp}"

# Verifica se a mensagem é comando de conexão
def is_connect_command(message): 
    return message[0:len("hi, meu nome eh <")] == "hi, meu nome eh <" and message[len(message)-1] == ">"

# Verifica se a mensagem é comando de saída
def is_exit_command(message):
    return message == "bye"

# Verifica se o cliente está na sala
def is_client_in_room(client_address, room_clients):
    return client_address in room_clients

# Extrai o nome de usuário do comando de conexão
def catch_username(message):
    return message[len("hi, meu nome eh <"):len(message)-1] 

# Cria o socket UDP do servidor
def create_server(ip, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((ip, port))
    return server_socket

# Envia mensagem fragmentada para um cliente
def send_message(message, server_socket, client_address):
    path = write_message(message)
    try:
        fragments = Fragmentation(path)
        [server_socket.sendto(fragment, client_address) for fragment in fragments]
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")
    finally:
        os.remove(path)

# Mensagens de sistema para o chat
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

# Função principal do servidor: implementa o RDT 3.0
def start_server():
    server_socket = create_server(SERVER_IP, SERVER_PORT)
    print(server_start_message(server_socket))

    # Dicionário para armazenar o último ACK enviado para cada mensagem (ID)
    last_ack_sent = {}
    while True:
        # 1. Recebe pacote UDP do cliente
        data, client_address = server_socket.recvfrom(BUFFER_SIZE)
        data_str = data.decode(errors='ignore')
        
        # Ignora pacotes de ACK recebidos do cliente
        if data_str.startswith('ACK|'):
            print(f"[INFO] ACK recebido de {client_address}, ignorando.")
            continue

        print(f"[RECEBIDO] Pacote recebido de {client_address} ({len(data)} bytes)")
        split_idx = data_str.find('|')
        if split_idx == -1:
            print('[ERRO] Pacote mal formatado (sem checksum).')
            # Não é possível extrair ID, não reenviar ACK
            continue
        received_checksum = int(data_str[:split_idx])
        rest = data[split_idx+1:]
        # 2. Procura o fim do cabeçalho (quarto '|')
        header_end = 0
        pipe_count = 0
        for i, b in enumerate(rest):
            if b == ord('|'):
                pipe_count += 1
                if pipe_count == 4:
                    header_end = i + 1
                    break
        if pipe_count < 4:
            print('[ERRO] Cabeçalho incompleto.')
            # Tenta extrair ID e reenviar último ACK, se possível
            try:
                header_str = rest[:].decode(errors='ignore')
                header_parts = header_str.split('|')
                arquivo_id = header_parts[0]
                if arquivo_id in last_ack_sent:
                    print(f"[RETRANSMISSÃO] Reenviando último ACK para ID={arquivo_id}")
                    server_socket.sendto(last_ack_sent[arquivo_id], client_address)
            except Exception:
                pass
            continue
        header_bytes = rest[:header_end]
        chunk = rest[header_end:]
        print('[PROCESSO] Verificando integridade do pacote (checksum)...')
        calc_checksum = zlib.crc32(header_bytes + chunk)
        if calc_checksum != received_checksum:
            print('[ERRO] Pacote corrompido (checksum inválido).')
            # Tenta extrair ID e reenviar último ACK, se possível
            try:
                header_str = header_bytes.decode(errors='ignore')
                header_parts = header_str.split('|')
                arquivo_id = header_parts[0]
                if arquivo_id in last_ack_sent:
                    print(f"[RETRANSMISSÃO] Reenviando último ACK para ID={arquivo_id}")
                    server_socket.sendto(last_ack_sent[arquivo_id], client_address)
            except Exception:
                pass
            continue
        print('[OK] Checksum válido!')
        # 3. Decodifica o pacote e extrai informações do cabeçalho
        message = (header_bytes + chunk).decode(errors='ignore')
        message_info = message.split("|", 4)
        message_content = message_info[4]
        arquivo_id = message_info[0]
        num_pacote = message_info[1]
        # 4. Monta e envia o ACK para o cliente
        ack_str = f"ACK|{arquivo_id}|{num_pacote}"
        ack_checksum = zlib.crc32(ack_str.encode('utf-8'))
        ack_packet = f"{ack_str}|{ack_checksum}".encode('utf-8')
        print(f"[ENVIO] Enviando ACK para {client_address} (ID={arquivo_id}, SEQ={num_pacote})")
        server_socket.sendto(ack_packet, client_address)
        last_ack_sent[arquivo_id] = ack_packet
        # 5. Monta a mensagem completa caso seja fragmentada
        while message_info[3] == "0":
            print('[PROCESSO] Aguardando próximo fragmento para montagem da mensagem completa...')
            data, client_address = server_socket.recvfrom(BUFFER_SIZE)
            print(f"[RECEBIDO] Pacote recebido de {client_address} ({len(data)} bytes)")
            data_str = data.decode(errors='ignore')
            split_idx = data_str.find('|')
            if split_idx == -1:
                print('[ERRO] Pacote mal formatado (sem checksum).')
                continue
            received_checksum = int(data_str[:split_idx])
            rest = data[split_idx+1:]
            header_end = 0
            pipe_count = 0
            for i, b in enumerate(rest):
                if b == ord('|'):
                    pipe_count += 1
                    if pipe_count == 4:
                        header_end = i + 1
                        break
            if pipe_count < 4:
                print('[ERRO] Cabeçalho incompleto.')
                try:
                    header_str = rest[:].decode(errors='ignore')
                    header_parts = header_str.split('|')
                    arquivo_id = header_parts[0]
                    if arquivo_id in last_ack_sent:
                        print(f"[RETRANSMISSÃO] Reenviando último ACK para ID={arquivo_id}")
                        server_socket.sendto(last_ack_sent[arquivo_id], client_address)
                except Exception:
                    pass
                continue
            header_bytes = rest[:header_end]
            chunk = rest[header_end:]
            print('[PROCESSO] Verificando integridade do pacote (checksum)...')
            calc_checksum = zlib.crc32(header_bytes + chunk)
            if calc_checksum != received_checksum:
                print('[ERRO] Pacote corrompido (checksum inválido).')
                try:
                    header_str = header_bytes.decode(errors='ignore')
                    header_parts = header_str.split('|')
                    arquivo_id = header_parts[0]
                    if arquivo_id in last_ack_sent:
                        print(f"[RETRANSMISSÃO] Reenviando último ACK para ID={arquivo_id}")
                        server_socket.sendto(last_ack_sent[arquivo_id], client_address)
                except Exception:
                    pass
                continue
            print('[OK] Checksum válido!')
            message = (header_bytes + chunk).decode(errors='ignore')
            message_info = message.split("|", 4)
            message_content += message_info[4]
            arquivo_id = message_info[0]
            num_pacote = message_info[1]
            ack_str = f"ACK|{arquivo_id}|{num_pacote}"
            ack_checksum = zlib.crc32(ack_str.encode('utf-8'))
            ack_packet = f"{ack_str}|{ack_checksum}".encode('utf-8')
            print(f"[ENVIO] Enviando ACK para {client_address} (ID={arquivo_id}, SEQ={num_pacote})")
            server_socket.sendto(ack_packet, client_address)
            last_ack_sent[arquivo_id] = ack_packet
        message = message_content
        # 6. Lógica de chat: conexão, desconexão e broadcast
        if not is_client_in_room(client_address, clients) and is_connect_command(message):
            print(f"[CONEXÃO] Conexão recebida de {client_address}")
            username = catch_username(message)
            print(f"[CONEXÃO] Novo cliente conectado: {client_address} (usuário: {username})")
            send_message(connected_message(), server_socket, client_address)
            notify_every_client(clients, new_user_connection_message(username), server_socket)
            clients[client_address] = username 
        elif not is_client_in_room(client_address, clients) and not is_connect_command(message):
            print(f"[ERRO] Cliente {client_address} tentou enviar mensagem sem estar conectado.")
            send_message(not_connected_message(),server_socket, client_address)
        elif is_exit_command(message):
            disconnected_user = clients[client_address]
            del clients[client_address]
            print(f"[DESCONECTADO] Cliente desconectado: {client_address} (usuário: {disconnected_user})")
            send_message(disconnected_message(), server_socket, client_address)
            notify_every_client(clients, user_logged_out_message(disconnected_user),server_socket)
        else:
            formatted_message = format_message(message, client_address, clients)
            print(f"[MENSAGEM] Mensagem recebida de {client_address}: {formatted_message}")
            notify_every_client(clients, formatted_message, server_socket)

if __name__ == "__main__":
    start_server()