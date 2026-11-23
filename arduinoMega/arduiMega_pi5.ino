#include <Servo.h>

// ---------- PINOS (ajuste conforme sua montagem) ----------
const uint8_t PIN_S0 = 22, PIN_S1 = 23, PIN_S2 = 24, PIN_S3 = 25, PIN_OUT = 26; // TCS230
const uint8_t PIN_INDUTIVO = 30;      // LJ12A3 (NPN): LOW = metal
const uint8_t PIN_IR       = 31;      // IR reflexivo: LOW = detectou
const uint8_t PIN_SERVO_TOPO  = 9;
const uint8_t PIN_SERVO_CALHA = 10;

const bool INDUTIVO_ATIVO_BAIXO = true;
const bool IR_ATIVO_BAIXO       = true;

// ---------- SERVOS (ângulos de exemplo, ajuste na montagem) ----------
const int TOPO_REPOUSO = 0,  TOPO_EMPURRA = 90;
const int CALHA_CENTRO = 90, CALHA_ORG = 30, CALHA_REC = 150;

// ---------- PESOS E LIMIARES (ajuste com os testes de bancada) ----------
const float W_SEM_METAL  = 0.30f;
const float W_SEM_TRANSP = 0.30f;
const float W_COR_OK     = 0.15f;   // cor concorda com orgânico
const float W_COR_RUIM   = 0.10f;   // cor discorda
const float LIM_ACEITA   = 0.75f;
const float LIM_CONFLITO = 0.90f;

const unsigned long JANELA_RAMPA_MS = 1500;  // tempo observando IR/indutivo na rampa

// Calibração do TCS230: período (µs) lido com papel branco e com preto
const long CAL_BRANCO = 40;
const long CAL_PRETO  = 400;

Servo servoTopo, servoCalha;

struct Cor { int r, g, b; };
struct Decisao { const char* classe; float conf; };

// ---------- TCS230 ----------
long lerCanal(bool s2, bool s3) {
  digitalWrite(PIN_S2, s2);
  digitalWrite(PIN_S3, s3);
  delay(30);
  long p = pulseIn(PIN_OUT, LOW, 30000UL);
  return (p == 0) ? CAL_PRETO : p;     // timeout = muito escuro
}

int paraEscala(long periodo) {
  return constrain(map(periodo, CAL_BRANCO, CAL_PRETO, 255, 0), 0, 255);
}

Cor lerCor() {
  Cor c;
  c.r = paraEscala(lerCanal(LOW,  LOW));
  c.b = paraEscala(lerCanal(LOW,  HIGH));
  c.g = paraEscala(lerCanal(HIGH, HIGH));
  return c;
}

// Regra provisória: azul claramente mais fraco que vermelho e verde
// (amarelo e marrom). Recalibre com casca de banana, PET e latinha.
bool corOrganica(const Cor& c) {
  return (c.b < 0.7f * c.r) && (c.b < 0.7f * c.g);
}

// ---------- Rampa: indutivo + IR ----------
void lerRampa(bool& metal, bool& ir) {
  metal = false; ir = false;
  unsigned long t0 = millis();
  while (millis() - t0 < JANELA_RAMPA_MS) {
    bool m = digitalRead(PIN_INDUTIVO) == (INDUTIVO_ATIVO_BAIXO ? LOW : HIGH);
    bool i = digitalRead(PIN_IR)       == (IR_ATIVO_BAIXO ? LOW : HIGH);
    metal = metal || m;      // basta detectar uma vez durante a passagem
    ir    = ir    || i;
  }
}

// ---------- Fusão ----------
float reforca(float p, float w)   { return p + w * (1.0f - p); }
float enfraquece(float p, float w){ return p * (1.0f - w); }

