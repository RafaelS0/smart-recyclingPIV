# Integração física — Smart Recycling

## O que foi adaptado

Fontes examinadas em 16–17/11/2026:
- Documento da equipe: https://docs.google.com/document/d/1Xp4Oc-URVvYnerThbXe_YUCzz_PsSz-oI8dqQ3h-PAw/edit (v0.1; diagrama serial Mega/Pi/ESP32 e transporte HTTP).
- Guia direto de gravação e instalação: docs/COMECE_AQUI.md.
- https://github.com/RafaelS0/smart-recyclingPIV — commit `4a12454a6a9c4b7710326f13c7dd3ec7c1ca5fdb`.
- https://github.com/techSash/Waste-classification — commit `68339005d1d5f6e769c0ed15f58a9b7cd366edc7` (Apache-2.0).

O primeiro repositório fornece IR/TCS230 e a referência da dashboard. As regras em classificador.ino ainda usam limiares zerados. O segundo fornece o notebook de treinamento, sem arquivo de pesos treinados. Esta adaptação preserva os pinos publicados, exige calibração explícita e inclui treino/exportação modernos. Nenhum modelo treinado nem dataset está incluído.

A dashboard publicada usa Next.js App Router, React/TypeScript, Server Components, carregamento inicial autenticado no servidor, navegação Painel/Histórico, estados de carregamento/erro, WebSocket e gráficos Recharts carregados sob demanda. FastAPI/PostgreSQL continuam sendo a única fonte persistente de dados.

## Fluxo e responsabilidades

Sensores → Mega (aquisição e fusão) → UART1 com CRC32 → ESP32 (fila LittleFS, HTTPS/TLS) → API → PostgreSQL → WebSocket → Next.js.

Câmera USB → Raspberry Pi (TFLite) ↔ UART2 do Mega. O Mega solicita uma sessão ao Pi (hello/session) e inclui o identificador de sessão nos pedidos de objeto, evitando reutilizar respostas após reiniciar. O Pi responde somente à solicitação do objeto identificado; não publica uma segunda classificação do mesmo objeto. Um resultado com baixa confiança ou divergência permanece indefinido. O Pi envia heartbeat próprio, sem aumentar contadores.

Este firmware é de aquisição/monitoramento. Não aciona motor ou servo, não altera intertravamentos e não implementa comandos remotos. Preserve/integre separadamente o controlador físico validado. A parada de emergência deve permanecer independente do software e da rede.

## Ligações confirmadas e propostas

| Componente | Ligação | Situação |
|---|---|---|
| IR digital | Mega D9 | Preservada do repositório |
| TCS230 S0/S1/S2/S3/OUT | Mega D4/D5/D6/D7/D8 | Preservada do repositório |
| Mega Serial1 TX | D18 → conversor 5 V/3,3 V → ESP32 RX16 | Proposta configurável |
| ESP32 TX17 | Conversor de nível → Mega RX19 | Reservada; protocolo atual só transmite Mega → ESP |
| Mega Serial2 TX/RX | D16/D17 → conversor de nível → adaptador USB–TTL 3,3 V RX/TX → Pi | Proposta; Pi usa /dev/ttyUSB0 por padrão |
| Terras | Referência GND comum para UART/sensores compatíveis | Verificar isolamento e alimentação da montagem |
| Câmera USB | Porta USB do Pi | Escolher índice CAMERA_INDEX real |
| Indutivo | Mega D22, sinal condicionado active LOW com pull-up | Proposta adotada em 17/11/2026 |
| HC-SR04 objeto / orgânicos / recicláveis TRIG,ECHO | D24/D25 · D26/D27 · D28/D29 | Proposta adotada |
| HX711 orgânicos / recicláveis DT,SCK | D30/D31 · D32/D33 | Proposta adotada; calibrar peso |
| Realimentação física da esteira | -1 (não informada) | Estado permanece desconhecido |
| Servo SG90 e NEMA17/A4988 | Não acionados por estes códigos | Pinagem/controle/intertravamentos pendentes |

Não conecte saída de 5 V do Mega diretamente às entradas de 3,3 V do ESP32/Pi. Não conecte a saída industrial do LJ12A3 diretamente ao GPIO: use interface elétrica adequada à variante real (NPN/PNP e tensão). Use alimentação dimensionada e isolação/conversores de nível apropriados. Os pinos propostos não comprovam a fiação da equipe.

Se usar UART GPIO do Pi no lugar do USB–TTL, configure SERIAL_PORT=/dev/serial0, habilite a UART e desative console serial; confirme TX/RX e conversão de nível. O exemplo preferencial usa USB–TTL para separar a configuração do console do Pi.

