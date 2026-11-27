import os
import csv
import time
import numpy as np
from PIL import Image
from tflite_runtime.interpreter import Interpreter

# Configurações
MODEL_PATH = "/home/piv/best_waste_classifier.tflite"
DATASET_PATH = "/home/piv/smart-recycling/TEST"
OUTPUT_CSV = "/home/piv/smart-recycling/resultados_dataset.csv"

CLASSES = ["ORGANIC", "RECYCLABLE"]
FOLDERS = {"O": 0, "R": 1}
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp")

# Carrega o modelo
print("Carregando modelo...")
interpreter = Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

print("Modelo carregado!\n")

# Estatísticas
total = 0
correct = 0
errors = 0

class_total = [0, 0]
class_correct = [0, 0]

# Matriz de confusão:
# linhas = classe real / colunas = classe prevista
confusion = np.zeros((2, 2), dtype=int)

total_inference_time = 0.0
image_results = []

# Percorre as pastas O e R
for folder, true_index in FOLDERS.items():

    folder_path = os.path.join(DATASET_PATH, folder)

    if not os.path.isdir(folder_path):
        print(f"AVISO: pasta não encontrada: {folder_path}")
        continue

    files = sorted(os.listdir(folder_path))

    for filename in files:

        if not filename.lower().endswith(IMAGE_EXTENSIONS):
            continue

        image_path = os.path.join(folder_path, filename)

        try:
            # Abre e prepara a imagem
            with Image.open(image_path) as image:
                image = image.convert("RGB")
                image = image.resize((30, 60), Image.Resampling.NEAREST)
                image_array = np.asarray(image, dtype=np.float32)

            input_data = np.expand_dims(image_array, axis=0)

            # Entrada no modelo
            interpreter.set_tensor(
                input_details[0]["index"],
                input_data
            )

            # Inferência
            start = time.perf_counter()
            interpreter.invoke()
            elapsed = time.perf_counter() - start

            scores = interpreter.get_tensor(
                output_details[0]["index"]
            )[0]

            predicted_index = int(np.argmax(scores))
            predicted_class = CLASSES[predicted_index]
            true_class = CLASSES[true_index]

            is_correct = predicted_index == true_index

            # Estatísticas
            total += 1
            class_total[true_index] += 1
            confusion[true_index][predicted_index] += 1

            if is_correct:
                correct += 1
                class_correct[true_index] += 1
            else:
                errors += 1

            total_inference_time += elapsed

            image_results.append([
                image_path,
                true_class,
                predicted_class,
                float(scores[0]),
                float(scores[1]),
                is_correct,
                elapsed * 1000
            ])

            # Progresso
            if total % 100 == 0:
                print(f"Processadas {total} imagens...")

        except Exception as e:
            print(f"Erro na imagem {image_path}: {e}")

# Salva resultados individuais em CSV
with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as csvfile:

    writer = csv.writer(csvfile)

    writer.writerow([
        "image",
        "true_class",
        "predicted_class",
        "organic_score",
        "recyclable_score",
        "correct",
        "inference_ms"
    ])

    writer.writerows(image_results)

# Relatório
print("\n" + "=" * 45)
print("       RESULTADO DA AVALIAÇÃO")
print("=" * 45)

print(f"Total de imagens: {total}")
print(f"Acertos:          {correct}")
print(f"Erros:            {errors}")

if total > 0:
    print(f"Acurácia geral:   {correct / total * 100:.2f}%")

print("\n--- Acurácia por classe ---")

for i, class_name in enumerate(CLASSES):
    if class_total[i] > 0:
        accuracy = class_correct[i] / class_total[i] * 100
        print(
            f"{class_name}: {class_correct[i]}/{class_total[i]} "
            f"({accuracy:.2f}%)"
        )

print("\n--- Matriz de confusão ---")
print("Linhas = real | Colunas = previsto")
print(f"{'':15} ORGANIC  RECYCLABLE")
print(f"ORGANIC       {confusion[0][0]:7}  {confusion[0][1]:10}")
print(f"RECYCLABLE   {confusion[1][0]:7}  {confusion[1][1]:10}")

print("\n--- Tempo de inferência ---")

if total > 0:
    print(f"Tempo total:  {total_inference_time:.2f} s")
    print(f"Tempo médio:  {total_inference_time / total * 1000:.2f} ms/imagem")

print(f"\nCSV salvo em: {OUTPUT_CSV}")
print("=" * 45)
