// ===============================
// SMART RECYCLING - TESTE 1
// TCS230 + SENSOR IR
// ===============================

// ---------- Sensor IR ----------
const int IR_PIN = 9; // jumper marrom


// ---------- TCS230 ----------
const int S0_PIN  = 4; //jumper azul
const int S1_PIN  = 5; //jumper laranja
const int S2_PIN  = 6; // jumper laranja
const int S3_PIN  = 7; // jumper amarelo
const int OUT_PIN = 8; // jumper branco


void setup() {

  Serial.begin(9600);

  // IR
  pinMode(IR_PIN, INPUT);

  // TCS230
  pinMode(S0_PIN, OUTPUT);
  pinMode(S1_PIN, OUTPUT);
  pinMode(S2_PIN, OUTPUT);
  pinMode(S3_PIN, OUTPUT);
  pinMode(OUT_PIN, INPUT);

  // Escala de frequência do TCS230
  // 20%
  digitalWrite(S0_PIN, HIGH);
  digitalWrite(S1_PIN, LOW);

  Serial.println("================================");
  Serial.println("SMART RECYCLING - TESTE 1");
  Serial.println("Sensor IR + TCS230");
  Serial.println("================================");

  Serial.println();
  Serial.println("Coloque uma amostra sobre os sensores.");
  Serial.println("Digite qualquer caractere para realizar uma leitura.");
}


// --------------------------------
// Leitura de uma cor
// --------------------------------

unsigned long lerCor(bool s2, bool s3) {

  digitalWrite(S2_PIN, s2);
  digitalWrite(S3_PIN, s3);

  delay(20);

  unsigned long tempo = pulseIn(OUT_PIN, LOW, 100000);

  return tempo;
}


// --------------------------------
// Leitura RGB
// --------------------------------

void lerRGB(unsigned long &vermelho,
            unsigned long &verde,
            unsigned long &azul) {

  // Vermelho
  vermelho = lerCor(LOW, LOW);

  // Verde
  verde = lerCor(HIGH, HIGH);

  // Azul
  azul = lerCor(LOW, HIGH);
}


// --------------------------------
// LOOP
// --------------------------------

void loop() {

  // Espera comando pelo Serial Monitor
  if (Serial.available() > 0) {

    // Limpa o caractere recebido
    while (Serial.available() > 0) {
      Serial.read();
    }

    // -------- IR --------

    int ir = digitalRead(IR_PIN);


    // -------- TCS230 --------

    unsigned long vermelho;
    unsigned long verde;
    unsigned long azul;

    lerRGB(vermelho, verde, azul);


    // -------- Resultado --------

    Serial.println();
    Serial.println("----------- LEITURA -----------");

    Serial.print("IR: ");
    Serial.println(ir);

    Serial.print("Vermelho: ");
    Serial.println(vermelho);

    Serial.print("Verde: ");
    Serial.println(verde);

    Serial.print("Azul: ");
    Serial.println(azul);

    Serial.println("-------------------------------");
    Serial.println();
  }
}
