import urllib.request,urllib.error,json,http.cookiejar,pathlib,subprocess,hashlib
root=pathlib.Path('/opt/smart-recycling');access=json.loads((root/'access.json').read_text());base=access['url']
jar=http.cookiejar.CookieJar();opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
def request(path='',data=None):
    req=urllib.request.Request(base+path,data=data,headers={'Content-Type':'application/json','Origin':'https://mrvbot.com'})
    try:
        with opener.open(req,timeout=20) as r:return r.status,r.read()
    except urllib.error.HTTPError as e:return e.code,e.read()
assert request('api/overview')[0]==401
assert request('login')[0]==200
assert request('static/style.css')[0]==200
assert request('api/auth/login',json.dumps({'username':access['username'],'password':access['password']}).encode())[0]==200
assert request()[0]==200
assert request('api/overview')[0]==200
assert request('docs')[0]==200
assert request('openapi.json')[0]==200
assert request('api/telemetry',b'{}')[0]==401
assert request('api/auth/logout',b'{}')[0]==200
assert request('api/overview')[0]==401
backup=next(p for p in sorted((root/'backups').iterdir()) if (p/'sites-before.json').exists())
before=json.loads((backup/'sites-before.json').read_text())
for url,value in before.items():
    if 'status' not in value:continue
    with urllib.request.urlopen(url,timeout=20) as r:
        assert r.status==value['status'] and hashlib.sha256(r.read()).hexdigest()==value['sha256'],url
previous=json.loads((backup/'containers.json').read_text())
current=subprocess.check_output(['docker','ps','--format','{{.Names}}']).decode().splitlines()
assert set(previous)<=set(current)
print('PASS: login, sessao, logout, CSS, API, OpenAPI, telemetria protegida, sites e containers anteriores preservados')
