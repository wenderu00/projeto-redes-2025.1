# projeto-redes-2025.1
# Implementação do Protocolo de Transferência de Dados Confiável (RDT 3.0)

## Integrantes
* Eduardo Teles
* Lucas Angeli Occenstein
* Márcio Wendell

O projeto implementa um serviço de chat sobre UDP, garantindo a entrega confiável de mensagens através da aplicação dos mecanismos do protocolo RDT 3.0. A seguir, detalham-se os componentes técnicos da solução.

## 1. Estrutura do Pacote e Cabeçalho

Para gerenciar a fragmentação e a confiabilidade, foi definido um cabeçalho customizado que precede o payload de dados em cada pacote UDP. O formato é o seguinte:

`CHECKSUM|UUID|SEQ_NUM|TOTAL_PACKETS|END_FLAG|PAYLOAD`

* **CHECKSUM**: Um valor `zlib.crc32` calculado sobre o restante do cabeçalho e o `PAYLOAD`. É usado para detecção de corrupção de bits.
* **UUID**: Um identificador único universal para a mensagem completa, permitindo que o receptor agrupe fragmentos que pertencem à mesma transmissão.
* **SEQ_NUM**: O número de sequência do fragmento (iniciado em 0), essencial para a reordenação e detecção de pacotes duplicados.
* **TOTAL_PACKETS**: O número total de fragmentos que compõem a mensagem.
* **END_FLAG**: Uma flag (0 ou 1) que indica se o fragmento é o último da sequência, sinalizando o fim da mensagem.
* **PAYLOAD**: O fragmento dos dados da mensagem.

## 2. Mecanismos de Confiabilidade

### a. Detecção de Erros (Checksum)

* **Envio**: Antes de transmitir um pacote, o remetente calcula o `zlib.crc32` sobre o cabeçalho (sem o campo de checksum) e o payload. O resultado é inserido no início do pacote.
* **Recebimento**: Ao receber um pacote, o receptor extrai o checksum, recalcula-o com base no resto do pacote e compara os dois valores. Se houver divergência, o pacote é considerado corrompido e descartado.

### b. Feedback (ACKs e NAKs implícitos)

O sistema utiliza pacotes de confirmação (ACK) para notificar o remetente sobre o recebimento bem-sucedido de um fragmento.

* O formato do ACK é: `ACK|UUID|SEQ_NUM|CHECKSUM`.
* Quando um pacote corrompido é recebido, o receptor reenvia o ACK do último pacote válido recebido para aquela mensagem (identificada pelo UUID). Esse ACK duplicado funciona como um NAK (Negative Acknowledgement) implícito, sinalizando ao remetente que o pacote esperado não chegou corretamente.

### c. Retransmissão por Timeout

* O remetente, após enviar cada fragmento, inicia um temporizador (timeout de 1.0 segundo).
* O socket é configurado como não-bloqueante (`setblocking(False)`) para permitir a espera pelo ACK sem travar a execução.
* Se o ACK correspondente ao `SEQ_NUM` enviado não for recebido antes do timeout, o remetente assume a perda do pacote (ou do ACK) e retransmite o mesmo fragmento.

### d. Tratamento de Duplicidade e Perda

* **Número de Sequência**: O `SEQ_NUM` no cabeçalho permite ao receptor identificar e descartar pacotes duplicados, que podem ocorrer devido à retransmissão por timeouts prematuros ou perda de ACKs.
* **Retransmissão de ACK**: Se o receptor recebe um pacote com `SEQ_NUM` superior ao esperado, ele detecta uma perda e continua reenviando o ACK do último pacote em ordem recebido, até que o fragmento perdido seja retransmitido e chegue corretamente.

## 3. Fluxo Operacional

* **Fragmentação**: Uma mensagem é dividida em múltiplos pacotes pela função `Fragmentation()`, que gera o cabeçalho completo para cada um.
* **Envio Confiável (Sender)**:
    * Um loop itera sobre cada fragmento.
    * O fragmento é enviado e um timeout é iniciado.
    * O sender aguarda um ACK com o `UUID` e `SEQ_NUM` correspondentes.
    * Em caso de timeout ou recebimento de um ACK incorreto/duplicado, o fragmento é reenviado.
    * O processo avança para o próximo fragmento apenas após o recebimento do ACK correto.
* **Recebimento Confiável (Receiver)**:
    * Ao receber um pacote, o checksum é validado.
    * Se inválido, o pacote é descartado e o último ACK válido para aquele `UUID` é reenviado.
    * Se válido, o `SEQ_NUM` é verificado. Se for o esperado, o payload é processado, um novo ACK é enviado e o `SEQ_NUM` esperado é incrementado.
    * Se o `SEQ_NUM` for de um pacote já recebido (duplicado), o payload é descartado, mas o ACK correspondente é reenviado para garantir que o remetente avance.

Essa arquitetura garante que as mensagens sejam entregues de forma íntegra, ordenada e completa, superando as limitações inerentes ao protocolo UDP.

## 4. Tutorial de Uso

### Inicialização

* **Servidor**: Para inicializar o servidor, utilize o seguinte comando no terminal:
    ```
    python server.py
    ```
* **Cliente**: Para inicializar o cliente, utilize o seguinte comando no terminal:
    ```
    python client.py
    ```

### Comandos do Chat

* **Conexão**: Para se conectar ao chat, envie a mensagem:
    ```
    hi, meu nome eh NOME
    ```
    Substitua `NOME` pelo seu nome de usuário.
* **Desconexão**: Para sair do chat, envie a mensagem:
    ```
    bye
    
