import json,os,io,zipfile
from pathlib import Path
from datetime import datetime,timezone,timedelta
from playwright.sync_api import sync_playwright
access=json.loads((Path.home()/'Downloads/smart-recycling-acesso.json').read_text());out=Path(__file__).resolve().parents[1]/'artifacts';out.mkdir(exist_ok=True)
with sync_playwright() as p:
 executable=next((Path(os.environ['LOCALAPPDATA'])/'ms-playwright').glob('chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe'))
 browser=p.chromium.launch(headless=True,executable_path=str(executable));context=browser.new_context(viewport={'width':1440,'height':1000})
 page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 assert context.request.get(access['url']+'api/integration/download').status==401
 page.goto(access['url']+'integracao');page.wait_for_url('**/login');page.locator('#username').fill(access['username']);page.locator('#password').fill(access['password']);page.locator('#submit').click();page.wait_for_url('**/smart_recycling/')
 page.get_by_role('link',name='Conectar equipamentos',exact=True).click();page.wait_for_url('**/integracao');page.get_by_role('heading',name='Conectar os equipamentos').wait_for()
 response=context.request.get(access['url']+'api/integration/download');assert response.status==200
 with zipfile.ZipFile(io.BytesIO(response.body())) as archive:
  names=archive.namelist();assert 'firmware/mega2560/src/main.cpp' in names and 'frontend/app/page.tsx' in names
  assert not any('/.pio/' in n or '/node_modules/' in n or n.endswith('/secrets.h') or Path(n).name=='.env' for n in names)
  assert all(access['password'].encode() not in archive.read(n) for n in names)
 page.set_viewport_size({'width':390,'height':844});page.wait_for_function('document.documentElement.scrollWidth<=innerWidth',timeout=3000);page.screenshot(path=str(out/'hardware-guide-mobile.png'),full_page=False)
 # Synthetic fixtures affect ONLY this browser's read responses, never the database.
 now=datetime.now(timezone.utc)
 common={'device_id':'browser-test','simulated':False,'data_current':True,'confidence':.9,'metal':False,'infrared':1,'color_r':140,'color_g':120,'color_b':40,'distance_cm':5.5,'organic_bin_distance_cm':21.2,'recyclable_bin_distance_cm':15.9,'organic_fill_pct':45,'recyclable_fill_pct':92,'organic_weight_g':1500,'recyclable_weight_g':2200,'conveyor_running':False,'servo_position_deg':None}
 first={**common,'id':'fixture-one','object_id':'object-one','timestamp':(now-timedelta(seconds=20)).isoformat(),'material':'reciclavel'}
 last_class={**common,'id':'fixture-two','object_id':'object-two','timestamp':(now-timedelta(seconds=10)).isoformat(),'material':'organico'}
 summary={'total':2,'organic':1,'recyclable':1,'undefined':0,'simulation_mode':False,'legacy_readings':0,'latest':{**common,'id':'fixture-snapshot','timestamp':now.isoformat(),'material':'indefinido'},'latest_classification':last_class}
 page.route('**/api/v1/devices',lambda route:route.fulfill(json=[
     {'device_id':'pi-browser-fixture','role':'raspberry_pi','last_seen':now.isoformat(),'online':True},
     {'device_id':'esp32-academico','role':'esp32','last_seen':now.isoformat(),'online':True,
      'component_status':{'sensor_cor':True,'servo_calha':False,'servo_topo':None},'components_current':True},
 ]))
 page.route('**/api/overview',lambda route:route.fulfill(json=summary))
 page.route('**/api/readings?limit=200',lambda route:route.fulfill(json=[last_class,first]))
 def bin_items():
  past=datetime.fromisoformat(summary['latest']['timestamp'])<datetime.now(timezone.utc)-timedelta(minutes=2)
  return {'items':[{'codigo':code,'distancia_cm':None if past else body[0],'ocupacao_pct':None if past else body[1],
                    'peso_gramas':None if past else body[2],'timestamp':summary['latest']['timestamp'],
                    'estado':'sem_dados_recentes' if past else 'normal'}
                   for code,body in [('organicos',(21.2,45,1500)),('reciclaveis',(15.9,92,2200))]]}
 page.route('**/api/lixeiras',lambda route:route.fulfill(json=bin_items()))

 page.set_viewport_size({'width':1600,'height':1000});page.goto(access['url']);page.get_by_test_id('stat-total').filter(has_text='2').wait_for();assert page.locator('.classification-value').inner_text()=='Orgânico'
 page.get_by_text('Raspberry Pi · pi-browser-fixture · conectado',exact=True).wait_for()
 status=page.get_by_label('Estado informado dos componentes')
 assert status.locator('.sensor-chip').filter(has_text='Sensor de cor').locator('small').inner_text()=='Operante'
 assert status.locator('.sensor-chip').filter(has_text='Servo da calha').locator('small').inner_text()=='Indisponível'
 assert status.locator('.sensor-chip').filter(has_text='Servo do topo').locator('small').inner_text()=='Sem confirmação'

 page.locator('.bin-value').filter(has_text='45%').wait_for();assert page.get_by_text('21,2 cm',exact=True).count()==1;assert page.get_by_text('Atenção: ocupação de 90% ou mais.',exact=True).count()==1
 page.locator('.recharts-pie').wait_for();page.locator('.recharts-line').first.wait_for()
 page.screenshot(path=str(out/'next-dashboard-fixture.png'),full_page=True)
 page.get_by_role('link',name='Histórico',exact=True).click();page.wait_for_url('**/historico/');page.locator('select').select_option('organico');page.locator('tbody tr').filter(has_text='Orgânico').wait_for();assert page.locator('tbody tr').count()==1
 summary['latest']['timestamp']=(now-timedelta(minutes=5)).isoformat()
 page.goto(access['url']);page.locator('.sensor-chip strong').filter(has_text='Sem dados recentes').wait_for();assert all(text=='—' for text in page.locator('.bin-value').all_text_contents())
 page.set_viewport_size({'width':390,'height':844});page.wait_for_function('document.documentElement.scrollWidth<=innerWidth',timeout=3000)
 assert not errors,errors;browser.close()
print('PASS: authenticated code download, no secrets, mobile guide, isolated browser fixtures, latest-classification vs snapshots, real bin fields, alerts, filters and stale readings')