## Preparar e compilar o Mega

No computador de desenvolvimento, na raiz do pacote:

```sh
python -m pip install platformio==6.1.19
python -m platformio run -d firmware/mega2560
python -m platformio run -d firmware/mega2560 -t upload --upload-port PORTA_DO_MEGA
python -m platformio device monitor --port PORTA_DO_MEGA --baud 115200
```

Antes do upload, confira a montagem com a tabela do perfil proposto em include/config.h. A proposta foi adotada pelo usuário em 17/11/2026; -1 permanece somente para sinais não informados. Não publique zero para substituir um sensor ausente.

- R no monitor USB: imprime leituras/calibração, sem classificar nem contar objeto.
- C no monitor USB: solicita uma classificação de um objeto real posicionado na área de captura. Não movimenta atuadores.
- Um snapshot de sensores é enviado a cada 10 segundos e não aumenta contadores.
- AUTOMATIC_OBJECT_TRIGGER é false. Só habilite após configurar HC-SR04 do objeto, distâncias de presença/liberação e validar a cadência da esteira. O mecanismo exige liberação antes de contar outro objeto.
- AI_TIMEOUT_MS é configurável (padrão 2500 ms). Meça a latência no Pi 3 antes de definir o tempo de retenção física do objeto.

### Calibração

COLOR_CALIBRATION_CONFIRMED=false por padrão. WHITE_US/BLACK_US foram extraídos de teste_cor.ino, mas precisam ser conferidos na instalação atual. RGB processado fica null até confirmar. Timeout de pulseIn é falha, não canal zero.

SENSOR_RULES_VALIDATED=false por padrão. Defina ORGANIC_MIN_PULSE usando amostras rotuladas e confirme IR_RECYCLABLE_IS_LOW antes de ativar. Sem regras nem IA disponível, a classificação permanece indefinida. Metal detectado pode indicar reciclável somente quando o sensor estiver configurado e eletricamente validado.

Para HX711: configure DT/SCK, leia o valor bruto com lixeira vazia e use-o em ZERO_OFFSET. Aplique massa conhecida e calcule SCALE=(bruto_com_massa - bruto_vazio)/massa_em_gramas. Confirme com outra massa; SCALE pode ser negativo conforme a montagem. Não há tara automática ao reiniciar. Fator zero desabilita peso.

Para ocupação: meça EMPTY_CM e FULL_CM separadamente em cada lixeira. A fórmula é 100*(empty-distance)/(empty-full), limitada a 0–100. É ocupação baseada em distância, não volume/peso validado. Distância do objeto não é reutilizada como distância da lixeira.

## Preparar o ESP32

```sh
python tools/configurar_dispositivos.py --component esp32
python -m platformio run -d firmware/esp32
python -m platformio run -d firmware/esp32 -t upload --upload-port PORTA_DO_ESP32
```

Configure o Wi-Fi localmente com tools/configurar_dispositivos.py --component esp32. O modo acadêmico tem a chave vazia. A opção --versionado também carrega a chave para filas antigas ou para o protocolo v1. O arquivo secrets.h é privado. O certificado público ISRG Root X1 está em tls_ca.h; a cadeia HTTPS do servidor foi verificada com essa raiz. Nunca use setInsecure(). O relógio do ESP32 é sincronizado por NTP.

**Inicialização única do armazenamento:** em placa nova/sem fila, execute `python -m platformio run -d firmware/esp32 -t uploadfs --upload-port PORTA_DO_ESP32`. Isso grava uma imagem LittleFS vazia e APAGA a fila existente. Não repita em produção com eventos pendentes. O firmware não formata automaticamente a memória.

A recepção UART continua em uma tarefa enquanto HTTPS trabalha em outra. Quadros inválidos, incompletos ou sem CRC válido são rejeitados. A fila LittleFS conserva até 64 eventos (incluindo rejeitados); não sobrescreve eventos antigos ao encher. Arquivos temporários interrompidos não são enviados automaticamente. Falhas de gravação/CRC/fila cheia são informadas no USB.

O gateway cria UUIDs e preserva os mesmos IDs e corpos em cada repetição HTTPS. Aguarde a primeira sincronização do relógio do ESP32 antes de classificar no modo acadêmico. O object_id do Mega, usado para correlacionar a resposta do Pi, é preservado em controller_object_id; o object_id persistente recebe o UUID do gateway para evitar colisões após reiniciar o Mega.

HTTP 200/201 confirma a gravação; 400/409/422 leva o arquivo a rejected_ para diagnóstico. 401, perda de rede e falhas temporárias geram espera progressiva, sem imprimir a chave. O upload exige relógio válido. O modo acadêmico começa a enviar após a sincronização inicial do relógio. No modo v1, uma amostra anterior à sincronização pode ter timestamp desconhecido.

