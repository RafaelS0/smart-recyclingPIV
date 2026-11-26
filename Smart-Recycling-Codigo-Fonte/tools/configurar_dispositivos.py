"""Configure private credentials locally. Never put Wi-Fi passwords in chat or Git."""
import argparse,getpass,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def clean(value,name):
    if not value or any(ord(c)<32 or ord(c)==127 for c in value):raise ValueError(f'{name}: valor vazio ou caractere de controle')
    return value

def esp_header(ssid,password,key,device_id):
    if key:clean(key,'chave')
    for name,value in [('SSID',ssid),('senha Wi-Fi',password),('device_id',device_id)]:clean(value,name)
    if not re.fullmatch(r'[A-Za-z0-9._:-]{1,80}',device_id):raise ValueError('device_id invalido')
    values={'WIFI_SSID':ssid,'WIFI_PASSWORD':password,'DEVICE_KEY':key,'DEVICE_ID':device_id,'API_URL':'https://mrvbot.com/smart_recycling/api/v1/events'}
    return '#pragma once\n// PRIVADO: nao compartilhar ou enviar ao Git.\n'+''.join(f'constexpr char {name}[]={json.dumps(value,ensure_ascii=False)};\n' for name,value in values.items())

def pi_config(key,device_id):
    clean(key,'chave');clean(device_id,'device_id')
    if not re.fullmatch(r'[A-Za-z0-9._:-]{1,80}',device_id):raise ValueError('device_id invalido')
    values={'API_URL':'https://mrvbot.com/smart_recycling/api/v1/events','DEVICE_ID':device_id,'DEVICE_KEY':key,'SERIAL_PORT':'/dev/ttyUSB0','CAMERA_INDEX':'0','MODEL_PATH':'/opt/smart-recycling-device/models/waste.tflite','MANIFEST_PATH':'/opt/smart-recycling-device/models/manifest.json','OUTBOX_PATH':'/var/lib/smart-recycling/outbox.sqlite3','MIN_CONFIDENCE':'0.75'}
    return ''.join(f'{name}={json.dumps(value,ensure_ascii=False)}\n' for name,value in values.items())

def save_private(path,text,overwrite=False):
    if path.exists() and not overwrite:raise FileExistsError(f'{path}: ja existe. Use --overwrite para substituir a sua configuracao.')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w' if overwrite else 'x',encoding='utf-8') as file:file.write(text)
    path.chmod(0o600)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--component',choices=['esp32','pi','all'],default='all');parser.add_argument('--credentials',type=Path,default=Path.home()/'Downloads/smart-recycling-configuracao-privada/device.json');parser.add_argument('--overwrite',action='store_true');parser.add_argument('--versionado',action='store_true',help='Carrega também a chave para o modo v1 ou a fila anterior do ESP32');args=parser.parse_args()
    key = ''
    if args.component in ('pi', 'all') or args.versionado:
        key = json.loads(args.credentials.read_text(encoding='utf-8-sig'))['DEVICE_KEY'] if args.credentials.is_file() else getpass.getpass('Chave DEVICE_KEY da VPS: ')
    if args.component in ('esp32','all'):
        ssid=input('Nome da rede Wi-Fi (2,4 GHz): ');password=getpass.getpass('Senha do Wi-Fi (nao sera exibida): ');device=input('ID do ESP32 [smart-recycling-esp32-01]: ').strip() or 'smart-recycling-esp32-01'
        text=esp_header(ssid,password,key,device)
        for target in [ROOT/'firmware/esp32/include/secrets.h',ROOT/'firmware/arduino-ide/SmartRecycling_ESP32/secrets.h']:
            if target.parent.is_dir():save_private(target,text,args.overwrite)
        print('Configuracao ESP32 salva em secrets.h. Nenhum segredo foi impresso.')
    if args.component in ('pi','all'):
        device=input('ID do Raspberry [smart-recycling-pi-01]: ').strip() or 'smart-recycling-pi-01'
        save_private(ROOT/'firmware/raspberry_pi/device.env',pi_config(key,device),args.overwrite)
        print('Configuracao Pi salva em firmware/raspberry_pi/device.env. Arquivo privado: copie somente ao seu Pi.')
if __name__=='__main__':
    try:main()
    except (ValueError,FileExistsError,KeyError) as error:raise SystemExit(str(error))
