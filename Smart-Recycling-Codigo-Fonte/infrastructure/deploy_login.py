from pathlib import Path
import datetime,subprocess,tarfile,json,hashlib,secrets
root=Path('/opt/smart-recycling');stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S');backup=root/'backups'/('login-'+stamp);backup.mkdir()
with tarfile.open(backup/'app-before.tgz','w:gz') as archive:
    for item in ['app','docker-compose.yml','.env']:archive.add(root/item,arcname=item)
(backup/'smart-recycling.conf').write_bytes(Path('/etc/nginx/snippets/smart-recycling.conf').read_bytes())
with tarfile.open('/tmp/smart-recycling-login.tgz','r:gz') as archive:archive.extractall(root,filter='data')
access=json.loads((root/'access.json').read_text());salt=secrets.token_hex(16);hashed=hashlib.scrypt(access['password'].encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
env=root/'.env';text=env.read_text();text='\n'.join(line for line in text.splitlines() if not line.startswith(('LOGIN_USER=','LOGIN_PASSWORD_HASH=')))+'\n';env.write_text(text+'LOGIN_USER='+access['username']+'\nLOGIN_PASSWORD_HASH='+salt+':'+hashed+'\n')
subprocess.run(['docker','compose','-p','smart-recycling','up','-d','--build','api'],cwd=root,check=True)
print('BACKUP',backup)
