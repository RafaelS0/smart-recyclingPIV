from pathlib import Path
import tarfile,datetime,subprocess
root=Path('/opt/smart-recycling')
backup=root/'backups'/('tutorial-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir()
with tarfile.open(backup/'app-before.tgz','w:gz') as archive:archive.add(root/'app',arcname='app')
with tarfile.open('/tmp/smart-recycling-tutorial.tgz','r:gz') as archive:archive.extractall(root,filter='data')
subprocess.run(['docker','compose','-p','smart-recycling','up','-d','--build','api'],cwd=root,check=True)
print('BACKUP',backup)
