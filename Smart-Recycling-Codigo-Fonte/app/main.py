import os
import asyncio
import hashlib
import secrets
import hmac
import time
from collections import defaultdict, deque
from datetime import timedelta
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Literal
from fastapi import FastAPI, Depends, Header, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Boolean, desc, func
from sqlalchemy.orm import declarative_base, sessionmaker, Session

DB_URL = os.environ['DATABASE_URL']
DEVICE_KEY = os.environ['DEVICE_KEY']
ADMIN_TOKEN = os.environ['ADMIN_TOKEN']
SIMULATION_MODE = os.getenv('SIMULATION_MODE', 'false').lower() == 'true'
engine = create_engine(DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Reading(Base):
    __tablename__ = 'readings'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    device_id = Column(String(80), nullable=False)
    simulated = Column(Boolean, nullable=False)
    material = Column(String(24), nullable=False)
    confidence = Column(Float, nullable=True)
    metal = Column(Boolean, nullable=False)
    infrared = Column(Float, nullable=True)
    color_r = Column(Integer, nullable=True)
    color_g = Column(Integer, nullable=True)
    color_b = Column(Integer, nullable=True)
    distance_cm = Column(Float, nullable=True)
    organic_fill_pct = Column(Float, nullable=True)
    recyclable_fill_pct = Column(Float, nullable=True)
    organic_weight_g = Column(Float, nullable=True)
    recyclable_weight_g = Column(Float, nullable=True)
    conveyor_running = Column(Boolean, nullable=False)
    servo_position_deg = Column(Float, nullable=True)

class Command(Base):
    __tablename__ = 'commands'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    command = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default='pending')
    device_id = Column(String(80), nullable=False)

class UserSession(Base):
    __tablename__ = 'user_sessions'
    token_hash = Column(String(64), primary_key=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)

LOGIN_USER = os.getenv('LOGIN_USER', 'admin')
LOGIN_HASH = os.getenv('LOGIN_PASSWORD_HASH', '')
COOKIE = 'sr_session'
BASE_PATH = os.getenv('ROOT_PATH', '')
login_attempts = defaultdict(deque)

def session_valid(token):
    if not token:
        return False
    with SessionLocal() as db:
        row = db.get(UserSession, hashlib.sha256(token.encode()).hexdigest())
        return bool(row and row.expires_at.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc))

def check_origin(request):
    origin = request.headers.get('origin')
    expected = 'https://' + request.headers.get('host', '')
    if origin and origin != expected:
        raise HTTPException(403, 'Origem nao permitida')

class Telemetry(BaseModel):
    device_id: str = Field(min_length=1, max_length=80)
    simulated: bool = False
    material: Literal['organico', 'reciclavel', 'indefinido']
    confidence: float | None = Field(default=None, ge=0, le=1)
    metal: bool = False
    infrared: float | None = None
    color_r: int | None = Field(default=None, ge=0, le=255)
    color_g: int | None = Field(default=None, ge=0, le=255)
    color_b: int | None = Field(default=None, ge=0, le=255)
    distance_cm: float | None = Field(default=None, ge=0)
    organic_fill_pct: float | None = Field(default=None, ge=0, le=100)
    recyclable_fill_pct: float | None = Field(default=None, ge=0, le=100)
    organic_weight_g: float | None = Field(default=None, ge=0)
    recyclable_weight_g: float | None = Field(default=None, ge=0)
    conveyor_running: bool = False
    servo_position_deg: float | None = Field(default=None, ge=0, le=180)

class CommandRequest(BaseModel):
    command: Literal['start', 'pause', 'stop']
    device_id: str = Field(default='smart-recycling-01', min_length=1, max_length=80)

clients: set[WebSocket] = set()

def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def device_auth(x_device_key: str | None = Header(default=None)):
    if not hmac.compare_digest(x_device_key or "", DEVICE_KEY):
        raise HTTPException(401, 'Credencial de dispositivo inválida')

def admin_auth(authorization: str | None = Header(default=None)):
    if authorization != f'Bearer {ADMIN_TOKEN}':
        raise HTTPException(401, 'Token de administrador inválido')

