// ==========================================
// SMART RECYCLING - CLASSIFICADOR
// TCS230 + SENSOR IR
// ==========================================

// ---------- Sensor IR ----------
const int IR_PIN = 9; // jumper marrom


// ---------- TCS230 ----------
const int S0_PIN  = 4; //jumper azul
const int S1_PIN  = 5; //jumper laranja
const int S2_PIN  = 6; // jumper laranja
const int S3_PIN  = 7; // jumper amarelo
const int OUT_PIN = 8; // jumper branco


// =================================================
// LIMIARES EXPERIMENTAIS
// =================================================
// ESTES VALORES DEVEM SER SUBSTITUÍDOS pelos valores
// encontrados nos testes de vocês.

const unsigned long LIMIAR_VERMELHO = 0;
const unsigned long LIMIAR_VERDE    = 0;
const unsigned long LIMIAR_AZUL     = 0;


// Qual estado do IR foi observado para recicláveis.
// Pode ser HIGH ou LOW dependendo do módulo.
const int IR_RECICLAVEL = LOW;


// Quantidade de leituras para fazer uma média
const int NUM_LEITURAS = 5;


// -------------------------------------------------
// Leitura de uma cor
// -------------------------------------------------

unsigned long lerCor(bool s2, bool s3) {

  digitalWrite(S2_PIN, s2);
  digitalWrite(S3_PIN, s3);

  delay(20);

  return pulseIn(OUT_PIN, LOW, 100000);
}


// -------------------------------------------------
// Leitura média do RGB
// -------------------------------------------------

void lerRGB(unsigned long &vermelho,
            unsigned long &verde,
            unsigned long &azul) {

  unsigned long somaR = 0;
  unsigned long somaG = 0;
  unsigned long somaB = 0;

  for (int i = 0; i < NUM_LEITURAS; i++) {

    somaR += lerCor(LOW, LOW);      // Vermelho
    somaG += lerCor(HIGH, HIGH);    // Verde
    somaB += lerCor(LOW, HIGH);     // Azul
  }

  vermelho = somaR / NUM_LEITURAS;
  verde    = somaG / NUM_LEITURAS;
  azul     = somaB / NUM_LEITURAS;
}


// -------------------------------------------------
// CLASSIFICAÇÃO
// -------------------------------------------------

String classificar(unsigned long vermelho,
                   unsigned long verde,
                   unsigned long azul,
                   int ir) {

  // PRIMEIRA DECISÃO: SENSOR IR

  if (ir == IR_RECICLAVEL) {

    // Se os testes mostrarem que essa condição
    // já é suficiente, podemos classificar direto.

    return "RECICLAVEL";
  }


  // SEGUNDA DECISÃO: TCS230

  // Aqui entra a regra descoberta experimentalmente.

  if (vermelho > LIMIAR_VERMELHO &&
      verde > LIMIAR_VERDE &&
      azul > LIMIAR_AZUL) {

    return "ORGANICO";
  }

  return "RECICLAVEL";
}


// =================================================
// SETUP
// =================================================

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

  // Frequência do TCS230
  digitalWrite(S0_PIN, HIGH);
  digitalWrite(S1_PIN, LOW);

  Serial.println("================================");
  Serial.println("SMART RECYCLING");
  Serial.println("CLASSIFICADOR");
  Serial.println("================================");
}


// =================================================
// LOOP
// =================================================

void loop() {

  Serial.println();
  Serial.println("Coloque uma amostra...");

  delay(2000);


  // -----------------------------
  // Ler IR
  // -----------------------------

  int ir = digitalRead(IR_PIN);


  // -----------------------------
  // Ler TCS230
  // -----------------------------

  unsigned long vermelho;
  unsigned long verde;
  unsigned long azul;

  lerRGB(vermelho, verde, azul);


  // -----------------------------
  // Classificar
  // -----------------------------

  String resultado =
      classificar(vermelho, verde, azul, ir);


  // -----------------------------
  // Mostrar resultado
  // -----------------------------

  Serial.println("-----------------------------");

  Serial.print("IR: ");
  Serial.println(ir);

  Serial.print("Vermelho: ");
  Serial.println(vermelho);

  Serial.print("Verde: ");
  Serial.println(verde);

  Serial.print("Azul: ");
  Serial.println(azul);

  Serial.print("CLASSIFICACAO: ");
  Serial.println(resultado);

  Serial.println("-----------------------------");


  // Esperar antes da próxima amostra
  delay(3000);
}
