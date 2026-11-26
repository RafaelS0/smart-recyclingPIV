"""Compile/upload only the requested board. Filesystem erase requires an explicit flag."""
import argparse,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def commands(component,port,compile_only=False,initialize_fs=False):
    project=ROOT/'firmware'/('mega2560' if component=='mega' else 'esp32')
    result=[[sys.executable,'-m','platformio','run','-d',str(project)]]
    if not compile_only:
        result.append(result[0]+['-t','upload','--upload-port',port])
        if initialize_fs:
            if component!='esp32':raise ValueError('--inicializar-fs e exclusivo do ESP32')
            result.append(result[0]+['-t','uploadfs','--upload-port',port])
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('component',choices=['mega','esp32']);parser.add_argument('--porta');parser.add_argument('--compilar',action='store_true');parser.add_argument('--inicializar-fs',action='store_true',help='ESP32 NOVO: apaga o armazenamento da fila');parser.add_argument('--dry-run',action='store_true');args=parser.parse_args()
    if not args.compilar and not args.porta and not args.dry_run:parser.error('Informe --porta COMx ou /dev/ttyUSBx; nada sera gravado por adivinhacao.')
    if args.inicializar_fs and args.component!='esp32':parser.error('--inicializar-fs exige esp32')
    if not args.dry_run and args.component=='esp32' and not args.compilar:
        if not (ROOT/'firmware/esp32/include/secrets.h').is_file():parser.error('Execute tools/configurar_dispositivos.py --component esp32 antes de gravar.')
    if args.inicializar_fs:print('ATENCAO: uploadfs apaga a fila. Use somente em placa nova/vazia.')
    for command in commands(args.component,args.porta or 'PORTA_A_CONFIRMAR',args.compilar,args.inicializar_fs):
        if args.dry_run:print(subprocess.list2cmdline(command))
        else:subprocess.run(command,check=True)
if __name__=='__main__':main()
