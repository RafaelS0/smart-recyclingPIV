import serial
import time
import subprocess
import os
import numpy as np
from PIL import Image
from tflite_runtime.interpreter import Interpreter

# CONFIGURAÇÕES
PORTA_ARDUINO = "/dev/ttyUSB0"
BAUD = 115200

MODELO = "/home/piv/best_waste_classifier.tflite"
IMAGEM = "/tmp/captura.jpg"

CLASSES = ["ORGANIC", "RECYCLABLE"]

# Carrega CNN uma única vez
print("Carregando modelo CNN...", flush=True)

interpreter = Interpreter(model_path=MODELO)
interpreter.allocate_tensors()

entrada = interpreter.get_input_details()
saida = interpreter.get_output_details()

print("Modelo carregado!", flush=True)


def capturar_imagem():
    print("Capturando imagem...", flush=True)

    comando = [
        "v4l2-ctl",
        "-d", "/dev/video0",
        "--set-fmt-video=width=640,height=480,pixelformat=MJPG",
        "--set-parm=30",
        "--stream-mmap=3",
        "--stream-skip=5",
        "--stream-count=1",
        "--stream-to=" + IMAGEM
    ]

    subprocess.run(
        comando,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
        timeout=15
    )

    if not os.path.exists(IMAGEM) or os.path.getsize(IMAGEM) == 0:
        raise RuntimeError("Imagem vazia ou não capturada")

    print("Imagem capturada!", flush=True)


def classificar_imagem():
    img = Image.open(IMAGEM).convert("RGB")
    img = img.resize((30, 60), Image.Resampling.NEAREST)

    dados = np.asarray(img, dtype=np.float32)
    dados = np.expand_dims(dados, axis=0)

    interpreter.set_tensor(entrada[0]["index"], dados)

    inicio = time.time()
    interpreter.invoke()
    fim = time.time()

    resultados = interpreter.get_tensor(saida[0]["index"])[0]

    indice = int(np.argmax(resultados))
    classe = CLASSES[indice]
    confianca = float(resultados[indice])

    print("\n===== CLASSIFICAÇÃO =====", flush=True)
    print(f"ORGANIC:      {resultados[0]:.4f}", flush=True)
    print(f"RECYCLABLE:   {resultados[1]:.4f}", flush=True)
    print(f"Resultado:     {classe}", flush=True)
    print(f"Confiança:    {confianca * 100:.2f}%", flush=True)
    print(f"Inferência:    {(fim-inicio)*1000:.2f} ms", flush=True)
    print("========================\n", flush=True)

    return classe


def main():
    print(f"Conectando ao Arduino em {PORTA_ARDUINO}...", flush=True)

    arduino = serial.Serial(PORTA_ARDUINO, BAUD, timeout=1)

    # A abertura da porta serial pode reiniciar o Mega
    time.sleep(2)
    arduino.reset_input_buffer()

    print("Arduino conectado!", flush=True)
    print("SMART RECYCLING ATIVO - aguardando objetos...\n", flush=True)

    try:
        while True:
            linha = arduino.readline().decode(
                "utf-8", errors="replace"
            ).strip()

            if not linha:
                continue

            print(f"[ARDUINO] {linha}", flush=True)

            if linha == "CAPTURE":
                try:
                    capturar_imagem()
                    classe = classificar_imagem()

                    arduino.write((classe + "\n").encode("utf-8"))
                    arduino.flush()

                    print(f"[PI -> ARDUINO] {classe}\n", flush=True)

                except Exception as e:
                    print(f"ERRO NO PROCESSAMENTO: {e}", flush=True)

                    arduino.write(b"ERROR\n")
                    arduino.flush()

    except KeyboardInterrupt:
        print("\nEncerrando Smart Recycling...", flush=True)

    finally:
        arduino.close()
        print("Serial fechada.", flush=True)


if __name__ == "__main__":
    main()
