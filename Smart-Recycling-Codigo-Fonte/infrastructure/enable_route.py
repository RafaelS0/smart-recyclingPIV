from pathlib import Path
import subprocess,datetime,json,urllib.request,hashlib
p=Path('/etc/nginx/sites-enabled/mrvbot.com.conf')
stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
backup=Path('/opt/smart-recycling/backups')/stamp
backup.mkdir(parents=True)
original=p.read_bytes();(backup/p.name).write_bytes(original)
state=subprocess.check_output(['docker','ps','--format','{{.Names}}']).decode().splitlines()
(backup/'containers.json').write_text(json.dumps(state))
urls=['https://mrvbot.com/','https://convertearq.com.br/','https://vetcolosso.com.br/','https://racoesdafronteira.com.br/','https://miguelvalentim.com.br/']
baseline={}
for url in urls:
    try:
        with urllib.request.urlopen(url,timeout=20) as r: baseline[url]={'status':r.status,'sha256':hashlib.sha256(r.read()).hexdigest()}
    except Exception as e: baseline[url]={'error':str(e)}
(backup/'sites-before.json').write_text(json.dumps(baseline,indent=2))
print(json.dumps(baseline,indent=2))
snippet=Path('/etc/nginx/snippets/smart-recycling.conf')
if snippet.exists(): raise RuntimeError('Snippet already exists: inspect before overwrite')
snippet.write_text(Path('/opt/smart-recycling/infrastructure/smart-recycling.nginx.conf').read_text(encoding='utf-8-sig'))
text=original.decode();anchor='    include /etc/nginx/snippets/lavanderia.conf;'
assert text.count(anchor)==1
p.write_text(text.replace(anchor,anchor+'\n    include /etc/nginx/snippets/smart-recycling.conf;'))
result=subprocess.run(['nginx','-t'])
if result.returncode:
    p.write_bytes(original)
    raise RuntimeError('Nginx validation failed; original restored')
subprocess.run(['systemctl','reload','nginx'],check=True)
print('BACKUP',backup)
