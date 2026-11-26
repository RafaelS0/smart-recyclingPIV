"""Compile the generated Arduino sketches with the same pinned board/toolchain."""
import subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for board,sketch in [('mega2560','SmartRecycling_Mega'),('esp32','SmartRecycling_ESP32')]:
    with tempfile.TemporaryDirectory(prefix='smart-ide-check-') as directory:
        project=Path(directory).resolve()
        assert project.is_relative_to(Path(tempfile.gettempdir()).resolve())
        ini=(ROOT/'firmware'/board/'platformio.ini').read_text(encoding='utf-8-sig')
        ini='[platformio]\nsrc_dir = '+(ROOT/'firmware/arduino-ide'/sketch).as_posix()+'\n\n'+ini
        (project/'platformio.ini').write_text(ini,encoding='utf-8')
        subprocess.run(['python','-m','platformio','run','-d',str(project)],check=True)
print('PASS: both generated .ino wrappers compiled with pinned PlatformIO environments')
