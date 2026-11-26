from pathlib import Path
FORBIDDEN={'.pio','__pycache__','node_modules','.next','integration','.git'}
def publishable(path,root):
    relative=path.relative_to(root)
    if not path.is_file() or any(part in FORBIDDEN for part in relative.parts):return False
    name=path.name
    if name in {'device.json','access.json'}:return False
    if name.startswith('secrets.') and name!='secrets.example.h':return False
    if name.startswith('device.env') and name!='device.env.example':return False
    if name.startswith('.env') and name!='.env.example':return False
    return path.suffix not in {'.pyc','.tsbuildinfo','.bak','.old'}