O trecho Mega → ESP ainda não tem confirmação/retransmissão persistente no Mega: desconectar a UART ou cortar energia antes de gravar a fila pode perder a amostra. Valide isso em bancada; não confunda persistência HTTPS com garantia absoluta de entrega de ponta a ponta.

## Modelo: treinar ou converter pesos reais

Execute no computador de treinamento, não na VPS compartilhada nem no Pi 3:

```sh
python -m venv .venv-treino
# Ative o ambiente conforme o sistema operacional.
python -m pip install -r firmware/training/requirements.txt
python firmware/training/train.py --dataset DATASET --output treino-01 --epochs 50
```

Obtenha o dataset original com suas condições de uso e atribuição. A estrutura deve conter TRAIN/O, TRAIN/R, TEST/O e TEST/R. O código usa 20% de TRAIN para validação; TEST é reservado para avaliação ao final. Mantém entrada RGB 60x30, seis convoluções, duas camadas densas e ordem O=orgânico/R=reciclável. Não há divisão por 255: o modelo original treina com pixels brutos. A exportação grava esse pré-processamento no manifesto.

Saídas: best.keras, evaluation.json, export/waste.tflite e export/manifest.json. Para pesos já treinados:

```sh
python firmware/training/export.py --model best_waste_classifier.h5 --output export-modelo-01 --input-scale 1.0
```

Use --input-scale 0.00392156862745098 SOMENTE se o seu treinamento efetivamente usou pixels divididos por 255. Formato/ordem das classes e dimensões têm de corresponder. O manifesto inclui SHA256; trocar o modelo exige atualizar os metadados. A confiança não é acurácia; os resultados anunciados pelo autor não comprovam desempenho nesta esteira.

Não foi executado treinamento nem conversão de pesos reais nesta entrega: o dataset/pesos não foram fornecidos. O adaptador foi testado com um interpretador de teste; isso não valida um modelo real.

## Instalar no Raspberry Pi 3

Configuração de referência: Raspberry Pi OS 64-bit, Python 3.11, USB–TTL e câmera USB. A roda ARM64/Python 3.11 do runtime foi verificada no PyPI, mas sua execução no Pi físico continua pendente. Adapte versões se usar outro SO/arquitetura.

```sh
sudo apt update
sudo apt install python3-venv python3-opencv python3-numpy python3-pil
sudo useradd --system --user-group --groups dialout,video --home-dir /opt/smart-recycling-device smart-recycling
sudo install -d -o smart-recycling -g smart-recycling /opt/smart-recycling-device /var/lib/smart-recycling
# Copie os arquivos de firmware/raspberry_pi/ para /opt/smart-recycling-device/.
sudo -u smart-recycling python3 -m venv --system-site-packages /opt/smart-recycling-device/.venv
sudo -u smart-recycling /opt/smart-recycling-device/.venv/bin/python -m pip install -r /opt/smart-recycling-device/requirements.txt
sudo -u smart-recycling /opt/smart-recycling-device/.venv/bin/python -m pip install ai-edge-litert==2.3.0
```

Copie o modelo e manifesto para /opt/smart-recycling-device/models/. Copie device.env.example para /etc/smart-recycling-device.env, preencha a chave e confirme porta serial/câmera. Proteja o arquivo com dono root e modo 600; o systemd lê EnvironmentFile antes de reduzir privilégios. Conceda leitura do código/modelos ao usuário do serviço e escrita apenas no diretório de estado.

```sh
sudo install -m 644 /opt/smart-recycling-device/smart-recycling-device.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now smart-recycling-device
sudo journalctl -u smart-recycling-device -f
```

O serviço valida SHA256 e dimensões do modelo. A câmera é capturada somente para solicitações de objeto; falhas produzem resposta ok=false, nunca uma classificação inventada. Resultados para o mesmo object_id são reutilizados em memória para evitar nova inferência na repetição da solicitação. A fila SQLite persiste heartbeats com repetição idempotente. Sessão/segredos do painel nunca são necessários no Pi.

Se faltarem modelo, runtime, porta ou câmera, corrija a configuração e reinicie o serviço. NTP deve estar ativo no Pi. Antes de integrar a esteira, valide a captura, direção da imagem, área de interesse/iluminação, latência e uma amostra rotulada para cada classe.

## Novo protocolo da API

POST https://mrvbot.com/smart_recycling/api/v1/events
Cabeçalhos: Content-Type: application/json e X-Device-Key: chave privada.

