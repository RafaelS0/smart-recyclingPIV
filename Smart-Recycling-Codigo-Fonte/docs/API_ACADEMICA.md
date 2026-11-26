# API acadêmica do Smart Recycling

Os três POSTs usam HTTPS e o cabeçalho `Content-Type: application/json`. As consultas, o painel e a documentação interativa usam o login atual.

Base `https://mrvbot.com/smart_recycling`. Use timestamps ISO 8601 em UTC, como os exemplos. Troque o horário pelo instante medido pelo equipamento.

## Classificar um item

Envie para `POST /api/eventos` uma vez por item. Reuse o mesmo `event_id` e corpo se precisar reenviar após uma falha.

```json
{
  "event_id": "daijwdji12jid1",
  "timestamp": "2026-11-22T19:24:14Z",
  "material": "organico",
  "metal": 0,
  "ir": 1,
  "color": [255, 255, 255],
  "rasp_material": "organico",
  "rasp_acuracia": 0.93,
  "acuracia_final": 0.95
}
```

`material` aceita `organico`, `reciclavel` ou `indefinido`. Os sensores digitais aceitam 0 ou 1. A cor segue RGB na faixa de 0 a 255. Os campos opcionais podem usar `null` quando faltarem leituras. As duas pontuações vão de 0 a 1.

## Atualizar as lixeiras

Envie para `POST /api/lixeiras` a cada 60 segundos pelo ESP32 usando as medições do Arduino.

```json
{
  "timestamp": "2026-11-22T19:24:14Z",
  "reciclaveis_cm": null,
  "organicos_cm": 30.1
}
```

Quanto menor a distância do sensor até o resíduo, mais cheia está a lixeira. O painel mostra os centímetros disponíveis. Para exibir percentual e alertas por ocupação, calibre as distâncias de vazio e cheio e envie o percentual pelo protocolo v1. A leitura acadêmica passa a aparecer como desatualizada após 150 segundos.

## Informar o estado dos componentes

Envie para `POST /api/dispositivos` com os seis campos de estado.

```json
{
  "timestamp": "2026-11-22T19:24:14Z",
  "sensor_indutivo": true,
  "sensor_cor": true,
  "sensor_ir": true,
  "raspberry": true,
  "servo_topo": true,
  "servo_calha": true
}
```

Use `true` para operante, `false` para indisponível ou `null` quando não há confirmação. O firmware confirma o sensor de cor pelos pulsos recebidos e o Raspberry pela resposta serial. O indutivo, o IR e os servos permanecem sem confirmação de funcionamento na ausência de diagnóstico elétrico dedicado. A classificação ainda pode carregar a leitura digital de IR e metal.

## Enviar pelo terminal

Salve o corpo em um arquivo JSON e envie à rota correspondente. No Windows, use `curl.exe`.

```sh
curl -sS -H "Content-Type: application/json" --data-binary @evento.json https://mrvbot.com/smart_recycling/api/eventos
```

- HTTP 201 confirma a gravação. HTTP 200 indica reenvio idêntico.
- HTTP 409 indica que um ID já registrado foi reutilizado com outro conteúdo.
- HTTP 422 indica divergência nos campos ou valores do JSON.
- Os três POSTs acadêmicos são públicos e podem alterar o painel. Use o ambiente local para amostras de teste.
- As consultas `GET /api/eventos`, `GET /api/lixeiras` e `GET /api/dispositivos` exigem sessão. O protocolo versionado `/api/v1/events` e os envelopes antigos continuam usando `X-Device-Key`.
