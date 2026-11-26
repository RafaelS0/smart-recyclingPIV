"""Isolated end-to-end protocol/API checks; never writes to production."""
import os,sys,tempfile,hashlib,json
from pathlib import Path
from datetime import datetime,timezone,timedelta
from fastapi.testclient import TestClient
ROOT=Path(os.getenv('PROJECT_ROOT',str(Path(__file__).resolve().parents[1])))
with tempfile.TemporaryDirectory() as directory:
    os.environ.update(DATABASE_URL=os.getenv('TEST_DATABASE_URL','sqlite:///'+str(Path(directory)/'hardware.db')),DEVICE_KEY='device-test',ADMIN_TOKEN='admin-test',SIMULATION_MODE='false',ROOT_PATH='')
    salt='1234567890abcdef';os.environ['LOGIN_PASSWORD_HASH']=salt+':'+hashlib.scrypt(b'password-test',salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
    sys.path.insert(0,str(ROOT/'app'));os.chdir(ROOT/'app');import main
    with TestClient(main.app,base_url='https://testserver') as client:
        assert client.post('/api/auth/login',json={'username':'admin','password':'password-test'}).status_code==200
        headers={'X-Device-Key':'device-test'}
        stamp=datetime.now(timezone.utc).isoformat()
        event={'schema_version':1,'event_id':'test-event-0001','device_id':'esp32-01','timestamp':stamp,'type':'telemetry','data':{'color_r':100,'metal':None,'organic_weight_g':None,'organic_bin_distance_cm':23.4}}
        assert client.post('/api/v1/events',json=event).status_code==401
        with client.websocket_connect('wss://testserver/ws') as ws:
            assert client.post('/api/v1/events',json=event,headers=headers).status_code==201
            assert ws.receive_json()['type']=='hardware_event'
        overview=client.get('/api/overview').json();assert overview['total']==0 and overview['latest']['organic_bin_distance_cm']==23.4
        assert overview['latest']['metal'] is None and overview['latest']['organic_weight_g'] is None
        assert client.get('/api/readings').json()==[]
        assert client.post('/api/v1/events',json=event,headers=headers).json()['duplicate'] is True
        altered={**event,'data':{'color_r':101}};assert client.post('/api/v1/events',json=altered,headers=headers).status_code==409
        classification={**event,'event_id':'test-class-0001','type':'classification','data':{'material':'reciclavel','object_id':'object-01','metal':True,'fusion':'ai','ai':{'material':'reciclavel','confidence':.9,'model_version':'test-model','inference_ms':22}}}
        assert client.post('/api/v1/events',json=classification,headers=headers).status_code==201
        assert client.post('/api/v1/events',json=classification,headers=headers).status_code==200
        assert client.post('/api/v1/events',json={**classification,'event_id':'new-class-same-object'},headers=headers).status_code==409
        overview=client.get('/api/overview').json();assert overview['total']==1 and overview['recyclable']==1
        assert overview['latest_classification']['ai']['confidence']==.9
        old={**event,'event_id':'old-buffered-event','timestamp':(datetime.now(timezone.utc)-timedelta(days=1)).isoformat(),'data':{'infrared':1}}
        assert client.post('/api/v1/events',json=old,headers=headers).status_code==201
        assert client.get('/api/overview').json()['latest']['event_id']!='old-buffered-event'
        invalid={**event,'event_id':'invalid-event','data':{'organic_fill_pct':101}};assert client.post('/api/v1/events',json=invalid,headers=headers).status_code==422
        assert client.post('/api/v1/events',json={**classification,'event_id':'no-object-event','data':{'material':'organico'}},headers=headers).status_code==422
        assert client.post('/api/v1/events',json={**event,'event_id':'nan-test-event','data':{'infrared':'NaN'}},headers=headers).status_code==422
        assert client.post('/api/v1/events',json={**event,'event_id':'future-event','timestamp':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()},headers=headers).status_code==422
        heartbeat={**event,'event_id':'heartbeat-01','type':'heartbeat','data':{'device_role':'raspberry_pi'}}
        assert client.post('/api/v1/events',json=heartbeat,headers=headers).status_code==201
        assert client.get('/api/overview').json()['total']==1
        assert client.get('/api/v1/devices').json()[0]['online'] is True
        assert len(client.get('/api/readings').json())==1
        # Unknown source time must not be presented as a current sensor sample.
        unknown={**event,'device_id':'no-clock','event_id':'unknown-time','timestamp':None}
        assert client.post('/api/v1/events',json=unknown,headers=headers).status_code==201
        alias={**classification,'event_id':'document-event-001','data':{**classification['data'],'object_id':'doc-object-1','material':'organico'}}
        assert client.post('/api/eventos',json=alias,headers=headers).status_code==201
        assert client.post('/api/v1/events',json=alias,headers=headers).json()['duplicate'] is True
        assert client.post('/api/eventos',json=event,headers=headers).status_code==422
        bin_event={**event,'event_id':'document-bin-001','timestamp':datetime.now(timezone.utc).isoformat(),'data':{'organic_fill_pct':92,'organic_weight_g':1500,'organic_bin_distance_cm':7}}
        assert client.post('/api/lixeiras',json=bin_event,headers=headers).status_code==201
        assert client.get('/api/lixeiras').json()['items'][0]['estado']=='cheia'
        assert client.get('/api/lixeiras').json()['items'][0]['peso_gramas']==1500
        assert client.post('/api/lixeiras',json={**bin_event,'event_id':'rec-bin-partial','timestamp':datetime.now(timezone.utc).isoformat(),'data':{'recyclable_fill_pct':34}},headers=headers).status_code==201
        bins=client.get('/api/lixeiras').json()['items'];assert bins[0]['peso_gramas']==1500 and bins[1]['ocupacao_pct']==34
        assert client.post('/api/dispositivos',json={**heartbeat,'event_id':'doc-heartbeat-001'},headers=headers).status_code==201
        assert client.get('/api/resumo').json()['total']==2
        assert client.get('/api/resumo').json()['organicos']==1
        page=client.get('/api/eventos?limite=1&pagina=1').json()
        assert page['total']==2 and len(page['items'])==1 and page['total_paginas']==2
        assert client.get('/api/eventos?pagina=0').status_code==422
        assert sum(r['organicos']+r['reciclaveis']+r['desconhecidos'] for r in client.get('/api/historico?intervalo=hora').json()['items'])==2
        assert client.get('/api/historico?intervalo=semana').status_code==422
        assert client.post('/api/telemetry',json={'device_id':'legacy','material':'reciclavel'},headers=headers).status_code==201
        mixed=client.get('/api/eventos?limite=2&pagina=1').json()
        assert mixed['total']==3 and len(mixed['items'])==2
        assert len(client.get('/api/eventos?limite=2&pagina=2').json()['items'])==1
        assert sum(r['organicos']+r['reciclaveis']+r['desconhecidos'] for r in client.get('/api/historico?intervalo=dia').json()['items'])==3
        before=client.get('/api/overview').json()['total']
        assert client.get('/api/device/verify',headers=headers).json()['authenticated'] is True
        assert client.get('/api/device/verify').status_code==401
        assert client.get('/api/overview').json()['total']==before
        session_token=client.cookies.get('sr_session')
        client.cookies.clear()
        for path in ['/api/eventos','/api/lixeiras','/api/dispositivos','/api/resumo','/api/historico']:
            assert client.get(path).status_code==401,path
        assert client.post('/api/dispositivos',json={**heartbeat,'event_id':'doc-no-key'}).status_code==401
        public_stamp=datetime.now(timezone.utc).isoformat()
        simple={'event_id':'daijwdji12jid1','timestamp':public_stamp,'material':'organico',
                'metal':0,'ir':1,'color':[255,255,255],'rasp_material':'organico',
                'rasp_acuracia':.93,'acuracia_final':.95}
        with client.websocket_connect('wss://testserver/ws',headers={'Cookie':'sr_session='+session_token}) as ws:
            registered=client.post('/api/eventos',json=simple)
            assert registered.status_code==201 and registered.json()=={'event_id':simple['event_id'],'duplicate':False}
            assert ws.receive_json()['event_type']=='classification'
        assert client.post('/api/eventos',json=simple).status_code==200
        assert client.post('/api/eventos',json={**simple,'color':[0,0,0]}).status_code==409
        assert client.post('/api/eventos',json={**simple,'metal':2}).status_code==422
        assert client.post('/api/eventos',json={**simple,'color':[256,10,10]}).status_code==422
        assert client.post('/api/eventos',json={**simple,'rasp_acuracia':1.01}).status_code==422
        positions={'timestamp':public_stamp,'reciclaveis_cm':None,'organicos_cm':30.1}
        assert client.post('/api/lixeiras',json=positions).status_code==201
        assert client.post('/api/lixeiras',json=positions).status_code==200
        assert client.post('/api/lixeiras',json={**positions,'organicos_cm':-2}).status_code==422
        status={'timestamp':public_stamp,'sensor_indutivo':True,'sensor_cor':True,
                'sensor_ir':True,'raspberry':True,'servo_topo':None,'servo_calha':False}
        assert client.post('/api/dispositivos',json=status).status_code==201
        assert client.post('/api/dispositivos',json={**status,'servo_topo':1}).status_code==422
        assert client.post('/api/dispositivos',json={'timestamp':public_stamp}).status_code==422
        assert client.get('/api/dispositivos').status_code==401
        client.cookies.set('sr_session',session_token)
        row=client.get('/api/overview').json()['latest_classification']
        assert row['event_id']==simple['event_id'] and row['metal'] is False and row['infrared']==1
        assert row['color_r']==255 and row['confidence']==.95 and row['rasp_acuracia']==.93
        assert client.get('/api/overview').json()['total']==before+1
        bins=client.get('/api/lixeiras').json()['items']
        assert bins[0]['distancia_cm']==30.1 and bins[0]['ocupacao_pct'] is None
        assert bins[1]['distancia_cm'] is None and bins[1]['ocupacao_pct'] is None
        device=next(d for d in client.get('/api/dispositivos').json()['items'] if d['device_id']=='esp32-academico')
        assert device['component_status']['servo_calha'] is False and device['components_current'] is True
        main.engine.dispose()
    main.engine.dispose()
print('PASS: versioned telemetry, real-null states, one classification per object, dedup/conflicts, WebSocket, heartbeat, timestamps and invalid payloads')
