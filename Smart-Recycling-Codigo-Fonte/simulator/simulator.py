import os, time, random
import httpx

api = os.getenv('API_URL', 'http://api:8000')
key = os.environ['DEVICE_KEY']
organic_weight = 0.0
recyclable_weight = 0.0
organic_count = 0
recyclable_count = 0

with httpx.Client(timeout=10) as client:
    while True:
        if os.getenv('SIMULATION_MODE', 'true').lower() != 'true':
            time.sleep(30)
            continue
        material = random.choices(['organico', 'reciclavel', 'indefinido'], weights=[43, 51, 6])[0]
        mass = round(random.uniform(12, 130), 1)
        if material == 'organico':
            organic_count += 1
            organic_weight += mass
        elif material == 'reciclavel':
            recyclable_count += 1
            recyclable_weight += mass
        payload = {
            'device_id': 'simulator-01', 'simulated': True, 'material': material,
            'confidence': round(random.uniform(.65, .98), 3) if material != 'indefinido' else None,
            'metal': material == 'reciclavel' and random.random() < .35,
            'infrared': round(random.uniform(0, 1023), 1),
            'color_r': random.randint(0,255), 'color_g': random.randint(0,255), 'color_b': random.randint(0,255),
            'distance_cm': round(random.uniform(3, 30), 1),
            'organic_fill_pct': min(100, organic_count * 1.7),
            'recyclable_fill_pct': min(100, recyclable_count * 1.5),
            'organic_weight_g': round(organic_weight, 1),
            'recyclable_weight_g': round(recyclable_weight, 1),
            'conveyor_running': True, 'servo_position_deg': 25 if material == 'organico' else 125
        }
        try:
            r = client.post(f'{api}/api/telemetry', json=payload, headers={'X-Device-Key': key})
            r.raise_for_status()
            print('Enviado', material, r.json(), flush=True)
        except Exception as exc:
            print('Aguardando API:', exc, flush=True)
        time.sleep(4)
