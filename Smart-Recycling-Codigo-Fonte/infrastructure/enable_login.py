from pathlib import Path
import subprocess,urllib.request
assert urllib.request.urlopen('http://127.0.0.1:18080/login').status==200
p=Path('/etc/nginx/snippets/smart-recycling.conf');original=p.read_text();updated=original.replace('    auth_basic "Smart Recycling";','    auth_basic off;').replace('    auth_basic_user_file /opt/smart-recycling/.htpasswd;\n','').replace('    proxy_set_header Host $host;','    proxy_set_header Host $host;\n    proxy_set_header X-Real-IP $remote_addr;\n    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;')
p.write_text(updated)
try:
    subprocess.run(['nginx','-t'],check=True)
    subprocess.run(['systemctl','reload','nginx'],check=True)
except Exception:
    p.write_text(original)
    raise
print('Login da aplicacao habilitado')
