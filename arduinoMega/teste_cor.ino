// ===============================
// SMART RECYCLING - CÓDIGO CALIBRADO
// TCS230 + SENSOR IR
// ===============================

// -------- Sensor IR --------
const int IR_PIN = 9;

// -------- TCS230 --------
const int S0_PIN  = 4;
const int S1_PIN  = 5;
const int S2_PIN  = 6;
const int S3_PIN  = 7;
const int OUT_PIN = 8;

// -------- VALORES REAIS DA SUA CALIBRAÇÃO --------
const unsigned long V_BRANCO = 50;
const unsigned long G_BRANCO = 56;
const unsigned long B_BRANCO = 44;

const unsigned long V_PRETO  = 273;
const unsigned long G_PRETO  = 283;
const unsigned long B_PRETO  = 222;

void setup() {
  Serial.begin(9600);

  // Pinos do IR
  pinMode(IR_PIN, INPUT);

  // Pinos do TCS230
  pinMode(S0_PIN, OUTPUT);
  pinMode(S1_PIN, OUTPUT);
  pinMode(S2_PIN, OUTPUT);
  pinMode(S3_PIN, OUTPUT);
  pinMode(OUT_PIN, INPUT);

  // Escala de frequência do TCS230 em 20%
  digitalWrite(S0_PIN, HIGH);
  digitalWrite(S1_PIN, LOW);

  Serial.println("================================");
  Serial.println("SMART RECYCLING - RGB (0-255)");
  Serial.println("================================");
  Serial.println("Digite qualquer caractere para ler.");
}

// --------------------------------
// Leitura do tempo de pulso
// --------------------------------
unsigned long lerCor(bool s2, bool s3) {
  digitalWrite(S2_PIN, s2);
  digitalWrite(S3_PIN, s3);
  delay(20);
  return pulseIn(OUT_PIN, LOW, 100000);
}

// --------------------------------
// Mapeamento para escala 0 a 255
// --------------------------------
void lerRGB(int &r255, int &g255, int &b255) {
  unsigned long vTempo = lerCor(LOW, LOW);   // Vermelho
  unsigned long gTempo = lerCor(HIGH, HIGH); // Verde
  unsigned long bTempo = lerCor(LOW, HIGH);  // Azul

  // Converte tempo menor -> 255 (Luz Máxima) e tempo maior -> 0 (Sem Luz)
  r255 = map(vTempo, V_BRANCO, V_PRETO, 255, 0);
  g255 = map(gTempo, G_BRANCO, G_PRETO, 255, 0);
  b255 = map(bTempo, B_BRANCO, B_PRETO, 255, 0);

  // Garante que o resultado permaneça estritamente no intervalo [0, 255]
  r255 = constrain(r255, 0, 255);
  g255 = constrain(g255, 0, 255);
  b255 = constrain(b255, 0, 255);
}

void loop() {
  if (Serial.available() > 0) {
    while (Serial.available() > 0) {
      Serial.read(); // Limpa o buffer
    }

    int ir = digitalRead(IR_PIN);

    int r, g, b;
    lerRGB(r, g, b);

    Serial.println();
    Serial.println("----------- LEITURA RGB -----------");
    Serial.print("IR: ");
    Serial.println(ir);

    Serial.print("R (Vermelho): ");
    Serial.println(r);

    Serial.print("G (Verde):    ");
    Serial.println(g);

    Serial.print("B (Azul):     ");
    Serial.println(b);
    Serial.println("-----------------------------------");
  }
}