def serialize(row):
    return {c.name: (getattr(row, c.name).isoformat() if isinstance(getattr(row, c.name), datetime) else getattr(row, c.name)) for c in row.__table__.columns}

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title='Smart Recycling API', version='0.1.0', lifespan=lifespan, root_path=os.getenv('ROOT_PATH', ''))
@app.middleware('http')
async def protect_dashboard(request: Request, call_next):
    path = request.url.path
    if BASE_PATH and path.startswith(BASE_PATH + '/'):
        path = path[len(BASE_PATH):]
    public = path in ['/login', '/api/auth/login', '/api/health', '/api/telemetry', '/api/v1/events', '/api/eventos', '/api/lixeiras', '/api/dispositivos'] or path.startswith('/static/') or path.startswith('/api/device/')
    if path in ['/api/eventos','/api/lixeiras','/api/dispositivos'] and request.method != 'POST':
        public=False
    if not public and not session_valid(request.cookies.get(COOKIE)):
        if path.startswith('/api/'):
            return JSONResponse({'detail': 'Sessao expirada. Entre novamente.'}, status_code=401)
        return RedirectResponse(BASE_PATH + '/login', status_code=303)
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

class LoginRequest(BaseModel):
    username: str = Field(max_length=80)
    password: str = Field(max_length=256)

@app.get('/login')
def login_page():
    return FileResponse('static/login.html')

