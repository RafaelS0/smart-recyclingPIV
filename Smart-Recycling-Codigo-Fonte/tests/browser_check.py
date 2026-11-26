import json,os
from pathlib import Path
from playwright.sync_api import sync_playwright
access=json.loads((Path.home()/'Downloads/smart-recycling-acesso.json').read_text())
out=Path(__file__).resolve().parents[1]/'artifacts';out.mkdir(exist_ok=True)
with sync_playwright() as p:
    executable=next((Path(os.environ['LOCALAPPDATA'])/'ms-playwright').glob('chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe'))
    browser=p.chromium.launch(headless=True,executable_path=str(executable))
    context=browser.new_context(viewport={'width':1440,'height':1050},device_scale_factor=1)
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(access['url']);page.wait_for_url('**/login');page.locator('#username').wait_for()
    page.screenshot(path=str(out/'login-desktop.png'),full_page=True)
    page.locator('#username').fill(access['username']);page.locator('#password').fill('senha-incorreta');page.locator('#submit').click();page.get_by_role('alert').filter(has_text='incorretos').wait_for()
    page.locator('#password').fill(access['password']);page.locator('#submit').click();page.wait_for_url('**/smart_recycling/');page.get_by_text('DISPOSITIVO DESCONECTADO',exact=False).wait_for()
    page.wait_for_function("document.getElementById('total').textContent==='0'")
    page.wait_for_function('socket && socket.readyState===1')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path=str(out/'dashboard-desktop.png'),full_page=True)
    assert context.request.get(access['url']+'api/overview').status==200
    cookies=context.cookies();assert any(c['name']=='sr_session' and c['httpOnly'] and c['secure'] for c in cookies)
    page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(out/'dashboard-mobile.png'),full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.locator('#logout').click();page.wait_for_url('**/login')
    assert context.request.get(access['url']+'api/overview').status==401
    page.screenshot(path=str(out/'login-mobile.png'),full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors,errors
    browser.close()
print('PASS: navegador desktop/mobile, login incorreto/correto, sessao segura, painel, API protegida, logout, sem overflow e sem erros JavaScript')
