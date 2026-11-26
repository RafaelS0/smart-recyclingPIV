from pathlib import Path
import tarfile,datetime,subprocess
root=Path('/opt/smart-recycling');backup=root/'backups'/('nextjs-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir()
(backup/'docker-compose.yml').write_bytes((root/'docker-compose.yml').read_bytes());nginx=Path('/etc/nginx/snippets/smart-recycling.conf');(backup/'smart-recycling.conf').write_bytes(nginx.read_bytes())
with tarfile.open('/tmp/smart-recycling-next.tgz','r:gz') as archive:archive.extractall(root,filter='data')
subprocess.run(['docker','compose','-p','smart-recycling','up','-d','--build','frontend'],cwd=root,check=True)
print('BACKUP',backup)
