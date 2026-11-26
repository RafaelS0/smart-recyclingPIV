# GRAVAR OS EQUIPAMENTOS — versão 17/11/2026

Este pacote é para os equipamentos. O site/API já estão na VPS em https://mrvbot.com/smart_recycling/.
Não instale o serviço do Raspberry na VPS. Não precisa mudar DNS ou substituir outros sites.

## 1. Configure a chave e o Wi-Fi no computador

Abra um terminal na pasta extraída e execute:

```sh
python -m pip install platformio==6.1.19
python tools/configurar_dispositivos.py --component esp32
python tools/configurar_dispositivos.py --component pi
```

O configurador do ESP32 acadêmico solicita o nome e a senha do Wi-Fi 2,4 GHz. O configurador do Pi lê a chave do protocolo v1 da pasta privada `Downloads/smart-recycling-configuracao-privada/device.json`. A chave foi obtida da VPS sem alterá-la; esse arquivo NÃO está no ZIP. Em outro computador, informe a chave privada quando solicitada.

São criados secrets.h para ESP32 e device.env para o Pi. Nunca envie esses arquivos ao Git, a sites ou a grupos. A senha do painel não é a chave de dispositivo. Não altere a chave global na VPS sem atualizar as placas já configuradas.

## 2. Pinagem da montagem escolhida

O usuário confirmou em 17/11/2026 o uso da proposta. Os números abaixo são o perfil de montagem deste pacote — conferem com config.h, mas não constituem medição da fiação já montada.

| Conexão | Mega 2560 | Outro lado |
|---|---|---|
| IR digital | D9 | Saída digital do módulo |
| TCS230 S0/S1/S2/S3/OUT | D4/D5/D6/D7/D8 | Pinos do TCS230 |
| Indutivo | D22 | Saída condicionada/isolada; active LOW, entrada com pull-up |
| HC-SR04 objeto TRIG/ECHO | D24/D25 | Sensor de presença do objeto |
| HC-SR04 orgânicos TRIG/ECHO | D26/D27 | Sensor da lixeira orgânica |
| HC-SR04 recicláveis TRIG/ECHO | D28/D29 | Sensor da lixeira reciclável |
| HX711 orgânicos DT/SCK | D30/D31 | Conversor da célula orgânica |
| HX711 recicláveis DT/SCK | D32/D33 | Conversor da célula reciclável |
| UART1 para ESP32 | TX1=D18, RX1=D19 | ESP32 RX=16, TX=17, com conversão de nível |
| UART2 para Pi | TX2=D16, RX2=D17 | USB–TTL 3,3 V RX/TX, com conversão de nível |
| Referência UART | GND | GND do circuito/adaptador conforme montagem |
| Câmera | — | USB do Raspberry Pi 3 |

Não confunda D16/D17 do MEGA (link Pi) com GPIO16/GPIO17 do ESP32 (link Mega). TX cruza com RX. A porta USB usada para gravar o Mega é Serial/USB de diagnóstico, não Serial2 da IA.

Mega opera com lógica 5 V. ESP32/Pi usam 3,3 V: use conversão de nível. A saída industrial do LJ12A3 precisa de condicionamento/isolação adequado, nunca conexão direta de 12 V ao GPIO. Confirme a variante NPN/PNP antes da ligação. Sensores e motores precisam de alimentação apropriada.

Servo D44 e A4988 STEP/DIR/ENABLE D35/D36/D37 ficam somente RESERVADOS para o controlador local validado. Não são acionados por este firmware. Nenhum sensor de movimento da esteira foi informado; o estado da esteira permanece desconhecido. A parada física não depende da VPS.

## 3. Grave Mega e ESP32

Identifique as portas reais no computador (COM5/COM6 abaixo são só exemplos):

```sh
python tools/gravar.py mega --porta COM5
python tools/gravar.py esp32 --porta COM6
```

Em Linux, use /dev/ttyACM0 ou /dev/ttyUSB0 conforme os dispositivos reais. O script compila antes de gravar e não escolhe a porta por adivinhação.

ESP32 novo: inicialize uma única vez a partição da fila:

```sh
python tools/gravar.py esp32 --porta COM6 --inicializar-fs
```

ATENÇÃO: uploadfs apaga a fila de eventos. Use apenas em placa nova/vazia. Uma atualização normal usa o comando sem --inicializar-fs.

Prefere Arduino IDE? Abra os sketches em:
- firmware/arduino-ide/SmartRecycling_Mega/SmartRecycling_Mega.ino
- firmware/arduino-ide/SmartRecycling_ESP32/SmartRecycling_ESP32.ino

Bibliotecas: ArduinoJson 6.21.5; HX711 0.7.5 no Mega. ESP32: core Espressif 2.0.17, placa ESP32 Dev Module (WROOM/ESP32 clássico), equivalente ao ambiente PlatformIO compilado. A geração dos sketches evita a reescrita automática de protótipos na aplicação C++. O caminho PlatformIO é o caminho de compilação verificado. A inicialização LittleFS continua necessária.

## 4. Calibre antes de confiar nos valores

No monitor USB do Mega a 115200 baud:
- R imprime leituras reais e valores brutos do HX711, sem criar classificação.
- C solicita uma classificação de um objeto real posicionado na câmera/sensores.

O Mega amostra os sensores a cada 10 s. O modo acadêmico do ESP32 envia distância e estado dos componentes em ciclos de aproximadamente 60 s. Essas atualizações ficam fora do contador de classificações. A contagem automática fica desativada até ajustar a distância de presença/liberação ao posicionamento físico; depois, habilite AUTOMATIC_OBJECT_TRIGGER em config.h e recompile.

