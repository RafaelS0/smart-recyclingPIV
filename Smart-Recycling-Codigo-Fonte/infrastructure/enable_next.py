from pathlib import Path
import subprocess,urllib.request
root=Path('/opt/smart-recycling')
with urllib.request.urlopen('http://127.0.0.1:18081/smart_recycling/',timeout=15) as response:
    assert response.status==200
    assert 'login' in response.read().decode()
p=Path('/etc/nginx/snippets/smart-recycling.conf');original=p.read_bytes();p.write_bytes((root/'infrastructure/smart-recycling.nginx.conf').read_bytes())
try:
    subprocess.run(['nginx','-t'],check=True);subprocess.run(['systemctl','reload','nginx'],check=True)
except Exception:
    p.write_bytes(original);raise
print('Next.js routes enabled; existing backend routes retained')
