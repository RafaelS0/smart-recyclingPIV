"""Install this worker on a Raspberry Pi OS ARM64 device, never on the shared VPS."""
import argparse,hashlib,json,platform,shutil,subprocess,sys
from pathlib import Path
SOURCE=Path(__file__).resolve().parent
TARGET=Path('/opt/smart-recycling-device')
FILES=['main.py','model.py','outbox.py','protocol.py','preflight.py','requirements.txt','smart-recycling-device.service']
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',type=Path,default=SOURCE/'device.env');parser.add_argument('--model',type=Path);parser.add_argument('--manifest',type=Path);parser.add_argument('--start',action='store_true');parser.add_argument('--dry-run',action='store_true');args=parser.parse_args()
    if args.dry_run:
        print('Plano: validar ARM64/root; instalar pacotes Python/OpenCV; criar usuario smart-recycling; copiar worker para',TARGET,'; criar venv; configurar systemd e arquivo privado /etc/smart-recycling-device.env.');print('Iniciar servico:',args.start);return
    import os
    if sys.platform!='linux' or platform.machine()!='aarch64':raise SystemExit('Use no Raspberry Pi OS 64-bit (aarch64). Nao executar na VPS ou Windows.')
    if os.geteuid()!=0:raise SystemExit('Execute sudo python3 install.py ...')
    if sys.version_info<(3,11):raise SystemExit('Use Python 3.11 ou superior com runtime ARM64 correspondente.')
    if not args.config.is_file():raise SystemExit('Crie device.env pelo configurador local antes de instalar.')
    from preflight import load_config,verify_weights
    config=load_config(args.config)
    if not config.get('DEVICE_KEY') or config['DEVICE_KEY'].startswith('CONFIGURE'):raise SystemExit('DEVICE_KEY nao configurada')
    if bool(args.model)!=bool(args.manifest):raise SystemExit('Informe --model e --manifest juntos.')
    if args.model:verify_weights(args.model,args.manifest)
    if args.start and not args.model and not (TARGET/'models/waste.tflite').is_file():raise SystemExit('Para --start, forneca os pesos reais com --model e --manifest; nenhum modelo e inventado.')
    def run(*command):subprocess.run(list(command),check=True)
    run('apt-get','update');run('apt-get','install','-y','python3-venv','python3-opencv','python3-numpy','python3-pil')
    import pwd
    try:pwd.getpwnam('smart-recycling')
    except KeyError:run('useradd','--system','--user-group','--groups','dialout,video','--home-dir',str(TARGET),'smart-recycling')
    run('usermod','-aG','dialout,video','smart-recycling')
    run('install','-d','-o','smart-recycling','-g','smart-recycling',str(TARGET),'/var/lib/smart-recycling')
    for name in FILES:shutil.copyfile(SOURCE/name,TARGET/name);(TARGET/name).chmod(0o644)
    env=Path('/etc/smart-recycling-device.env');shutil.copyfile(args.config,env);env.chmod(0o600)
    if args.model:
        (TARGET/'models').mkdir(exist_ok=True);shutil.copyfile(args.model,TARGET/'models/waste.tflite');shutil.copyfile(args.manifest,TARGET/'models/manifest.json')
        for file in (TARGET/'models').iterdir():file.chmod(0o644)
    run('sudo','-u','smart-recycling','python3','-m','venv','--system-site-packages',str(TARGET/'.venv'))
    pip=['sudo','-u','smart-recycling',str(TARGET/'.venv/bin/python'),'-m','pip','install','--no-cache-dir']
    run(*pip,'-r',str(TARGET/'requirements.txt'));run(*pip,'ai-edge-litert==2.3.0')
    shutil.copyfile(SOURCE/'smart-recycling-device.service','/etc/systemd/system/smart-recycling-device.service')
    run('systemctl','daemon-reload')
    if args.start:run('systemctl','enable','--now','smart-recycling-device')
    print('Instalado. Estado fisico ainda exige preflight e ensaio da comunicacao com Mega. Segredos omitidos.')
if __name__=='__main__':main()