```json
{
  "schema_version": 1,
  "event_id": "UUID-UNICO-DO-EVENTO",
  "device_id": "smart-recycling-esp32-01",
  "timestamp": "2026-11-16T21:00:00Z",
  "type": "classification",
  "data": {
    "device_role": "esp32",
    "object_id": "UUID-UNICO-DO-OBJETO",
    "material": "indefinido",
    "metal": null,
    "organic_weight_g": null,
    "organic_bin_distance_cm": null,
    "fusion": "unavailable",
    "faults": ["ai_unavailable_or_timeout"]
  }
}
```

Exemplo estrutural: não envie os valores ilustrativos à produção. timestamp é o horário de coleta/recepção no gateway em UTC, não um horário gerado novamente a cada tentativa. Pode ser null se desconhecido; essa amostra não é tratada como atual.

- type=telemetry: snapshot; não incrementa contadores.
- type=heartbeat: presença; não incrementa contadores nem atualiza medições.
- type=classification: exige material e object_id; incrementa uma vez.
- Repetição exata do mesmo event_id: HTTP 200, duplicate=true.
- Novo evento: HTTP 201, duplicate=false.
- ID reutilizado com outro conteúdo ou outro evento para o mesmo device_id/object_id: HTTP 409.
- Payload inválido: HTTP 422; timestamp futuro em mais de 5 minutos é rejeitado.
- Credencial inválida: HTTP 401.
- Campos extra são rejeitados. Esquema completo: hardware-event.schema.json e /smart_recycling/docs.

GET /api/v1/devices usa sessão do painel e informa a comunicação dos dispositivos vistos nos últimos 60 segundos. Não pressupõe que sensor ou Arduino estejam conectados apenas porque o ESP32 envia heartbeat.

As tabelas hardware_events e hardware_devices são adicionais. Os registros anteriores permanecem intactos. /api/overview e /api/readings combinam os eventos novos com o legado. Leituras do endpoint antigo /api/telemetry continuam contando por POST; prefira o novo protocolo para evitar contagem periódica. Eventos buffered antigos não substituem uma medição de origem mais recente. Dados atuais dependem de timestamp válido e idade menor que 60 segundos.

## Testes e validação

Executados: build de produção Next.js + TypeScript; navegador desktop/mobile; compilação Mega e ESP32; criação da imagem LittleFS; testes de API com dados isolados, deduplicação, campos inválidos, timestamps, WebSocket e separação entre heartbeat/telemetria/classificação; testes de CRC/framing, persistência/repetição e pré-processamento da IA com interpretador de teste.

Não executados: upload às placas, leitura dos sensores físicos, captura da câmera real, treinamento com dataset, exportação/inferência de pesos reais, acionamento de motores/servo e ensaios de segurança física. A comunicação real dos equipamentos ainda não foi comprovada.

Na bancada, começar sem motor: enviar R, confirmar leituras reais, validar HTTPS, posicionar objeto e enviar C, verificar exatamente um registro, interromper Wi-Fi e confirmar a repetição com mesmo event_id, testar reinício da fila, desconectar sensores e conferir null/falhas, só depois integrar ao controlador físico validado.

A fila é limitada e o hardware pode perder eventos antes de persistir. Mantenha retenção/backup do PostgreSQL e monitore espaço livre. A credencial de dispositivo ainda é compartilhada; separar credenciais por dispositivo é uma evolução pendente.

## Documento da equipe e pacote para gravação (17/11/2026)

A pinagem de monitoramento proposta foi adotada por confirmação do usuário. Veja COMECE_AQUI.md para comandos simplificados, projetos Arduino IDE, configurador privado e instalador do Pi. Calibração e pesos do modelo ainda não foram fornecidos/validados.

As três rotas acadêmicas recebem JSON simples sem chave. Exemplos e comportamento do modo acadêmico estão em docs/API_ACADEMICA.md. O ESP32 usa esse modo por padrão. O protocolo v1 é opcional para o ESP32 e continua atendendo o heartbeat do serviço do Pi.

GET /api/device/verify valida a chave sem gravar presença/telemetria. As consultas exigem a sessão do painel. O protocolo v1 usa X-Device-Key. O banco PostgreSQL instalado foi preservado; não foi substituído pelo SQLite do protótipo.

Os projetos .ino gerados foram compilados também pelo pipeline Arduino/PlatformIO nas mesmas versões de placa/bibliotecas. O runtime ai-edge-litert instalado pelo assistente tem prioridade sobre versões antigas de tflite_runtime para os modelos exportados no TensorFlow atual. O instalador do Pi e a captura física ainda exigem execução no equipamento.