@app.post('/api/auth/login')
def login(payload: LoginRequest, request: Request):
    check_origin(request)
    ip = request.headers.get('x-real-ip') or request.client.host
    now = time.monotonic()
    attempts = login_attempts[ip]
    while attempts and attempts[0] < now - 300:
        attempts.popleft()
    if len(attempts) >= 8:
        raise HTTPException(429, 'Muitas tentativas. Aguarde 5 minutos.')
    attempts.append(now)
    try:
        salt, expected = LOGIN_HASH.split(':', 1)
        actual = hashlib.scrypt(payload.password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
        valid = hmac.compare_digest(actual, expected) and hmac.compare_digest(payload.username, LOGIN_USER)
    except ValueError:
        valid = False
    if not valid:
        raise HTTPException(401, 'Usuario ou senha incorretos.')
    attempts.clear()
    token = secrets.token_urlsafe(48)
    with SessionLocal() as db:
        db.query(UserSession).filter(UserSession.expires_at < datetime.now(timezone.utc)).delete()
        db.add(UserSession(token_hash=hashlib.sha256(token.encode()).hexdigest(), expires_at=datetime.now(timezone.utc) + timedelta(hours=8)))
        db.commit()
    response = JSONResponse({'ok': True})
    response.set_cookie(COOKIE, token, max_age=28800, httponly=True, secure=True, samesite='strict', path=BASE_PATH + '/')
    return response

@app.post('/api/auth/logout')
def logout(request: Request):
    check_origin(request)
    token = request.cookies.get(COOKIE, '')
    with SessionLocal() as db:
        db.query(UserSession).filter(UserSession.token_hash == hashlib.sha256(token.encode()).hexdigest()).delete()
        db.commit()
    response = JSONResponse({'ok': True})
    response.delete_cookie(COOKIE, path=BASE_PATH + '/', secure=True, httponly=True, samesite='strict')
    return response

app.mount('/static', StaticFiles(directory='static'), name='static')

@app.get('/')
def home():
    return FileResponse('static/index.html')

@app.get('/tutorial')
def tutorial():
    return FileResponse('static/tutorial.html')

@app.get('/integracao')
def integration_guide():
    return FileResponse('static/integration.html')

@app.get('/api/integration/download')
def integration_download():
    return FileResponse('integration/codigos-hardware.zip', filename='smart-recycling-integracao.zip', media_type='application/zip')

@app.get('/api/integration/devices')
def devices_download():
    return FileResponse('integration/dispositivos.zip', filename='smart-recycling-placas.zip', media_type='application/zip')

@app.get('/api/health')
def health():
    return {'ok': True, 'simulation_mode': SIMULATION_MODE}

@app.post('/api/telemetry', dependencies=[Depends(device_auth)], status_code=201)
async def ingest(payload: Telemetry, db: Session = Depends(db_session)):
    if payload.simulated and not SIMULATION_MODE:
        raise HTTPException(403, 'Simulação desabilitada')
    record = Reading(**payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    message = {'type': 'reading', 'data': serialize(record)}
    for ws in list(clients):
        try:
            await ws.send_json(message)
        except Exception:
            clients.discard(ws)
    return {'id': record.id}

@app.get('/api/device/verify', dependencies=[Depends(device_auth)])
def verify_device_key():
    return {'authenticated':True,'schema_version':1}

@app.get('/api/overview')
def overview(db: Session = Depends(db_session)):
    total = db.query(func.count(Reading.id)).filter(Reading.simulated.is_(False)).scalar() or 0
    organic = db.query(func.count(Reading.id)).filter(Reading.simulated.is_(False)).filter(Reading.material == 'organico').scalar() or 0
    recyclable = db.query(func.count(Reading.id)).filter(Reading.simulated.is_(False)).filter(Reading.material == 'reciclavel').scalar() or 0
    latest = db.query(Reading).filter(Reading.simulated.is_(False)).order_by(desc(Reading.id)).first()
    counts, hardware_latest, hardware_class = hardware_overview(db)
    legacy_latest = serialize(latest) if latest else None
    current = hardware_latest if hardware_latest and (not legacy_latest or hardware_latest['timestamp'] > legacy_latest['timestamp']) else legacy_latest
    last_class = hardware_class if hardware_class and (not legacy_latest or hardware_class['timestamp'] > legacy_latest['timestamp']) else legacy_latest
    return {'total': total + sum(counts.values()), 'organic': organic + counts.get('organico',0),
            'recyclable': recyclable + counts.get('reciclavel',0),
            'undefined': total-organic-recyclable + counts.get('indefinido',0),
            'latest': current, 'latest_classification': last_class, 'legacy_readings':total, 'simulation_mode':SIMULATION_MODE}

@app.get('/api/readings')
def readings(limit: int = 40, db: Session = Depends(db_session)):
    limit = max(1, min(limit, 200))
    legacy = [serialize(r) for r in db.query(Reading).filter(Reading.simulated.is_(False)).order_by(desc(Reading.id)).limit(limit).all()]
    combined = legacy + hardware_history(db,limit)
    return sorted(combined,key=lambda r:datetime.fromisoformat(r['timestamp']),reverse=True)[:limit]

@app.post('/api/commands', dependencies=[Depends(admin_auth)], status_code=202)
def create_command(payload: CommandRequest, db: Session = Depends(db_session)):
    raise HTTPException(403, 'Comandos fisicos bloqueados ate validacao do firmware e dos intertravamentos')

@app.get('/api/device/commands', dependencies=[Depends(device_auth)])
def pending_commands(device_id: str, db: Session = Depends(db_session)):
    return [serialize(c) for c in db.query(Command).filter(Command.device_id == device_id, Command.status == 'pending').order_by(Command.id).limit(10)]

class Ack(BaseModel):
    status: Literal['accepted', 'executed', 'rejected']

@app.post('/api/device/commands/{command_id}/ack', dependencies=[Depends(device_auth)])
def acknowledge(command_id: int, ack: Ack, db: Session = Depends(db_session)):
    cmd = db.get(Command, command_id)
    if not cmd:
        raise HTTPException(404, 'Comando não encontrado')
    cmd.status = ack.status
    db.commit()
    return {'ok': True}

@app.websocket('/ws')
async def websocket(ws: WebSocket):
    if not session_valid(ws.cookies.get(COOKIE)):
        await ws.close(code=4401)
        return
    origin = ws.headers.get('origin')
    if origin and origin != 'https://' + ws.headers.get('host', ''):
        await ws.close(code=4403)
        return
    await ws.accept()
    clients.add(ws)
    try:
        while True:
            await ws.receive_text()
            if not session_valid(ws.cookies.get(COOKIE)):
                await ws.close(code=4401)
                break
    except WebSocketDisconnect:
        pass
    finally:
        clients.discard(ws)

from hardware import register_hardware
hardware_overview, hardware_history = register_hardware(app, Base, SessionLocal, clients, device_auth, db_session, Reading, serialize, overview)
