# Publicacao em producao — 13/11/2026

URL: https://mrvbot.com/smart_recycling/
Acesso: usuario e senha no arquivo local C:/Users/Matheus/Downloads/smart-recycling-acesso.json.

## Infraestrutura
- SSH: root@129.121.38.121, porta 22022, chave SSH existente.
- Projeto: /opt/smart-recycling; Compose: smart-recycling.
- API: 127.0.0.1:18080. PostgreSQL 16 em rede Docker, sem porta publica.
- Volume persistente: smart-recycling_postgres_data.
- Nginx: /etc/nginx/snippets/smart-recycling.conf, incluido no virtual host existente.
- Configuracao anterior e verificacao dos sites: /opt/smart-recycling/backups/.
- Segredos: /opt/smart-recycling/.env; acesso ao painel: access.json no mesmo diretorio.
- Tela de login propria com sessao de 8 horas, cookie Secure/HttpOnly/SameSite e logout com revogacao no banco. Senha com hash scrypt. Painel, consultas, documentacao e WebSocket protegidos. Limite de tentativas de login por IP. Credenciais anteriores mantidas.
- Telemetria usa X-Device-Key separada, em POST /smart_recycling/api/telemetry.
- Simulador nao iniciado; simulacao rejeitada; comandos fisicos bloqueados.

## Operacao
```sh
cd /opt/smart-recycling
docker compose -p smart-recycling ps
docker compose -p smart-recycling logs --tail=100 api
docker compose -p smart-recycling up -d --build api
```
Nao executar down -v: remove o banco persistente.

## Testes executados
- python tests/test_smoke.py: banco SQLite temporario isolado, ausencia de hardware, autenticacao do dispositivo, rejeicao de simulacao, validacao, persistencia, agregacao, notificacao WebSocket e bloqueio de comandos.
- VPS: PostgreSQL healthy; API inicializada; HTTPS e autenticacao; painel, OpenAPI e consultas; rejeicao de telemetria sem chave; handshake WebSocket autenticado via HTTPS.
- Todos os containers preexistentes preservados. Paginas principais de mrvbot.com, vetcolosso.com.br, racoesdafronteira.com.br e miguelvalentim.com.br: HTTP 200 e mesmo SHA256 antes/depois.
- Nenhuma telemetria sintetica inserida no banco de producao.

## Escopo e pendencias
Esta entrega publica o MVP existente com ajustes para producao. Nao implementa integralmente o documento extenso anexado.
Ainda faltam migrations Alembic, deduplicacao por event_id, multiplos usuarios e perfis, auditoria, rate limiting, relatorios CSV/PDF, paginas completas de IA/alertas/historico, MQTT, firmware e backups automaticos do banco.
O protocolo atual continua sendo o Telemetry descrito no README, sem schema_version/event_id. Cada POST registra uma leitura/classificacao; os totais sao contagens dessas leituras, nao uma contagem fisica validada de objetos unicos.
Integracao de Arduino, ESP32, camera e Raspberry Pi nao foi testada nem comprovada. Leituras expiram visualmente em 60 segundos. Confirmação do movimento e intertravamentos dependem de firmware e sensores reais.

## Atualizacao visual e login

Painel responsivo com navegacao, cartoes de indicadores, sensores, lixeiras e eventos. Login dedicado em /smart_recycling/login, mostrar/ocultar senha e mensagens de erro. Validacao visual em Chromium headless nas larguras de 1440 e 390 pixels. Testes de login incorreto/correto, cookie protegido, WebSocket autenticado, logout, API apos logout e ausencia de overflow passaram. Capturas em artifacts/.

Backup anterior a esta atualizacao: /opt/smart-recycling/backups/login-20261113-053516/.

## Tutorial da API

Guia autenticado em https://mrvbot.com/smart_recycling/tutorial, acessivel no menu e no topo do painel. Inclui sete passos: disponibilidade, autenticacao por sessao e dispositivo, telemetria com exemplos PowerShell/Python/Postman, contrato dos campos, consultas e WebSocket, integracao ESP32 e erros. Botoes para copiar os exemplos e consultar a saude da API. Nao envia telemetria automaticamente e nao inclui chaves reais.

Validado com tests/browser_tutorial.py: protecao de acesso, link no painel, sete secoes, teste de saude, copia de codigo, navegacao por ancoras, referencia OpenAPI e ausencia de overflow nas larguras 1440/390 pixels. Sites e containers anteriores verificados apos a publicacao. Backup: /opt/smart-recycling/backups/tutorial-20261113-054121/.

## Atualização de 16/11/2026 — Next.js e hardware

Frontend migrado para Next.js 16.4.6 / React 19.3.1 com TypeScript, App Router, Server Components autenticados e Recharts sob demanda. Serviço smart-recycling-frontend-1, porta local 18081. Nginx encaminha apenas /smart_recycling/, /smart_recycling/historico e /smart_recycling/_next para o frontend; login, tutorial, WebSocket e API continuam no FastAPI. Histórico com filtro por categoria e dispositivo; ausência de medições não é mostrada como zero.

