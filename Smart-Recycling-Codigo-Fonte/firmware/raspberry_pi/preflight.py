"""Read-only preflight on the Raspberry: no classifications or heartbeats are posted."""
import argparse,hashlib,json,os,sys,urllib.request
from pathlib import Path

def load_config(path):
    values={}
    for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
        if not line.strip() or line.lstrip().startswith('#'):continue
        key,separator,value=line.partition('=')
        if not separator:raise ValueError('Linha de configuracao invalida')
        value=value.strip();values[key.strip()]=json.loads(value) if value.startswith('"') else value
    return values

def verify_weights(model_path,manifest_path):
    manifest=json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    if manifest.get('sha256')!=hashlib.sha256(Path(model_path).read_bytes()).hexdigest():raise ValueError('SHA256 do modelo nao corresponde ao manifesto')
    if manifest.get('class_names')!=['organico','reciclavel']:raise ValueError('Ordem das classes do modelo incorreta')
    return manifest

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',default='/etc/smart-recycling-device.env');parser.add_argument('--sem-hardware',action='store_true');args=parser.parse_args()
    config=load_config(args.config)
    base='https://mrvbot.com/smart_recycling'
    key=config.get('DEVICE_KEY','')
    if not key or key.startswith('CONFIGURE'):raise ValueError('Configure a chave privada primeiro')
    with urllib.request.urlopen(base+'/api/health',timeout=15) as response:
        if not json.load(response).get('ok'):raise ValueError('API nao confirmou disponibilidade')
    request=urllib.request.Request(base+'/api/device/verify',headers={'X-Device-Key':key})
    with urllib.request.urlopen(request,timeout=15) as response:
        if not json.load(response).get('authenticated'):raise ValueError('Credencial nao validada')
    print('OK: HTTPS, API e chave do dispositivo. Nenhuma telemetria enviada.')
    if args.sem_hardware:return
    manifest=verify_weights(config['MODEL_PATH'],config['MANIFEST_PATH'])
    from model import WasteModel
    WasteModel(config['MODEL_PATH'],config['MANIFEST_PATH'],float(config.get('MIN_CONFIDENCE','.75')))
    print('OK: modelo real, hash, dimensoes e runtime. Versao:',manifest['model_version'])
    import cv2,serial
    camera=cv2.VideoCapture(int(config.get('CAMERA_INDEX','0')))
    try:
        ok,frame=camera.read()
        if not ok or frame is None:raise ValueError('Camera sem captura real')
        print('OK: captura real da camera',frame.shape)
    finally:camera.release()
    # Opening the UART can affect USB adapters: use with the worker stopped.
    with serial.Serial(config.get('SERIAL_PORT','/dev/ttyUSB0'),115200,timeout=.2):print('OK: porta serial acessivel (eletrica/handshake ainda precisam do ensaio com Mega).')
if __name__=='__main__':
    try:main()
    except Exception as error:
        # Omit request headers and private config from diagnostic output.
        print('FALHA:',type(error).__name__,str(error));raise SystemExit(1)
