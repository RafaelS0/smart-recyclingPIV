"""Create private deployment secrets once. Does not overwrite an existing .env."""
import getpass,hashlib,secrets
from pathlib import Path
root=Path(__file__).resolve().parents[1];target=root/'.env'
if target.exists():raise SystemExit('.env already exists; existing credentials preserved.')
password=getpass.getpass('Senha inicial do administrador (minimo 12 caracteres): ')
if len(password)<12:raise SystemExit('Use pelo menos 12 caracteres.')
if password!=getpass.getpass('Confirme a senha: '):raise SystemExit('Senhas diferentes.')
salt=secrets.token_hex(16);digest=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
with target.open('x',encoding='utf-8') as file:
    for key in ['POSTGRES_PASSWORD','DEVICE_KEY','ADMIN_TOKEN']:file.write(f'{key}={secrets.token_hex(32)}\n')
    file.write(f'LOGIN_USER=admin\nLOGIN_PASSWORD_HASH={salt}:{digest}\nSIMULATION_MODE=false\nSMART_RECYCLING_PORT=18080\n')
target.chmod(0o600)
print('Credenciais criadas em .env. Nenhum segredo foi impresso. Guarde a senha em seu gerenciador de senhas.')
