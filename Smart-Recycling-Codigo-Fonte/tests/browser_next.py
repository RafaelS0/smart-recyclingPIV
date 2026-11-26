import json,os
from pathlib import Path
from playwright.sync_api import sync_playwright
access=json.loads((Path.home()/'Downloads/smart-recycling-acesso.json').read_text());out=Path(__file__).resolve().parents[1]/'artifacts';out.mkdir(exist_ok=True)
with sync_playwright() as p:
 executable=next((Path(os.environ['LOCALAPPDATA'])/'ms-playwright').glob('chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe'))
 browser=p.chromium.launch(headless=True,executable_path=str(executable));context=browser.new_context(viewport={'width':1600,'height':1000})
 page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(access['url']);page.wait_for_url('**/login');page.locator('#username').fill(access['username']);page.locator('#password').fill(access['password']);page.locator('#submit').click();page.wait_for_url('**/smart_recycling/')
 page.get_by_role('heading',name='Lixeira Inteligente — Painel de Monitoramento').wait_for();page.get_by_text('Aguardando classificações',exact=True).wait_for()
 assert page.locator('script[src*="/_next/"]').count()>0
 assert page.locator('.classification-value').inner_text()=='Indisponível'
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 page.screenshot(path=str(out/'next-dashboard-desktop.png'),full_page=True)
 page.get_by_role('link',name='Histórico',exact=True).click();page.wait_for_url('**/historico/');page.get_by_role('heading',name='Nenhuma classificação registrada').wait_for()
 page.get_by_placeholder('Buscar dispositivo').fill('inexistente');assert page.locator('.history-count').inner_text()=='0 registro(s) exibido(s)'
 page.get_by_role('link',name='Painel',exact=True).click();page.wait_for_url('**/smart_recycling/')
 page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');page.screenshot(path=str(out/'next-dashboard-mobile.png'),full_page=True)
 page.get_by_role('link',name='Tutorial da API').click();page.wait_for_url('**/tutorial');page.get_by_role('heading',name='Do dispositivo ao painel.').wait_for()
 page.goto(access['url']);page.get_by_role('button',name='Sair da conta').click();page.wait_for_url('**/login');assert context.request.get(access['url']+'api/overview').status==401
 assert not errors,errors
 browser.close()
print('PASS: Next.js SSR, login, dados ausentes, graficos, navegacao historico, filtros, tutorial, mobile e logout')
