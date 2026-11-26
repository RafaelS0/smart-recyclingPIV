import pathlib, secrets, subprocess, json, datetime
root=pathlib.Path('/opt/smart-recycling')
if not (root/'.env').exists():
    values={k:secrets.token_hex(32) for k in ['POSTGRES_PASSWORD','DEVICE_KEY','ADMIN_TOKEN']}
    (root/'.env').write_text(''.join(f'{k}={v}\n' for k,v in values.items())+'SIMULATION_MODE=false\nSMART_RECYCLING_PORT=18080\n')
    (root/'.env').chmod(0o600)
if not (root/'.htpasswd').exists():
    password=secrets.token_urlsafe(24)
    hashed=subprocess.check_output(['openssl','passwd','-apr1','-stdin'],input=password.encode()).decode().strip()
    (root/'.htpasswd').write_text('admin:'+hashed+'\n')
    (root/'.htpasswd').chmod(0o640)
    subprocess.run(['chown','root:www-data',str(root/'.htpasswd')],check=True)
    (root/'access.json').write_text(json.dumps({'url':'https://mrvbot.com/smart_recycling/','username':'admin','password':password}))
    (root/'access.json').chmod(0o600)

import hashlib
access=json.loads((root/'access.json').read_text())
if 'LOGIN_PASSWORD_HASH=' not in (root/'.env').read_text():
    salt=secrets.token_hex(16)
    hashed=hashlib.scrypt(access['password'].encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
    with (root/'.env').open('a') as file:
        file.write('LOGIN_USER='+access['username']+'\nLOGIN_PASSWORD_HASH='+salt+':'+hashed+'\n')
