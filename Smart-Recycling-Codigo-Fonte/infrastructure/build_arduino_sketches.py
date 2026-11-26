from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[1]
for board,name in [('mega2560','SmartRecycling_Mega'),('esp32','SmartRecycling_ESP32')]:
    target=root/'firmware/arduino-ide'/name;target.mkdir(parents=True,exist_ok=True)
    (target/(name+'.ino')).write_text('// Application is kept in a header to avoid Arduino auto-prototype rewriting.\n#include "firmware_app.h"\n',encoding='utf-8')
    shutil.copyfile(root/'firmware'/board/'src/main.cpp',target/'firmware_app.h')
    for file in (root/'firmware'/board/'include').glob('*.h'):
        if file.name!='secrets.h':shutil.copyfile(file,target/file.name)
