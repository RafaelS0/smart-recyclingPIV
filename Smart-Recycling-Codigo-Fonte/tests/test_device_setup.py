import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'infrastructure'));sys.path.insert(0,str(ROOT/'firmware/raspberry_pi'))
from configurar_dispositivos import esp_header,pi_config,save_private
from gravar import commands
from preflight import load_config
from artifact_filter import publishable
class SetupTests(unittest.TestCase):
 def test_credentials_escaping(self):
  header=esp_header('Rede "Equipe" \\ IoT','senha-com-"aspas"','fixture-key-only','esp32-01')
  values={line.split()[2].split('[')[0]:json.loads(line.split('=',1)[1].rstrip(';')) for line in header.splitlines() if line.startswith('constexpr')}
  self.assertIn('DEVICE_KEY[]="";',esp_header('Rede','senha','','esp32-01'))
  self.assertEqual(values['WIFI_SSID'],'Rede "Equipe" \\ IoT');self.assertEqual(values['DEVICE_KEY'],'fixture-key-only')
  with self.assertRaises(ValueError):esp_header('SSID','senha','bad\nkey','esp32')
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'device.env';save_private(path,pi_config('fixture-key-only','pi-01'))
   self.assertEqual(load_config(path)['DEVICE_KEY'],'fixture-key-only')
   with self.assertRaises(FileExistsError):save_private(path,'replacement')
 def test_upload_plan(self):
  self.assertEqual(len(commands('mega','COM99',True)),1)
  plan=commands('esp32','COM99',False,True)
  self.assertEqual(len(plan),3);self.assertIn('uploadfs',plan[2]);self.assertIn('COM99',plan[1])
 def test_no_private_artifacts(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory)
   for name in ['secrets.h','secrets.h.bak','device.env','device.env.old','.env','device.json']:
    p=root/name;p.write_text('fixture');self.assertFalse(publishable(p,root),name)
   for name in ['secrets.example.h','device.env.example','.env.example','main.cpp']:
    p=root/name;p.write_text('public');self.assertTrue(publishable(p,root),name)
 def test_sketches_match_sources(self):
  for board,name in [('mega2560','SmartRecycling_Mega'),('esp32','SmartRecycling_ESP32')]:
   sketch=ROOT/'firmware/arduino-ide'/name
   self.assertEqual((sketch/'firmware_app.h').read_bytes(),(ROOT/'firmware'/board/'src/main.cpp').read_bytes())
   self.assertEqual((sketch/'config.h').read_bytes(),(ROOT/'firmware'/board/'include/config.h').read_bytes())
if __name__=='__main__':unittest.main()
