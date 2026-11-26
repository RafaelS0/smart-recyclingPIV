import json,os,io,zipfile
from pathlib import Path
from playwright.sync_api import sync_playwright
access=json.loads((Path.home()/'Downloads/smart-recycling-acesso.json').read_text())
private_key=json.loads((Path.home()/'Downloads/smart-recycling-configuracao-privada/device.json').read_text())['DEVICE_KEY']
with sync_playwright() as p:
 executable=next((Path(os.environ['LOCALAPPDATA'])/'ms-playwright').glob('chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe'))
 browser=p.chromium.launch(headless=True,executable_path=str(executable));context=browser.new_context(viewport={'width':390,'height':844})
 page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 assert context.request.get(access['url']+'api/integration/devices').status==401
 page.goto(access['url']+'integracao');page.wait_for_url('**/login');page.locator('#username').fill(access['username']);page.locator('#password').fill(access['password']);page.locator('#submit').click();page.wait_for_url('**/smart_recycling/')
 page.get_by_role('link',name='Conectar equipamentos',exact=True).click();page.wait_for_url('**/integracao')
 page.get_by_role('link',name='Baixar pacote para as placas',exact=False).wait_for()
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 response=context.request.get(access['url']+'api/integration/devices');assert response.status==200
 with zipfile.ZipFile(io.BytesIO(response.body())) as archive:
  names=archive.namelist()
  for name in ['COMECE_AQUI.md','tools/configurar_dispositivos.py','firmware/arduino-ide/SmartRecycling_Mega/SmartRecycling_Mega.ino','firmware/arduino-ide/SmartRecycling_ESP32/SmartRecycling_ESP32.ino','firmware/raspberry_pi/install.py','firmware/raspberry_pi/preflight.py']:
   assert name in names,name
  assert all(private_key.encode() not in archive.read(n) for n in names)
  assert not any(Path(n).name in ['device.env','secrets.h','device.json'] for n in names)
 for path in ['api/resumo','api/eventos?limite=10&pagina=1','api/historico?intervalo=hora','api/historico?intervalo=mes','api/lixeiras','api/dispositivos']:
  assert context.request.get(access['url']+path).status==200,path
 guest=browser.new_context()
 for path in ['api/eventos','api/lixeiras','api/dispositivos']:
  assert guest.request.post(access['url']+path,data={'timestamp':'invalid'}).status==422,path
  assert guest.request.get(access['url']+path).status==401,path
 guest.close()
 assert not errors,errors;browser.close()
print('PASS: pacote das placas, privacidade, guia mobile e rotas do documento na VPS (somente consultas)')
