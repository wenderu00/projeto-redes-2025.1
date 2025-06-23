import math
import uuid

def Fragmentation(txt_archive_path):
    """
    A função lê um arquivo de texto, o fragmenta em múltiplos pacotes e
    adiciona um cabeçalho a cada um para depois reconstruir.
    Retorna uma lista de pacotes em bytes, prontos para serem enviados.
    """
    
    # Define o tamanho máximo de cada pacote UDP em bytes.
    BUFFER_SIZE = 1024
    # Reserva um espaço para o cabeçalho. O payload = buffer_size - header_size.
    payload_size = BUFFER_SIZE - 128

    # Abre o arquivo de texto especificado no modo de leitura ('r') com codificação UTF-8..
    with open(txt_archive_path, 'r', encoding='utf-8') as file:
        # Lê o arquivo linha por linha e transforma tudo em uma única string.
        file_content = ''
        line = file.readline()
        while line:
            file_content += line
            line = file.readline()
    
    # Converte a string do conteúdo do arquivo para uma sequência de bytes usando UTF-8.
    file_content_bytes = file_content.encode('utf-8')
    # Calcula o tamanho total do arquivo em bytes.
    file_size = len(file_content_bytes)

    # Se o arquivo estiver vazio, retorna uma lista vazia para evitar erros.
    if file_size == 0:
        return []
    
    # Calcula o número total de pacotes necessários.
    # Usa math.ceil para arredondar para cima
    total_packets = math.ceil(file_size / payload_size)
    
    # Lista vazia que irá armazenar todos os pacotes finais.
    packets_to_send = []
    
    # Contador para o número sequencial de cada pacote, começando em 0.
    packet_Num = 0 
    
    # Gera um ID único e universal (UUID) para este conjunto de pacotes para diferenciar cada mensagem.
    arquive_id = str(uuid.uuid4())

    # Itera sobre os bytes do arquivo em "saltos" do tamanho do payload.
    # 'i' será o índice de início de cada fatia de dados.
    for i in range(0, file_size, payload_size):
        
        # Pega a fatia (chunk) de dados do arquivo, do início 'i' até 'i + payload_size'.
        chunk = file_content_bytes[i:i + payload_size]
        
        # Verifica se este é o último pacote da sequência.
        if packet_Num == total_packets - 1:
            # Se for o último, a flag de finalização é 1.
            flag_end = 1
        else:
            # Se não, a flag é 0.
            flag_end = 0
        
        # Monta o cabeçalho como uma string formatada (f-string).
        # Formato: ID_DO_ARQUIVO|NUMERO_DO_PACOTE|TOTAL_DE_PACOTES|FLAG_DE_FIM|
        header_str = f"{arquive_id}|{packet_Num}|{total_packets}|{flag_end}|"

        # Converte a string do cabeçalho para bytes e a concatena com o chunk de dados (que já está em bytes).
        final_packet = header_str.encode('utf-8') + chunk

        # Adiciona o pacote completo e pronto para envio à nossa lista.
        packets_to_send.append(final_packet)

        # Incrementa o contador do número do pacote para a próxima iteração.
        packet_Num += 1
        
    # Retorna a lista completa de pacotes.
    return packets_to_send