Decisao fundir(float pOrg, bool metal, bool irTransp, bool corOrg) {
  Decisao d;

  // vetos fortes: reciclável
  if (metal || irTransp) {
    if (pOrg > LIM_CONFLITO) { d.classe = "ERR"; d.conf = pOrg; }
    else                     { d.classe = "REC"; d.conf = max(0.85f, 1.0f - pOrg); }
    return d;
  }

  // evidências a favor de orgânico
  pOrg = reforca(pOrg, W_SEM_METAL);
  pOrg = reforca(pOrg, W_SEM_TRANSP);
  pOrg = corOrg ? reforca(pOrg, W_COR_OK) : enfraquece(pOrg, W_COR_RUIM);

  if (pOrg >= LIM_ACEITA)          { d.classe = "ORG"; d.conf = pOrg; }
  else if (pOrg <= 1.0f - LIM_ACEITA) { d.classe = "REC"; d.conf = 1.0f - pOrg; }
  else                             { d.classe = "ERR"; d.conf = max(pOrg, 1.0f - pOrg); }
  return d;
}

// ---------- Atuadores ----------
void empurrar() {
  servoTopo.write(TOPO_EMPURRA);
  delay(600);
  servoTopo.write(TOPO_REPOUSO);
}

void moverCalha(const char* classe) {
  if (strcmp(classe, "ORG") == 0)      servoCalha.write(CALHA_ORG);
  else if (strcmp(classe, "REC") == 0) servoCalha.write(CALHA_REC);
  else { servoCalha.write(CALHA_CENTRO); return; }   // ERR: aguarda intervenção
  delay(1200);                                        // tempo do resíduo cair
  servoCalha.write(CALHA_CENTRO);
}

// ---------- Serial ----------
char buf[40];
uint8_t nbuf = 0;

bool lerLinha() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (nbuf > 0) { buf[nbuf] = 0; nbuf = 0; return true; }
    } else if (nbuf < sizeof(buf) - 1) {
      buf[nbuf++] = c;
    }
  }
  return false;
}

// "PI,ORG,0.80" -> pOrg (probabilidade de ser orgânico)
bool parsePi(char* linha, float& pOrg) {
  char* tag = strtok(linha, ",");
  char* cls = strtok(NULL, ",");
  char* cf  = strtok(NULL, ",");
  if (!tag || !cls || !cf || strcmp(tag, "PI") != 0) return false;
  float c = constrain(atof(cf), 0.0f, 1.0f);
  if (strcmp(cls, "ORG") == 0)      pOrg = c;
  else if (strcmp(cls, "REC") == 0) pOrg = 1.0f - c;
  else                              pOrg = 0.5f;      // NONE: sem opinião da Pi
  return true;
}

void enviarResultado(const Decisao& d, bool metal, bool ir, const Cor& c) {
  Serial.print("RES,");  Serial.print(d.classe);
  Serial.print(',');      Serial.print(d.conf, 2);
  Serial.print(',');      Serial.print(metal ? 1 : 0);
  Serial.print(',');      Serial.print(ir ? 1 : 0);
  Serial.print(',');      Serial.print(c.r);
  Serial.print(',');      Serial.print(c.g);
  Serial.print(',');      Serial.println(c.b);
}

// ---------- Fluxo principal ----------
void processar(float pOrg) {
  Cor cor = lerCor();                  // cor lida no ponto de depósito
  empurrar();                          // servo empurra para a rampa
  bool metal, ir;
  lerRampa(metal, ir);                 // indutivo + IR na rampa
  Decisao d = fundir(pOrg, metal, ir, corOrganica(cor));
  moverCalha(d.classe);
  enviarResultado(d, metal, ir, cor);
}

void setup() {
  Serial.begin(115200);

  pinMode(PIN_S0, OUTPUT); pinMode(PIN_S1, OUTPUT);
  pinMode(PIN_S2, OUTPUT); pinMode(PIN_S3, OUTPUT);
  pinMode(PIN_OUT, INPUT);
  digitalWrite(PIN_S0, HIGH); digitalWrite(PIN_S1, LOW);   // escala 20%

  pinMode(PIN_INDUTIVO, INPUT_PULLUP);
  pinMode(PIN_IR, INPUT_PULLUP);

  servoTopo.attach(PIN_SERVO_TOPO);
  servoCalha.attach(PIN_SERVO_CALHA);
  servoTopo.write(TOPO_REPOUSO);
  servoCalha.write(CALHA_CENTRO);

  Serial.println("READY");
}

void loop() {
  if (lerLinha()) {
    float pOrg;
    if (parsePi(buf, pOrg)) processar(pOrg);
    else Serial.println("ERRO,linha_invalida");
  }
}