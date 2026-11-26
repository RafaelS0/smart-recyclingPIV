from pathlib import Path
import tarfile,datetime,subprocess,uuid,secrets
root=Path('/opt/smart-recycling');stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S');backup=root/'backups'/('hardware-'+stamp);backup.mkdir()
with tarfile.open(backup/'source-before.tgz','w:gz') as archive:
    for folder in ['app','frontend']:
        if (root/folder).exists():archive.add(root/folder,arcname=folder)
(backup/'docker-compose.yml').write_bytes((root/'docker-compose.yml').read_bytes())
for image in ['smart-recycling-api','smart-recycling-frontend']:subprocess.run(['docker','tag',image+':latest',image+':before-hardware-'+stamp],check=True)
with (backup/'database.sql').open('wb') as file:subprocess.run(['docker','exec','smart-recycling-db-1','pg_dump','-U','smart','smart_recycling'],stdout=file,check=True)
(backup/'database.sql').chmod(0o600)
with tarfile.open('/tmp/smart-recycling-hardware.tgz','r:gz') as archive:archive.extractall(root,filter='data')
subprocess.run(['docker','compose','-p','smart-recycling','build','api','frontend'],cwd=root,check=True)
values=dict(line.split('=',1) for line in (root/'.env').read_text().splitlines() if '=' in line and not line.startswith('#'))
test_db='sr_test_'+uuid.uuid4().hex[:12]
subprocess.run(['docker','exec','smart-recycling-db-1','createdb','-U','smart',test_db],check=True)
try:
    url='postgresql+psycopg://smart:'+values['POSTGRES_PASSWORD']+'@db:5432/'+test_db
    env_file=backup/'test-private.env'
    env_file.write_text('TEST_DATABASE_URL='+url+'\nPROJECT_ROOT=/project\n');env_file.chmod(0o600)
    command=['docker','run','--rm','--network','smart-recycling_default','-v',str(root/'app')+':/project/app:ro','-v',str(root/'tests')+':/project/tests:ro','--env-file',str(env_file),'smart-recycling-api:latest','sh','-c','pip install --no-cache-dir httpx==0.28.1 >/tmp/test-install.log && python /project/tests/test_hardware_api.py']
    try:
        if subprocess.run(command).returncode:raise SystemExit('Isolated PostgreSQL checks failed; production services retained. Credentials omitted.')
    finally:env_file.unlink(missing_ok=True)
finally:
    assert test_db.startswith('sr_test_')
    subprocess.run(['docker','exec','smart-recycling-db-1','dropdb','-U','smart',test_db],check=True)
if (root/'rotate-db-password.once').exists():
    replacement=secrets.token_hex(32)
    sql="ALTER ROLE smart WITH PASSWORD '"+replacement+"';\n"
    result=subprocess.run(['docker','exec','-i','smart-recycling-db-1','psql','-U','smart','-d','smart_recycling','-v','ON_ERROR_STOP=1'],input=sql.encode(),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if result.returncode:raise SystemExit('Database password renewal failed; secrets omitted.')
    env_path=root/'.env';lines=env_path.read_text().splitlines()
    env_path.write_text('\n'.join('POSTGRES_PASSWORD='+replacement if line.startswith('POSTGRES_PASSWORD=') else line for line in lines)+'\n');env_path.chmod(0o600)
    (root/'rotate-db-password.once').unlink()
    print('Internal database credential renewed. Device key and panel login preserved.')
subprocess.run(['docker','compose','-p','smart-recycling','up','-d','--no-deps','api','frontend'],cwd=root,check=True)
print('Production updated after isolated PostgreSQL checks. BACKUP',backup)
