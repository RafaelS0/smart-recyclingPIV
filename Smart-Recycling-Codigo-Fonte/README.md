# Smart Recycling

Painel de monitoramento IoT com Next.js 16, React 19, TypeScript, Recharts, FastAPI e PostgreSQL 16. Dashboard baseada na referência visual da equipe; dados reais e estados explícitos de ausência/desatualização.

Produção: https://mrvbot.com/smart_recycling/ (login existente preservado).

## Recursos

- Dashboard Next.js com renderização autenticada no servidor, navegação Painel/Histórico, carregamento/erro e atualização WebSocket com reconexão.
- Última classificação, sensores, ocupação/peso/distância por lixeira, distribuição e evolução das últimas 200 classificações.
- Login de 8 horas com cookie Secure/HttpOnly/SameSite e logout com revogação.
- API legada preservada; protocolo novo com eventos separados de telemetria, heartbeat e classificação, UUID e deduplicação por dispositivo/objeto.
- Firmware Mega, ESP32 e serviço Raspberry Pi; scripts de treino e exportação TensorFlow Lite baseados nos repositórios da equipe.
- Tutorial da API e guia de hardware no painel, com pacote de código para download autenticado.

## Estrutura

- frontend/: Next.js App Router, componentes e acesso autenticado no servidor.
- app/: FastAPI, contrato de hardware e páginas de login/documentação.
- firmware/mega2560/: IR/TCS230 com pinagem original, sensores opcionais e fusão com IA.
- firmware/esp32/: UART com CRC, fila LittleFS, HTTPS com validação TLS.
- firmware/raspberry_pi/: captura USB, inferência sob solicitação, resposta serial e heartbeat persistente.
- firmware/training/: treino, avaliação e conversão de pesos reais para TFLite; licença/atribuição incluídas.
- docs/INTEGRACAO.md: ligações, instalação, calibração, protocolo e pendências.
- tests/: testes isolados e verificações de navegador.
- infrastructure/: configurações e ferramentas de implantação.

## Implantação Ubuntu

Para instalação nova, com Docker Engine/Compose já disponíveis:

```sh
python3 infrastructure/init_env.py
docker compose -p smart-recycling up -d --build db api frontend
docker compose -p smart-recycling ps
```

Não recrie .env na VPS já instalada: preserva credenciais e banco. API usa loopback 18080; Next.js usa loopback 18081; PostgreSQL não publica porta. Configure HTTPS e proxy de subcaminho conforme infrastructure/smart-recycling.nginx.conf, incluindo o snippet somente no domínio desejado. Faça backup e nginx -t antes de recarregar; não substitua os virtual hosts existentes. Nenhum comando down -v é necessário.

A instalação está configurada para /smart_recycling e cookies HTTPS. A página não deve ser exposta diretamente por HTTP sem proxy. Para o frontend isolado: `npm ci` e `npm run build` em frontend/; API_INTERNAL_URL deve apontar para o FastAPI. Não inclua chaves do equipamento no frontend.

O simulador está em perfil development e desabilitado por padrão. Não o execute contra a produção.

## APIs

Autenticação humana: POST /api/auth/login, POST /api/auth/logout (sessão).
Consulta: GET /api/overview, GET /api/readings?limit=200, GET /api/v1/devices.
Dispositivos: POST /api/v1/events, com X-Device-Key.
Legado: POST /api/telemetry, ainda disponível com contagem por leitura.
Tempo real: /ws, autenticado pelo cookie da sessão.
Referência: /docs e /openapi.json, após login.

As URLs públicas têm o prefixo https://mrvbot.com/smart_recycling. Use o novo protocolo nos firmwares para não aumentar contagens com snapshots periódicos. O esquema completo está em docs/hardware-event.schema.json.

## Testes

```sh
python -m pip install -r app/requirements.txt
python -m pip install httpx numpy Pillow
python tests/test_smoke.py
python tests/test_hardware_api.py
python tests/test_device_adapters.py
python -m platformio run -d firmware/mega2560
python -m platformio run -d firmware/esp32
```

Os testes de API usam banco temporário isolado. Os testes de adaptador de IA injetam um interpretador de teste; não comprovam inferência de pesos reais. Testes de navegador precisam de Playwright e um arquivo local de acesso, que não é distribuído.

## Limites reais

A proposta de pinagem de monitoramento foi adotada pelo usuário em 17/11/2026: veja docs/COMECE_AQUI.md. Estado físico da esteira segue -1 por ausência de realimentação informada. Sem calibração validada, canais processados/regras permanecem desabilitados. Não há pesos treinados no repositório original: treine ou forneça o modelo real. Nenhuma leitura, câmera ou atuador físico foi validado remotamente. Motores/servo e comandos remotos permanecem fora deste firmware de monitoramento; preserve o controlador local e seus intertravamentos.

Leia docs/INTEGRACAO.md antes de conectar ou gravar placas. Entradas ESP32/Pi não toleram 5 V. A inicialização LittleFS apaga fila e deve ser feita apenas em placa nova/vazia. O trecho UART ainda não oferece confirmação/persistência no Mega; falhas antes de gravar a fila podem perder dados.

## Pacote para gravar os equipamentos

Leia docs/COMECE_AQUI.md. Execute python tools/configurar_dispositivos.py no computador para gerar os arquivos privados; depois tools/gravar.py para Mega/ESP32. O Raspberry tem install.py e preflight.py próprios. Os sketches Arduino IDE estão em firmware/arduino-ide/. O pacote das placas não inclui senha do Wi-Fi, chave de produção nem pesos fictícios. Rotas em português do documento v0.1 foram implementadas como compatibilidade sobre a API existente, sem trocar o PostgreSQL da VPS.

## API acadêmica

Os POSTs /api/eventos, /api/lixeiras e /api/dispositivos aceitam JSON simples sem chave ou sessão. O ESP32 usa essas rotas por padrão e envia atualização das lixeiras a cada 60 segundos. Exemplos em docs/API_ACADEMICA.md.
