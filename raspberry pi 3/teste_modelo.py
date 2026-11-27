import sys
import time
import numpy as np
from PIL import Image
from tflite_runtime.interpreter import Interpreter

MODEL_PATH = "/home/piv/best_waste_classifier.tflite"
IMAGE_PATH = sys.argv[1] if len(sys.argv) > 1 else "/tmp/captura.jpg"

CLASSES = ["ORGANIC", "RECYCLABLE"]

# 1. Carrega o modelo
print("Carregando modelo...")

interpreter = Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

print("Modelo carregado!")

# 2. Abre a imagem
print("\nAbrindo imagem...")

with Image.open(IMAGE_PATH) as image:
    print("Dimensões originais:", image.size)
    print("Formato original:", image.format)

    # 3. Prepara a imagem
    image = image.convert("RGB")
    image = image.resize((30, 60), Image.Resampling.NEAREST)

    image_array = np.asarray(image, dtype=np.float32)

# 4. Adiciona a dimensão do lote
input_data = np.expand_dims(image_array, axis=0)

print("\nPreparação da entrada:")
print("Formato:", input_data.shape)
print("Tipo:", input_data.dtype)
print("Valor mínimo:", input_data.min())
print("Valor máximo:", input_data.max())

# 5. Executa a inferência
interpreter.set_tensor(input_details[0]["index"], input_data)

start = time.perf_counter()
interpreter.invoke()
elapsed = time.perf_counter() - start

# 6. Obtém os resultados
scores = interpreter.get_tensor(output_details[0]["index"])[0]

predicted_index = int(np.argmax(scores))
predicted_class = CLASSES[predicted_index]

print("\n===== RESULTADO =====")
print(f"ORGANIC:    {scores[0]:.6f}")
print(f"RECYCLABLE: {scores[1]:.6f}")
print("Classe identificada:", predicted_class)
print(f"Tempo de inferência: {elapsed * 1000:.2f} ms")

