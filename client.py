import socket
import threading
import os
from datetime import datetime
from Fragmentation import Fragmentation
import zlib
import time

# Configurações do cliente
SERVER_IP = "127.0.0.1"
SERVER_PORT = 12345
BUFFER_SIZE = 1024

# Função utilitária para salvar mensagens em arquivo temporário (usado para fragmentação)
def write_message(message):
    path_name = f"user_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.txt"
    with open(path_name, "w", encoding="utf-8") as file:
        file.write(message)
    return path_name

# Função que recebe mensagens do servidor e implementa o RDT 3.0 para recebimento
def receive_message(client_socket):
    # Dicionário para armazenar o último ACK enviado para cada mensagem (ID)
    last_ack_sent = {}
    while True:
        try:
            # 1. Recebe pacote UDP do servidor
            data, sender_addr = client_socket.recvfrom(BUFFER_SIZE)
            print(f"[RECEBIDO] Pacote recebido de {sender_addr} ({len(data)} bytes)")
            # 2. Extrai o checksum do início do pacote
            data_str = data.decode(errors='ignore')
            split_idx = data_str.find('|')
            if split_idx == -1:
                print('[ERRO] Pacote mal formatado (sem checksum).')
                # Não é possível extrair ID, não reenviar ACK
                continue
            received_checksum = int(data_str[:split_idx])
            rest = data[split_idx+1:]
            # 3. Procura o fim do cabeçalho (quinto '|')
            header_end = 0
            pipe_count = 0
            for i, b in enumerate(rest):
                if b == ord('|'):
                    pipe_count += 1
                    if pipe_count == 5:
                        header_end = i + 1
                        break
            if pipe_count < 5:
                print('[ERRO] Cabeçalho incompleto.')
                # Tenta extrair ID e reenviar último ACK, se possível
                try:
                    header_str = rest[:].decode(errors='ignore')
                    header_parts = header_str.split('|')
                    arquivo_id = header_parts[0]
                    if arquivo_id in last_ack_sent:
                        print(f"[RETRANSMISSÃO] Reenviando último ACK para ID={arquivo_id}")
                        client_socket.sendto(last_ack_sent[arquivo_id], sender_addr)
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
                        client_socket.sendto(last_ack_sent[arquivo_id], sender_addr)
                except Exception:
                    pass
                continue
            print('[OK] Checksum válido!')
            # 4. Decodifica o pacote e extrai informações do cabeçalho
            message = (header_bytes + chunk).decode(errors='ignore')
            message_info = message.split("|")
            message_content = message_info[4]
            arquivo_id = message_info[0]
            num_pacote = message_info[1]
            # 5. Monta e envia o ACK para o servidor
            ack_str = f"ACK|{arquivo_id}|{num_pacote}"
            ack_checksum = zlib.crc32(ack_str.encode('utf-8'))
            ack_packet = f"{ack_str}|{ack_checksum}".encode('utf-8')
            print(f"[ENVIO] Enviando ACK para {sender_addr} (ID={arquivo_id}, SEQ={num_pacote})")
            client_socket.sendto(ack_packet, sender_addr)
            last_ack_sent[arquivo_id] = ack_packet
            # 6. Monta a mensagem completa caso seja fragmentada
            while message_info[3] == "0":
                print('[PROCESSO] Aguardando próximo fragmento para montagem da mensagem completa...')
                data, sender_addr = client_socket.recvfrom(BUFFER_SIZE)
                print(f"[RECEBIDO] Pacote recebido de {sender_addr} ({len(data)} bytes)")
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
                        if pipe_count == 5:
                            header_end = i + 1
                            break
                if pipe_count < 5:
                    print('[ERRO] Cabeçalho incompleto.')
                    try:
                        header_str = rest[:].decode(errors='ignore')
                        header_parts = header_str.split('|')
                        arquivo_id = header_parts[0]
                        if arquivo_id in last_ack_sent:
                            print(f"[RETRANSMISSÃO] Reenviando último ACK para ID={arquivo_id}")
                            client_socket.sendto(last_ack_sent[arquivo_id], sender_addr)
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
                            client_socket.sendto(last_ack_sent[arquivo_id], sender_addr)
                    except Exception:
                        pass
                    continue
                print('[OK] Checksum válido!')
                message = (header_bytes + chunk).decode(errors='ignore')
                message_info = message.split("|")
                message_content += message_info[4]
                arquivo_id = message_info[0]
                num_pacote = message_info[1]
                ack_str = f"ACK|{arquivo_id}|{num_pacote}"
                ack_checksum = zlib.crc32(ack_str.encode('utf-8'))
                ack_packet = f"{ack_str}|{ack_checksum}".encode('utf-8')
                print(f"[ENVIO] Enviando ACK para {sender_addr} (ID={arquivo_id}, SEQ={num_pacote})")
                client_socket.sendto(ack_packet, sender_addr)
                last_ack_sent[arquivo_id] = ack_packet
            message = message_content
            print(f"{message}")
        except Exception as e:
            print(f"Erro ao receber mensagem: {e}")
            break

# Função para aguardar o ACK de um fragmento específico
# Retorna True se ACK correto recebido, False se timeout
# O socket deve estar em modo não-bloqueante para timeout
def wait_for_ack(client_socket, arquivo_id, num_pacote, timeout=1.0):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            ack_data, _ = client_socket.recvfrom(BUFFER_SIZE)
            ack_str = ack_data.decode(errors='ignore')
            ack_parts = ack_str.split('|')
            if len(ack_parts) != 4:
                continue
            if ack_parts[0] != 'ACK':
                continue
            if ack_parts[1] != arquivo_id or ack_parts[2] != str(num_pacote):
                continue
            # Verifica o checksum do ACK
            ack_base = f"ACK|{ack_parts[1]}|{ack_parts[2]}"
            ack_checksum = zlib.crc32(ack_base.encode('utf-8'))
            if ack_checksum != int(ack_parts[3]):
                continue
            return True
        except BlockingIOError:
            time.sleep(0.01)
            continue
        except Exception:
            continue
    return False

# Função de envio de mensagens do cliente, implementando RDT 3.0 para envio
def send_message(client_socket):
    while True:
        message = input("Digite a mensagem para enviar: ")
        path = write_message(message)
        try:
            fragments = Fragmentation(path)
            # Para cada fragmento, envie e aguarde o ACK
            for fragment in fragments:
                # Extrai ID e número do pacote do fragmento
                # O fragmento é: checksum|ID|SEQ|TOTAL|FLAG|<dados>
                frag_str = fragment.decode(errors='ignore')
                parts = frag_str.split('|', 6)
                if len(parts) < 6:
                    continue
                arquivo_id = parts[1]
                num_pacote = parts[2]
                while True:
                    client_socket.sendto(fragment, (SERVER_IP, SERVER_PORT))
                    # Coloca o socket em modo não-bloqueante para timeout
                    client_socket.setblocking(False)
                    ack_ok = wait_for_ack(client_socket, arquivo_id, num_pacote, timeout=1.0)
                    client_socket.setblocking(True)
                    if ack_ok:
                        break
                    else:
                        print(f"Timeout ou ACK incorreto para pacote {num_pacote}, reenviando...")
        except Exception as e:
            print(f"Erro ao enviar mensagem: {e}")
            break
        finally:
            os.remove(path)

if __name__ == "__main__":
    # Cria o socket UDP do cliente
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.bind(('', 0))  
    # Inicia thread para receber mensagens
    threading.Thread(target=receive_message, args=(client_socket,), daemon=True).start()
    # Loop principal de envio
    send_message(client_socket)