Protocolo adicional /api/v1/events: telemetry, heartbeat e classification; identidade de evento e objeto, deduplicação, timestamp de origem, medições null, metadados de IA e distância independente por lixeira. /api/v1/devices registra presença do ESP32/Pi, sem confundir heartbeat com leituras. As tabelas hardware_events/hardware_devices são adicionais e preservam dados legados.

Código de integração: firmware/mega2560, firmware/esp32, firmware/raspberry_pi e firmware/training. Guia autenticado /smart_recycling/integracao e download /smart_recycling/api/integration/download. Fonte/documentação/licenças incluídas; nenhuma credencial, dataset ou peso real no pacote.

Verificações executadas: produção Next.js/TypeScript; navegação SSR, login/logout, histórico, tutorial e layout desktop/mobile no Chromium; fixtures de leitura isoladas no navegador para classificações, lixeiras, gráfico, filtro e dados antigos, sem gravação em produção; compilação PlatformIO Mega (RAM 5842/8192 bytes, flash 20222/253952) e ESP32 (RAM 50104/327680, flash 802585/1310720), geração da imagem LittleFS; API em SQLite temporário e PostgreSQL temporário separado na VPS; testes de CRC, framing, fila persistente/repetição e pré-processamento com interpretador de teste. PostgreSQL de teste foi removido após os testes. A cadeia HTTPS foi verificada usando ISRG Root X1.

Backup anterior às novas tabelas/API: /opt/smart-recycling/backups/hardware-20261116-192458/source-before.tgz e database.sql (modo 600), além das imagens Docker :before-hardware-20261116-192458. Backup anterior da configuração Nginx: /opt/smart-recycling/backups/nextjs-20261116-190629/.

Não executados: upload nas placas, validação de fiação, sensores/câmera reais, treinamento/conversão de pesos reais e testes de atuadores/intertravamentos. Pinos adicionais não confirmados permanecem -1; regras e calibração não validadas permanecem desabilitadas. Trecho UART não tem ACK persistente no Mega. O guia documenta instalação, configurações, limites e comissionamento de bancada.

## Atualização de 17/11/2026 — pacote de gravação e documento v0.1

Documento lido por exportação de texto/HTML e inspeção do diagrama: https://docs.google.com/document/d/1Xp4Oc-URVvYnerThbXe_YUCzz_PsSz-oI8dqQ3h-PAw/edit. Arquitetura confirma UART Mega/Pi/ESP e HTTP. Usuário adotou a proposta de montagem; perfil ativo: indutivo D22, HC-SR04 D24/25 (objeto), D26/27 (orgânicos), D28/29 (recicláveis), HX711 D30/31 e D32/33; IR/TCS230 e UARTs preservados. Atuadores continuam apenas reservados e não comandados; calibração e pesos reais pendentes.

Adicionados projetos Arduino IDE, tools/configurar_dispositivos.py (entrada privada de Wi-Fi/chave), tools/gravar.py (compilação/gravação por porta explícita), instalador ARM64 do Pi e diagnóstico somente de leitura. Chave existente preparada em pasta privada fora do repositório, sem inclusão em nenhum ZIP. A senha interna PostgreSQL foi renovada após aparecer numa exceção do runner de teste; o runner agora usa env-file privado e sanitiza falhas. Login do painel e DEVICE_KEY foram mantidos.

Rotas compatíveis com o documento: POST /api/eventos, /api/lixeiras, /api/dispositivos; GET /api/resumo, /api/eventos paginado, /api/historico agrupado UTC, /api/lixeiras com atualização independente e /api/dispositivos. GET /api/device/verify autentica a chave sem criar eventos/presença. Todas as rotas foram testadas em SQLite temporário e PostgreSQL isolado antes da publicação; erro de GROUP BY encontrado nessa etapa foi corrigido antes de afetar o serviço público.

Pacote das placas: /smart_recycling/api/integration/devices, autenticado; COME­CE_AQUI.md na raiz do ZIP e docs/COMECE_AQUI.md no código-fonte. Exclusões de credenciais testadas. Compilação dos fontes e dos dois sketches .ino passou; Mega: 5878/8192 bytes RAM e 21382/253952 flash. ESP32: 50104/327680 RAM e 802585/1310720 flash. Preflight real HTTPS/chave passou sem POST; captura, UART física e inferência de pesos reais não foram executadas. Instalação do Pi exercitada somente em dry-run neste Windows.

Backups do ciclo atual: /opt/smart-recycling/backups/hardware-20261117-214644/ (fonte, dump do banco e imagens anteriores). Sites e containers preexistentes verificados após publicação.
