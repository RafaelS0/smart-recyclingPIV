"""Testes isolados: nao acessam a VPS nem o banco de producao."""
import os
import sys
import tempfile
import hashlib
from pathlib import Path
from fastapi.testclient import TestClient

with tempfile.TemporaryDirectory() as directory:
    os.environ.update(DATABASE_URL='sqlite:///'+str(Path(directory)/'test.db'), DEVICE_KEY='test-device', ADMIN_TOKEN='test-admin', SIMULATION_MODE='false')
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
    os.chdir(Path(__file__).resolve().parents[1]/'app')
    salt="1234567890abcdef"
    os.environ["LOGIN_PASSWORD_HASH"]=salt+":"+hashlib.scrypt(b"test-password",salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
    import main
    with TestClient(main.app, base_url="https://testserver") as client:
        assert client.get("/api/overview").status_code==401
        assert client.get("/",follow_redirects=False).status_code==303
        assert client.get("/login").status_code==200
        assert client.get("/tutorial",follow_redirects=False).status_code==303
        assert client.post("/api/auth/login",json={"username":"admin","password":"wrong"}).status_code==401
        login=client.post("/api/auth/login",json={"username":"admin","password":"test-password"})
        assert login.status_code==200
        assert "HttpOnly" in login.headers["set-cookie"] and "Secure" in login.headers["set-cookie"]
        assert client.get('/tutorial').status_code==200
        assert 'X-Device-Key' in client.get('/tutorial').text
        assert client.get('/static/tutorial.js').status_code==200
        assert client.get('/api/health').json()['simulation_mode'] is False
        assert client.get('/api/overview').json()['latest'] is None
        payload={'device_id':'test-esp32','material':'reciclavel','metal':True}
        assert client.post('/api/telemetry',json=payload).status_code==401
        headers={'X-Device-Key':'test-device'}
        assert client.post('/api/telemetry',json={**payload,'simulated':True},headers=headers).status_code==403
        assert client.post('/api/telemetry',json={**payload,'distance_cm':-1},headers=headers).status_code==422
        with client.websocket_connect('wss://testserver/ws') as ws:
            assert client.post('/api/telemetry',json=payload,headers=headers).status_code==201
            assert ws.receive_json()['type']=='reading'
        summary=client.get('/api/overview').json()
        assert summary['total']==1 and summary['recyclable']==1
        assert summary['latest']['organic_weight_g'] is None
        assert client.post('/api/commands',json={'command':'start'},headers={'Authorization':'Bearer test-admin'}).status_code==403
        assert client.post('/api/auth/logout',headers={'Origin':'https://evil.example'}).status_code==403
        cookie=client.cookies.get('sr_session')
        assert client.post('/api/auth/logout').status_code==200
        assert client.get('/api/overview').status_code==401
        client.cookies.set('sr_session',cookie)
        assert client.get('/api/overview').status_code==401
    main.engine.dispose()
print('PASS: banco isolado, ausencia de dados, autenticacao, simulacao bloqueada, validacao, persistencia, WebSocket, agregacao e comandos bloqueados')

