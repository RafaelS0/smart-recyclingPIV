import json,os
from pathlib import Path
from playwright.sync_api import sync_playwright
access=json.loads((Path.home()/'Downloads/smart-recycling-acesso.json').read_text());out=Path(__file__).resolve().parents[1]/'artifacts';out.mkdir(exist_ok=True)
with sync_playwright() as p:
    executable=next((Path(os.environ['LOCALAPPDATA'])/'ms-playwright').glob('chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe'))
    browser=p.chromium.launch(headless=True,executable_path=str(executable));context=browser.new_context(viewport={'width':1440,'height':1000},permissions=['clipboard-read','clipboard-write'])
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(access['url']+'tutorial');page.wait_for_url('**/login')
    page.locator('#username').fill(access['username']);page.locator('#password').fill(access['password']);page.locator('#submit').click();page.wait_for_url('**/smart_recycling/')
    page.get_by_role('link',name='Tutorial da API',exact=True).click();page.wait_for_url('**/tutorial')
    assert len(page.locator('.guide-sections section').all())==7
    page.locator('#check-health').click();page.locator('#health-result').filter(has_text='API disponível').wait_for()
    page.locator('#conexao .copy-code').first.click();assert page.evaluate('navigator.clipboard.readText()')=='curl https://mrvbot.com/smart_recycling/api/health'
    assert access['password'] not in page.content()
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path=str(out/'tutorial-desktop.png'),full_page=False)
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path=str(out/'tutorial-mobile.png'),full_page=False)
    page.get_by_role('link',name='4. Campos',exact=True).click();assert page.url.endswith('#campos')
    page.locator('.top-actions').get_by_role('link',name='Referência da API').click();page.wait_for_url('**/docs');page.locator('.swagger-ui').wait_for()
    assert not errors,errors
    browser.close()
print('PASS: tutorial protegido, navegacao pelo painel, 7 passos, saude da API, copiar codigo, desktop/mobile e referencia OpenAPI')
