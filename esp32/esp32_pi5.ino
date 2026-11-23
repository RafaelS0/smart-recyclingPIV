/*
  ESP32 - ponte Serial -> HTTP (smart recycling)

    (9 campos separados por vírgula, terminada em \n):
    material,metal,ir,r,g,b,rasp_material,rasp_acuracia,acuracia_final
  Exemplo:
    organico,1,1,255,255,255,organico,0.93,0.93
  
  Campos r,g,b podem ficar vazios (viram null):
    organico,1,1,,,,organico,1.0,1.0

  Teste manual (sem Arduino):
    Abra o Monitor Serial da IDE em 115200 baud, com "Nova linha" (Newline) ativado,
    e envie uma linha no formato acima, ou apenas a palavra:  teste



  Bibliotecas: ArduinoJson v7 (Gerenciador de Bibliotecas) e pacote de placas "esp32" da Espressif.
*/

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <time.h>
#include <sys/time.h>

// ===================== CONFIGURAÇÃO =====================
const char* WIFI_SSID   = "Mateus";
const char* WIFI_SENHA  = "050698M@teus";

const char* URL_EVENTOS = "https://mrvbot.com/smart_recycling/api/eventos"; //endpoint para registrar uma classificação

const int  PIN_RX2      = 16;            // RX2 do ESP32 (recebe do TX do Arduino)
const int  PIN_TX2      = 17;            // TX2 do ESP32
const long BAUD_ARDUINO = 9600;          // mesmo baud do Serial do Arduino

const int  NUM_CAMPOS   = 9;
// ========================================================

String bufferArduino = "";   // acumula caracteres vindos do Arduino
String bufferUSB     = "";   // acumula caracteres digitados no Monitor Serial


// ---------- Leitura de linhas (não bloqueante) ----------
bool lerLinha(Stream &porta, String &buf, String &linha) {
  while (porta.available()) {
    char c = porta.read();
    if (c == '\r') continue;
    if (c == '\n') {
      linha = buf;
      buf = "";
      linha.trim();
      return linha.length() > 0;
    }
    if (buf.length() < 200) buf += c;   // evita estourar a memória
  }
  return false;
}


// ---------- Wi-Fi ----------
void conectarWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;

  Serial.print("Conectando ao Wi-Fi");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_SENHA);

  unsigned long inicio = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - inicio < 20000) {
    delay(500);
    Serial.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("\nWi-Fi conectado. IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nFalha ao conectar no Wi-Fi.");
  }
}


// ---------- Hora (NTP) ----------
void sincronizarHora() {
  configTime(0, 0, "pool.ntp.org", "time.google.com");   // UTC
  struct tm t;
  if (getLocalTime(&t, 10000)) {
    Serial.println("Hora sincronizada via NTP.");
  } else {
    Serial.println("Nao foi possivel sincronizar a hora (timestamp sera omitido).");
  }
}

// Retorna "2026-11-23T16:02:11.059Z" formato para armazenar em TIMESTAMP
String horaISO() {
  struct timeval tv;
  gettimeofday(&tv, nullptr);
  if (tv.tv_sec < 100000) return "";

  struct tm t;
  gmtime_r(&tv.tv_sec, &t);

  char base[24];
  strftime(base, sizeof(base), "%Y-%m-%dT%H:%M:%S", &t);

  char saida[40];
  snprintf(saida, sizeof(saida), "%s.%03ldZ", base, (long)(tv.tv_usec / 1000));
  return String(saida);
}


// ---------- event_id ----------
String gerarEventId() {
  static unsigned long contador = 0;
  char buf[48];
  snprintf(buf, sizeof(buf), "esp32-%08x-%lu", (unsigned int)esp_random(), ++contador);
  return String(buf);
}


// ---------- Envio HTTP ----------
bool enviar(const String &json) {
  conectarWiFi();
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Sem Wi-Fi, evento nao enviado.");
    return false;
  }

  WiFiClientSecure client;
  client.setInsecure(); 

  HTTPClient http;
  http.setTimeout(10000);

  if (!http.begin(client, URL_EVENTOS)) {
    Serial.println("Falha ao iniciar a conexao HTTP.");
    return false;
  }

  http.addHeader("Content-Type", "application/json");

  int codigo = http.POST(json);
  Serial.print("HTTP status: ");
  Serial.println(codigo);

  if (codigo > 0) {
    Serial.print("Resposta: ");
    Serial.println(http.getString());
  } else {
    Serial.print("Erro: ");
    Serial.println(http.errorToString(codigo));
  }

  http.end();
  return codigo >= 200 && codigo < 300;
}


// ---------- Converte a linha CSV em JSON e envia ----------
void tratarLinha(String linha) {
  // Atalho para testar sem Arduino
  if (linha.equalsIgnoreCase("teste")) {
    linha = "organico,1,1,255,255,255,organico,0.93,0.93";
    Serial.println("Usando linha de teste: " + linha);
  }

  // Separa os campos por vírgula (mantém campos vazios)
  String campos[NUM_CAMPOS];
  int n = 0, inicio = 0;
  while (n < NUM_CAMPOS) {
    int virg = linha.indexOf(',', inicio);
    if (virg < 0) {
      campos[n++] = linha.substring(inicio);
      break;
    }
    campos[n++] = linha.substring(inicio, virg);
    inicio = virg + 1;
  }

  if (n < NUM_CAMPOS) {
    Serial.print("Linha incompleta (");
    Serial.print(n);
    Serial.println(" campos), descartada: " + linha);
    return;
  }
  for (int i = 0; i < NUM_CAMPOS; i++) campos[i].trim();

  JsonDocument doc;

  String ts = horaISO();
  if (ts.length() > 0) doc["timestamp"] = ts;   // se vazio, o servidor pode preencher
  doc["event_id"]       = gerarEventId();
  doc["material"]       = campos[0];
  doc["metal"]          = campos[1].toInt();
  doc["ir"]             = campos[2].toInt();

  JsonArray color = doc["color"].to<JsonArray>();
  for (int i = 3; i <= 5; i++) {
    if (campos[i].length() == 0) color.add(nullptr);
    else                         color.add(campos[i].toInt());
  }

  doc["rasp_material"]  = campos[6];
  doc["rasp_acuracia"]  = campos[7].toFloat();
  doc["acuracia_final"] = campos[8].toFloat();

  String json;
  serializeJson(doc, json);

  Serial.println("Enviando: " + json);
  bool ok = enviar(json);
  Serial.println(ok ? "Evento enviado com sucesso." : "Falha no envio.");
}


// ---------- Arduino framework ----------
void setup() {
  Serial.begin(115200);                                   // USB: debug e testes manuais
  Serial2.begin(BAUD_ARDUINO, SERIAL_8N1, PIN_RX2, PIN_TX2);  // ligação com o Arduino
  delay(500);

  Serial.println("\n== ESP32 ponte Serial -> HTTP ==");
  conectarWiFi();
  if (WiFi.status() == WL_CONNECTED) sincronizarHora();

  Serial.println("Pronto. Digite 'teste' ou uma linha CSV para enviar manualmente.");
}

void loop() {
  String linha;

  // Dados vindos do Arduino
  if (lerLinha(Serial2, bufferArduino, linha)) {
    Serial.println("Arduino -> " + linha);
    tratarLinha(linha);
  }

  // Dados digitados no Monitor Serial (teste manual)
  if (lerLinha(Serial, bufferUSB, linha)) {
    Serial.println("USB -> " + linha);
    tratarLinha(linha);
  }
}