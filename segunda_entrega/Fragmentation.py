import math
import uuid
import zlib


def Fragmentation(txt_archive_path):
    """
    Fragmenta o conteúdo de um arquivo texto em múltiplos pacotes UDP, cada um com cabeçalho próprio.
    O cabeçalho contém:
      - checksum: verificação de integridade do pacote
      - ID da mensagem (UUID): identifica o conjunto de pacotes de uma mesma mensagem
      - número do pacote: ordem do fragmento
      - total de pacotes: quantos fragmentos compõem a mensagem
      - flag de fim: 1 se for o último pacote, 0 caso contrário
    O formato do cabeçalho é:
      <CHECKSUM>|<ID>|<SEQ>|<TOTAL>|<FLAG>|<DADOS>
    """
    # Tamanho máximo do pacote UDP
    BUFFER_SIZE = 1024
    # Reserva espaço para o cabeçalho (estimado em 128 bytes)
    payload_size = BUFFER_SIZE - 128

    # Lê o conteúdo do arquivo texto
    with open(txt_archive_path, 'r', encoding='utf-8') as file:
        file_content = file.read()

    # Converte o conteúdo para bytes
    file_content_bytes = file_content.encode('utf-8')
    file_size = len(file_content_bytes)

    # Se o arquivo estiver vazio, retorna lista vazia
    if file_size == 0:
        return []

    # Calcula o número total de pacotes necessários
    total_packets = math.ceil(file_size / payload_size)
    packets_to_send = []
    packet_Num = 0
    # Gera um UUID para identificar a mensagem
    arquive_id = str(uuid.uuid4())

    # Fragmenta o conteúdo em pacotes
    for i in range(0, file_size, payload_size):
        chunk = file_content_bytes[i:i + payload_size]
        # Flag de fim: 1 se for o último pacote, 0 caso contrário
        flag_end = 1 if packet_Num == total_packets - 1 else 0
        # Monta o cabeçalho sem o checksum
        header_str = f"{arquive_id}|{packet_Num}|{total_packets}|{flag_end}|"
        header_bytes = header_str.encode('utf-8')
        # Calcula o checksum sobre cabeçalho + chunk
        checksum = zlib.crc32(header_bytes + chunk)
        # Cabeçalho final: checksum + cabeçalho + chunk
        full_header_str = f"{checksum}|{header_str}"
        final_packet = full_header_str.encode('utf-8') + chunk
        packets_to_send.append(final_packet)
        packet_Num += 1
    return packets_to_send
