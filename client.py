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

# Variáveis para controle de ACKs recebidos
received_acks = {}
acks_lock = threading.Lock()

# Função utilitária para salvar mensagens em arquivo temporário (usado para fragmentação)
def write_message(message):
    path_name = f"user_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.txt"
    with open(path_name, "w", encoding="utf-8") as file:
        file.write(message)
    return path_name

# Função que recebe mensagens do servidor e implementa o RDT 3.0 para recebimento
def receive_message(client_socket):
    last_ack_sent = {}
    while True:
        try:
            data, sender_addr = client_socket.recvfrom(BUFFER_SIZE)
            data_str = data.decode(errors='ignore')

            if data_str.startswith('ACK|'):
                with acks_lock:
                    ack_parts = data_str.split('|')
                    if len(ack_parts) != 4:
                        continue
                    
                    _, arquivo_id, num_pacote, received_ack_checksum = ack_parts

                    ack_base = f"ACK|{arquivo_id}|{num_pacote}"
                    ack_checksum = zlib.crc32(ack_base.encode('utf-8'))

                    if str(ack_checksum) == received_ack_checksum:
                        received_acks[(arquivo_id, num_pacote)] = True
                    else:
                        print("[AVISO] Checksum de ACK inválido. Pacote ignorado.")
                continue

            print(f"[RECEBIDO] Pacote recebido de {sender_addr} ({len(data)} bytes)")
            split_idx = data_str.find('|')
            if split_idx == -1:
                print('[ERRO] Pacote de dados mal formatado (sem checksum).')
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
                print('[ERRO] Cabeçalho do pacote de dados incompleto.')
                continue

            header_bytes = rest[:header_end]
            chunk = rest[header_end:]
            print('[PROCESSO] Verificando integridade do pacote (checksum)...')
            calc_checksum = zlib.crc32(header_bytes + chunk)

            if calc_checksum != received_checksum:
                print('[ERRO] Pacote corrompido (checksum inválido).')
                continue

            print('[OK] Checksum válido!')
            message = (header_bytes + chunk).decode(errors='ignore')
            message_info = message.split("|", 4)
            message_content = message_info[4]
            arquivo_id = message_info[0]
            num_pacote = message_info[1]
            
            ack_str = f"ACK|{arquivo_id}|{num_pacote}"
            ack_checksum = zlib.crc32(ack_str.encode('utf-8'))
            ack_packet = f"{ack_str}|{ack_checksum}".encode('utf-8')
            print(f"[ENVIO] Enviando ACK para {sender_addr} (ID={arquivo_id}, SEQ={num_pacote})")
            client_socket.sendto(ack_packet, sender_addr)
            last_ack_sent[arquivo_id] = ack_packet

            while message_info[3] == "0":
                print('[PROCESSO] Aguardando próximo fragmento para montagem da mensagem completa...')
                data, sender_addr = client_socket.recvfrom(BUFFER_SIZE)
                data_str = data.decode(errors='ignore')
                
                if data_str.startswith('ACK|'):
                    continue

                split_idx = data_str.find('|')
                if split_idx == -1: continue

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
                if pipe_count < 4: continue

                header_bytes = rest[:header_end]
                chunk = rest[header_end:]
                calc_checksum = zlib.crc32(header_bytes + chunk)

                if calc_checksum != received_checksum:
                    print('[ERRO] Fragmento corrompido.')
                    continue
                
                print('[OK] Fragmento válido!')
                message = (header_bytes + chunk).decode(errors='ignore')
                message_info = message.split("|", 4)
                message_content += message_info[4]
                arquivo_id = message_info[0]
                num_pacote = message_info[1]
                
                ack_str = f"ACK|{arquivo_id}|{num_pacote}"
                ack_checksum = zlib.crc32(ack_str.encode('utf-8'))
                ack_packet = f"{ack_str}|{ack_checksum}".encode('utf-8')
                client_socket.sendto(ack_packet, sender_addr)
                last_ack_sent[arquivo_id] = ack_packet
            
            message = message_content
            print(f"{message}")

        except (ValueError, IndexError) as e:
            print(f"[AVISO] Erro ao processar pacote: {e}. Pacote ignorado.")
            continue
        except Exception as e:
            print(f"Erro crítico na thread de recebimento: {e}")
            break

# Função para aguardar o ACK de um fragmento específico
# Retorna True se ACK correto recebido, False se timeout
# O socket deve estar em modo não-bloqueante para timeout
def wait_for_ack(client_socket, arquivo_id, num_pacote, timeout=1.0):
    start_time = time.time()
    ack_key = (arquivo_id, str(num_pacote))
    while time.time() - start_time < timeout:
        with acks_lock:
            if ack_key in received_acks:
                del received_acks[ack_key]
                return True
        time.sleep(0.01)
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
                    ack_ok = wait_for_ack(client_socket, arquivo_id, num_pacote, timeout=1.0)
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