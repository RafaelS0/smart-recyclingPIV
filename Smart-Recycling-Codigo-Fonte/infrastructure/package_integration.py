from pathlib import Path
import zipfile
from artifact_filter import publishable
root=Path(__file__).resolve().parents[1]
with zipfile.ZipFile(root/'app/integration/codigos-hardware.zip','w',zipfile.ZIP_DEFLATED) as z:
 for folder in ['firmware','docs','frontend','app','tests','infrastructure','tools']:
  for p in (root/folder).rglob('*'):
   if publishable(p,root):z.write(p,p.relative_to(root))
 for name in ['README.md','docker-compose.yml','.env.example','.gitignore','DEPLOYMENT.md']:
  p=root/name
  if p.exists():z.write(p,p.relative_to(root))
with zipfile.ZipFile(root/'app/integration/dispositivos.zip','w',zipfile.ZIP_DEFLATED) as z:
 for folder in ['firmware','docs','tools']:
  for p in (root/folder).rglob('*'):
   if publishable(p,root):z.write(p,p.relative_to(root))
 z.write(root/'docs/COMECE_AQUI.md','COMECE_AQUI.md')
 z.write(root/'.gitignore','.gitignore')
print('Pacotes publico/por-equipamento gerados sem arquivos privados.')