Peso: defina SCALE e ZERO_OFFSET de cada HX711 usando lixeira vazia e massa conhecida. Fator zero mantém peso indisponível, não peso zero.
Ocupação: meça distância da lixeira vazia e da marca de cheia e configure EMPTY_CM/FULL_CM separadamente.
Cor: os valores branco/preto do repositório são referências; valide e habilite COLOR_CALIBRATION_CONFIRMED. Regras do classificador não são ativadas com limiares zerados. Consulte docs/INTEGRACAO.md.

## 5. Modelo real da IA

O repositório techSash contém treinamento, mas não os pesos já treinados. Nenhum modelo foi inventado no pacote. Treine em um computador com o dataset ou converta os pesos reais da equipe:

```sh
python -m pip install -r firmware/training/requirements.txt
python firmware/training/train.py --dataset DATASET --output treino-01 --epochs 50
# Ou, se a equipe já possui pesos compatíveis:
python firmware/training/export.py --model best_waste_classifier.h5 --output export-modelo-01 --input-scale 1.0
```

O resultado precisa conter waste.tflite + manifest.json, com RGB 60x30, ordem O=orgânico/R=reciclável e o pré-processamento correspondente ao treinamento. Não instale TensorFlow de treinamento na VPS compartilhada. Sem modelo/calibração, o sistema informa indefinido; isso não é uma classificação válida da IA.

## 6. Instale no Raspberry Pi 3

Use Raspberry Pi OS 64-bit, Python 3.11 e a câmera USB. Copie firmware/raspberry_pi/ (incluindo o device.env PRIVADO gerado no passo 1) para o Pi, por exemplo em ~/smart-recycling-pi/. Copie também os pesos/manifesto reais.

```sh
cd ~/smart-recycling-pi
# Instalar sem iniciar enquanto prepara o modelo:
sudo python3 install.py --config ./device.env
# Quando os arquivos reais estiverem disponíveis, instalar/iniciar:
sudo python3 install.py --config ./device.env --model ./waste.tflite --manifest ./manifest.json --start
sudo journalctl -u smart-recycling-device -f
```

O instalador verifica ARM64 e recusa execução na VPS x86/Windows; cria somente o serviço smart-recycling-device. Porta padrão /dev/ttyUSB0 corresponde ao USB–TTL conectado à Serial2 do Mega. Ajuste SERIAL_PORT/CAMERA_INDEX no arquivo privado antes da instalação, se necessário.

Com o worker parado, confira sem gravar qualquer evento:

```sh
sudo systemctl stop smart-recycling-device
sudo /opt/smart-recycling-device/.venv/bin/python /opt/smart-recycling-device/preflight.py --config /etc/smart-recycling-device.env
sudo systemctl start smart-recycling-device
```

O preflight verifica HTTPS, chave, pesos, runtime, captura da câmera e abertura serial. A abertura serial, sozinha, não comprova o circuito elétrico ou o handshake. Use --sem-hardware somente para verificar API/chave sem o Pi/câmera. Nenhuma classificação ou heartbeat é criado pelo preflight.

## 7. Confira a operação na VPS

Faça login em https://mrvbot.com/smart_recycling/. O ESP32 terá que mostrar entrega HTTPS no USB; o Pi terá heartbeat; os sensores aparecem após o Mega enviar quadros válidos. Dispositivo conectado não significa modelo/câmera calibrados.

Coloque um objeto real e envie C no USB do Mega: ele solicita inferência ao Pi, confere o object_id, faz a fusão e envia um único evento pela UART ao ESP32. O ESP32 persiste o evento, envia por HTTPS e repete com a mesma identidade se houver falha. A API deduplica. A perda antes de gravar a fila ESP32 ainda pode perder amostra; o link serial atual não tem ACK persistente no Mega.

O modo acadêmico envia JSON por HTTPS com Content-Type: application/json.
- POST /api/eventos recebe os campos diretos da classificação, incluindo event_id e material.
- POST /api/lixeiras recebe timestamp, organicos_cm e reciclaveis_cm. Cada distância aceita null.
- POST /api/dispositivos recebe timestamp e os seis estados do indutivo, cor, IR, Raspberry e servos.
- GET /api/resumo, /api/eventos?limite=50&pagina=1, /api/historico?intervalo=hora, /api/lixeiras e /api/dispositivos: sessão do painel.

Os três POSTs acadêmicos recebem JSON simples sem chave e sem login. Consulte docs/API_ACADEMICA.md para copiar os exemplos. O protocolo v1 segue disponível para quem precisa de peso, percentual calibrado ou metadados adicionais e usa uma chave. Para habilitá-lo no ESP32, ajuste ACADEMIC_ENDPOINTS para false em config.h e execute o configurador com --versionado. Use --versionado também na atualização de uma placa que ainda tenha eventos v1 na fila.

A VPS preserva PostgreSQL, dados existentes, domínios e serviços. O SQLite do documento é a arquitetura de referência do protótipo, não uma instrução para apagar o banco da VPS.

## O que foi testado e o que depende da bancada

Compilação Mega/ESP32, testes de API/deduplicação, compatibilidade das rotas, scripts em modo dry-run, configurações privadas e adaptadores de IA com interpretador de teste. Testes PostgreSQL separados do banco de produção.
Não foram feitos upload físico às placas, ensaios elétricos, calibração, inferência de pesos reais ou testes dos atuadores. Não afirme integração física concluída antes dessas verificações.
