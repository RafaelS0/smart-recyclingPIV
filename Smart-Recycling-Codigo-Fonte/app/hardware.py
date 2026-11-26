"""Versioned hardware protocol. Additive tables; legacy telemetry stays compatible."""
import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Annotated, Literal
from fastapi import Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ConfigDict, AwareDatetime, StrictBool, model_validator
from sqlalchemy import Column, String, DateTime, JSON, UniqueConstraint, func, desc
from sqlalchemy.exc import IntegrityError

Material = Literal['organico', 'reciclavel', 'indefinido']
Digital = Annotated[int, Field(strict=True, ge=0, le=1)]
ColorChannel = Annotated[int, Field(strict=True, ge=0, le=255)]
Confidence = Annotated[float, Field(ge=0, le=1)]
Distance = Annotated[float, Field(ge=0)]
ACADEMIC_DEVICE = 'esp32-academico'
ACADEMIC_EXPIRY_SECONDS = 150


class AcademicPayload(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    timestamp: AwareDatetime

    @model_validator(mode='after')
    def normalize_timestamp(self):
        self.timestamp = self.timestamp.astimezone(timezone.utc)
        if self.timestamp > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError('Timestamp no futuro. Verifique o relógio do ESP32.')
        return self


class AcademicClassification(AcademicPayload):
    event_id: str = Field(min_length=1, max_length=100, pattern=r'^[A-Za-z0-9._:-]+$')
    material: Material
    metal: Digital | None = None
    ir: Digital | None = None
    color: tuple[ColorChannel, ColorChannel, ColorChannel] | None = None
    rasp_material: Material | None = None
    rasp_acuracia: Confidence | None = None
    acuracia_final: Confidence | None = None


class AcademicBins(AcademicPayload):
    reciclaveis_cm: Distance | None
    organicos_cm: Distance | None


class AcademicStatus(AcademicPayload):
    sensor_indutivo: StrictBool | None
    sensor_cor: StrictBool | None
    sensor_ir: StrictBool | None
    raspberry: StrictBool | None
    servo_topo: StrictBool | None
    servo_calha: StrictBool | None


class AIResult(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    material: Literal['organico', 'reciclavel', 'indefinido']
    confidence: float | None = Field(default=None, ge=0, le=1)
    model_version: str = Field(max_length=100)
    inference_ms: float = Field(ge=0)

class HardwareData(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    device_role: Literal['arduino', 'esp32', 'raspberry_pi'] = 'esp32'
    material: Literal['organico', 'reciclavel', 'indefinido'] | None = None
    controller_object_id: str | None = Field(default=None, max_length=100)
    object_id: str | None = Field(default=None, min_length=1, max_length=100)
    confidence: float | None = Field(default=None, ge=0, le=1)
    metal: bool | None = None
    infrared: float | None = None
    infrared_mode: Literal['digital','analog'] | None = None
    color_r: int | None = Field(default=None, ge=0, le=255)
    color_g: int | None = Field(default=None, ge=0, le=255)
    color_b: int | None = Field(default=None, ge=0, le=255)
    color_pulse_us: list[int | None] | None = Field(default=None, min_length=3, max_length=3)
    color_calibrated: bool | None = None
    distance_cm: float | None = Field(default=None, ge=0)
    organic_bin_distance_cm: float | None = Field(default=None, ge=0)
    recyclable_bin_distance_cm: float | None = Field(default=None, ge=0)
    organic_fill_pct: float | None = Field(default=None, ge=0, le=100)
    recyclable_fill_pct: float | None = Field(default=None, ge=0, le=100)
    organic_weight_g: float | None = Field(default=None, ge=0)
    recyclable_weight_g: float | None = Field(default=None, ge=0)
    conveyor_running: bool | None = None
    servo_position_deg: float | None = Field(default=None, ge=0, le=180)
    sensor_material: Literal['organico','reciclavel','indefinido'] | None = None
    ai: AIResult | None = None
    rasp_material: Material | None = None
    rasp_acuracia: Confidence | None = None
    component_status: dict[str, StrictBool | None] | None = None
    fusion: Literal['ai','sensors','agreement','divergence','unavailable'] | None = None
    faults: list[str] = Field(default_factory=list, max_length=32)

class HardwareEvent(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_version: Literal[1]
    event_id: str = Field(min_length=8, max_length=120, pattern=r'^[A-Za-z0-9._:-]+$')
    device_id: str = Field(min_length=1, max_length=80, pattern=r'^[A-Za-z0-9._:-]+$')
    timestamp: AwareDatetime | None = None
    type: Literal['telemetry','classification','heartbeat']
    data: HardwareData

    @model_validator(mode='after')
    def validate_event(self):
        if self.type == 'classification' and (not self.data.object_id or not self.data.material):
            raise ValueError('classification requires object_id and material')
        if self.timestamp and self.timestamp > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError('timestamp is in the future; synchronize the device clock')
        if any(len(f)>160 for f in self.data.faults):
            raise ValueError('fault message too long')
        if self.timestamp:
            self.timestamp=self.timestamp.astimezone(timezone.utc)
        return self


def register_hardware(app, Base, SessionLocal, clients, device_auth, db_session, legacy_reading=None, serialize_legacy=None, overview=None):
    class HardwareRecord(Base):
        __tablename__ = 'hardware_events'
        event_id = Column(String(120), primary_key=True)
        device_id = Column(String(80), nullable=False, index=True)
        object_id = Column(String(100), nullable=True)
        kind = Column(String(20), nullable=False, index=True)
        material = Column(String(24), nullable=True, index=True)
        source_timestamp = Column(DateTime(timezone=True), nullable=True)
        received_at = Column(DateTime(timezone=True), nullable=False, index=True)
        payload = Column(JSON, nullable=False)
        digest = Column(String(64), nullable=False)
        __table_args__ = (UniqueConstraint('device_id','object_id', name='uq_hardware_object'),)

    class DevicePresence(Base):
        __tablename__ = 'hardware_devices'
        device_id = Column(String(80), primary_key=True)
        role = Column(String(24), nullable=False)
        last_seen = Column(DateTime(timezone=True), nullable=False)

    def project(record):
        data = dict(record.payload)
        stamp = record.source_timestamp or record.received_at
        event_id = record.object_id if record.event_id.startswith('academico:class:') else record.event_id
        data.update(id=record.event_id, event_id=event_id, device_id=record.device_id,
                    timestamp=stamp.replace(tzinfo=timezone.utc).isoformat(),
                    received_at=record.received_at.replace(tzinfo=timezone.utc).isoformat(),
                    source_timestamp=record.source_timestamp.replace(tzinfo=timezone.utc).isoformat() if record.source_timestamp else None,
                    data_current=record.source_timestamp is not None, simulated=False,
                    material=record.material or 'indefinido', event_type=record.kind)
        return data

    @app.post('/api/v1/events', dependencies=[Depends(device_auth)], tags=['Hardware v1'])
    async def ingest_event(payload: HardwareEvent, db=Depends(db_session)):
        if payload.event_id.startswith('academico:') or payload.device_id == ACADEMIC_DEVICE:
            raise HTTPException(422, 'Identificador reservado para o protocolo acadêmico.')
        return await store_event(payload, db)

    async def store_event(payload, db):
        fields = payload.model_dump(mode='json')
        # Keep fingerprints identical for versioned events accepted before these optional fields existed.
        for key in ('rasp_material', 'rasp_acuracia', 'component_status'):
            if fields['data'][key] is None:
                del fields['data'][key]
        digest = hashlib.sha256(json.dumps(fields, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        old = db.get(HardwareRecord,payload.event_id)
        if old:
            if old.digest != digest:
                raise HTTPException(409, 'event_id already used with different content')
            return {'event_id':old.event_id,'duplicate':True}
        now = datetime.now(timezone.utc)
        record = HardwareRecord(event_id=payload.event_id, device_id=payload.device_id,
            object_id=payload.data.object_id if payload.type=='classification' else None,
            kind=payload.type, material=payload.data.material if payload.type=='classification' else None,
            source_timestamp=payload.timestamp, received_at=now,
            payload=payload.data.model_dump(mode='json', exclude_unset=True), digest=digest)
        if db.bind.dialect.name == 'postgresql':
            from sqlalchemy.dialects.postgresql import insert
        else:
            from sqlalchemy.dialects.sqlite import insert
        presence = insert(DevicePresence).values(
            device_id=payload.device_id, role=payload.data.device_role, last_seen=now
        )
        db.add(record)
        try:
            db.execute(presence.on_conflict_do_update(
                index_elements=[DevicePresence.device_id],
                set_={'last_seen': now, 'role': payload.data.device_role},
                where=DevicePresence.last_seen <= now,
            ))
            db.commit()
        except IntegrityError:
            db.rollback()
            old=db.get(HardwareRecord,payload.event_id)
            if old and old.digest==digest:return {'event_id':old.event_id,'duplicate':True}
            raise HTTPException(409,'event_id or object_id already used; do not create a second classification for the same object')
        for ws in list(clients):
            try: await ws.send_json({'type':'hardware_event','event_type':payload.type,'event_id':payload.event_id})
            except Exception: clients.discard(ws)
        return JSONResponse({'event_id':record.event_id,'duplicate':False},status_code=201)

    @app.get('/api/v1/devices', tags=['Hardware v1'])
    def devices(db=Depends(db_session)):
        now = datetime.now(timezone.utc)
        items = [
            {'device_id': d.device_id, 'role': d.role,
             'last_seen': d.last_seen.replace(tzinfo=timezone.utc).isoformat(),
             'online': (now - d.last_seen.replace(tzinfo=timezone.utc)).total_seconds() < (
                 ACADEMIC_EXPIRY_SECONDS if d.device_id == ACADEMIC_DEVICE else 60
             )}
            for d in db.query(DevicePresence).all()
        ]
        status = db.query(HardwareRecord).filter(
            HardwareRecord.device_id == ACADEMIC_DEVICE,
            HardwareRecord.kind == 'heartbeat',
            HardwareRecord.event_id.startswith('academico:heartbeat:'),
        ).order_by(HardwareRecord.source_timestamp.desc().nulls_last(), HardwareRecord.received_at.desc()).first()
        if status:
            for item in items:
                if item['device_id'] == ACADEMIC_DEVICE:
                    item['component_status'] = status.payload.get('component_status') or {}
                    stamp = (status.source_timestamp or status.received_at).replace(tzinfo=timezone.utc)
                    item['component_timestamp'] = stamp.isoformat()
                    item['components_current'] = (now - stamp).total_seconds() < ACADEMIC_EXPIRY_SECONDS
                    break
        return items

    async def accept_versioned(payload, required, request, db):
        device_auth(request.headers.get('X-Device-Key'))
        if payload.type != required:
            raise HTTPException(422, f'This route requires type={required}')
        result = await ingest_event(payload, db)
        return result if isinstance(result, JSONResponse) else JSONResponse(result)

    async def accept_academic(payload, kind, data, db):
        if isinstance(payload, AcademicClassification):
            # Keep the original ID visible while avoiding collisions with existing v1 IDs.
            event_id = 'academico:class:' + payload.event_id
        else:
            fingerprint = hashlib.sha256(payload.model_dump_json().encode()).hexdigest()
            event_id = 'academico:' + kind + ':' + fingerprint
        hardware = HardwareEvent(
            schema_version=1, event_id=event_id, device_id=ACADEMIC_DEVICE,
            timestamp=payload.timestamp, type=kind, data=data,
        )
        result = await store_event(hardware, db)
        if isinstance(payload, AcademicClassification):
            body = {'event_id': payload.event_id, 'duplicate': not isinstance(result, JSONResponse)}
            return JSONResponse(body, status_code=201 if isinstance(result, JSONResponse) else 200)
        return result if isinstance(result, JSONResponse) else JSONResponse(result)

    @app.post('/api/eventos', status_code=201, tags=['Projeto acadêmico'])
    async def event_alias(payload: AcademicClassification | HardwareEvent, request: Request, db=Depends(db_session)):
        if isinstance(payload, HardwareEvent):
            return await accept_versioned(payload, 'classification', request, db)
        red, green, blue = payload.color or (None, None, None)
        data = HardwareData(
            object_id=payload.event_id, material=payload.material,
            metal=None if payload.metal is None else bool(payload.metal),
            infrared=payload.ir, infrared_mode='digital',
            color_r=red, color_g=green, color_b=blue,
            rasp_material=payload.rasp_material, rasp_acuracia=payload.rasp_acuracia,
            confidence=payload.acuracia_final,
        )
        return await accept_academic(payload, 'classification', data, db)

    @app.post('/api/lixeiras', status_code=201, tags=['Projeto acadêmico'])
    async def bin_alias(payload: AcademicBins | HardwareEvent, request: Request, db=Depends(db_session)):
        if isinstance(payload, HardwareEvent):
            return await accept_versioned(payload, 'telemetry', request, db)
        data = HardwareData(organic_bin_distance_cm=payload.organicos_cm,
                            recyclable_bin_distance_cm=payload.reciclaveis_cm)
        return await accept_academic(payload, 'telemetry', data, db)

    @app.post('/api/dispositivos', status_code=201, tags=['Projeto acadêmico'])
    async def device_alias(payload: AcademicStatus | HardwareEvent, request: Request, db=Depends(db_session)):
        if isinstance(payload, HardwareEvent):
            return await accept_versioned(payload, 'heartbeat', request, db)
        data = HardwareData(component_status=payload.model_dump(exclude={'timestamp'}))
        return await accept_academic(payload, 'heartbeat', data, db)

    @app.get('/api/resumo', tags=['Projeto - documento v0.1'])
    def project_summary(db=Depends(db_session)):
        current=overview(db)
        total=current['total']
        return {'total':total,'organicos':current['organic'],'reciclaveis':current['recyclable'],
            'desconhecidos':current['undefined'],
            'percentuais':{'organicos':current['organic']/total*100 if total else None,
                           'reciclaveis':current['recyclable']/total*100 if total else None},
            'ultima_classificacao':current['latest_classification'],'dispositivos':devices(db)}

    @app.get('/api/eventos', tags=['Projeto - documento v0.1'])
    def project_events(limite:int=Query(50,ge=1,le=200), pagina:int=Query(1,ge=1,le=1000000), db=Depends(db_session)):
        offset=(pagina-1)*limite
        # Fetch a bounded offset+page per source and merge in measurement order.
        # Legacy rows remain intact and visible; new counts include classification only.
        ordering=func.coalesce(HardwareRecord.source_timestamp,HardwareRecord.received_at)
        modern=db.query(HardwareRecord).filter(HardwareRecord.kind=='classification')
        modern_total=modern.count()
        legacy=db.query(legacy_reading).filter(legacy_reading.simulated.is_(False))
        legacy_total=legacy.count()
        if legacy_total==0:
            items=[project(r) for r in modern.order_by(ordering.desc(),HardwareRecord.event_id.desc()).offset(offset).limit(limite)]
        elif modern_total==0:
            items=[serialize_legacy(r) for r in legacy.order_by(legacy_reading.timestamp.desc(),legacy_reading.id.desc()).offset(offset).limit(limite)]
        else:
            from sqlalchemy import select, union_all, literal, cast, String as SQLString
            combined=union_all(
                select(literal('hardware').label('source'),HardwareRecord.event_id.label('key'),ordering.label('stamp')).where(HardwareRecord.kind=='classification'),
                select(literal('legacy').label('source'),cast(legacy_reading.id,SQLString).label('key'),legacy_reading.timestamp.label('stamp')).where(legacy_reading.simulated.is_(False))
            ).subquery()
            page=db.execute(select(combined).order_by(combined.c.stamp.desc(),combined.c.source,combined.c.key).offset(offset).limit(limite)).all()
            items=[project(db.get(HardwareRecord,row.key)) if row.source=='hardware' else serialize_legacy(db.get(legacy_reading,int(row.key))) for row in page]
        return {'items':items,'pagina':pagina,'limite':limite,'total':modern_total+legacy_total,'total_paginas':(modern_total+legacy_total+limite-1)//limite}

    @app.get('/api/historico', tags=['Projeto - documento v0.1'])
    def project_history(intervalo:Literal['hora','dia','mes']='hora', db=Depends(db_session)):
        # UTC buckets, returned in ascending order. No hard-coded or simulated series.
        ordering=func.coalesce(HardwareRecord.source_timestamp,HardwareRecord.received_at)
        def bucket(column):
            if db.bind.dialect.name=='postgresql':return func.date_trunc({'hora':'hour','dia':'day','mes':'month'}[intervalo],func.timezone('UTC',column))
            return func.strftime({'hora':'%Y-%m-%dT%H:00:00','dia':'%Y-%m-%dT00:00:00','mes':'%Y-%m-01T00:00:00'}[intervalo],column)
        series={}
        modern_bucket=bucket(ordering)
        legacy_bucket=bucket(legacy_reading.timestamp)
        queries=[db.query(modern_bucket,HardwareRecord.material,func.count()).filter(HardwareRecord.kind=='classification').group_by(modern_bucket,HardwareRecord.material),
            db.query(legacy_bucket,legacy_reading.material,func.count()).filter(legacy_reading.simulated.is_(False)).group_by(legacy_bucket,legacy_reading.material)]
        for query in queries:
            for stamp,material,count in query:
                key=stamp.replace(tzinfo=timezone.utc).isoformat() if isinstance(stamp,datetime) else stamp+'+00:00'
                row=series.setdefault(key,{'timestamp':key,'organicos':0,'reciclaveis':0,'desconhecidos':0})
                row[{'organico':'organicos','reciclavel':'reciclaveis'}.get(material,'desconhecidos')]+=count
        return {'intervalo':intervalo,'timezone':'UTC','items':[series[k] for k in sorted(series)]}

    @app.get('/api/lixeiras', tags=['Projeto - documento v0.1'])
    def project_bins(db=Depends(db_session)):
        from sqlalchemy import or_
        now = datetime.now(timezone.utc)
        rows=[]
        for key,name in [('organic','organicos'),('recyclable','reciclaveis')]:
            keys=[key+'_fill_pct',key+'_weight_g',key+'_bin_distance_cm']
            exists=[func.json_type(HardwareRecord.payload,'$.'+k).isnot(None) if db.bind.dialect.name=='sqlite' else HardwareRecord.payload[k].isnot(None) for k in keys]
            record=db.query(HardwareRecord).filter(HardwareRecord.kind.in_(['telemetry','classification']),or_(*exists)).order_by(HardwareRecord.source_timestamp.desc().nulls_last(),HardwareRecord.received_at.desc()).first()
            latest=project(record) if record else None
            legacy=db.query(legacy_reading).filter(legacy_reading.simulated.is_(False),or_(getattr(legacy_reading,keys[0]).isnot(None),getattr(legacy_reading,keys[1]).isnot(None))).order_by(legacy_reading.timestamp.desc()).first()
            if legacy:
                serialized=serialize_legacy(legacy)
                if not latest or serialized['timestamp']>latest['timestamp']:latest=serialized
            stamp=datetime.fromisoformat(latest['timestamp']) if latest else None
            max_age = ACADEMIC_EXPIRY_SECONDS if latest and latest['device_id'] == ACADEMIC_DEVICE else 60
            fresh=bool(stamp and latest.get('data_current',True) and (now-stamp).total_seconds()<max_age)
            fill=latest.get(keys[0]) if fresh else None
            rows.append({'codigo':name,'ocupacao_pct':fill,'peso_gramas':latest.get(keys[1]) if fresh else None,
                'distancia_cm':latest.get(keys[2]) if fresh else None,'timestamp':latest['timestamp'] if latest else None,
                'estado':'sem_dados_recentes' if not fresh else 'indisponivel' if fill is None else 'cheia' if fill>=90 else 'quase_cheia' if fill>=80 else 'normal'})
        return {'items':rows}

    @app.get('/api/dispositivos', tags=['Projeto - documento v0.1'])
    def project_devices(db=Depends(db_session)):
        return {'items':devices(db)}

    def overview_extra(db):
        counts=dict(db.query(HardwareRecord.material,func.count(HardwareRecord.event_id)).filter(HardwareRecord.kind=='classification').group_by(HardwareRecord.material).all())
        latest=db.query(HardwareRecord).filter(HardwareRecord.kind.in_(['telemetry','classification']),
                                                ~HardwareRecord.event_id.startswith('academico:telemetry:')).order_by(HardwareRecord.source_timestamp.desc().nulls_last(),desc(HardwareRecord.received_at)).first()
        last_class=db.query(HardwareRecord).filter(HardwareRecord.kind=='classification').order_by(HardwareRecord.source_timestamp.desc().nulls_last(),desc(HardwareRecord.received_at)).first()
        return counts, project(latest) if latest else None, project(last_class) if last_class else None

    def classification_history(db,limit):
        return [project(r) for r in db.query(HardwareRecord).filter(HardwareRecord.kind=='classification').order_by(HardwareRecord.source_timestamp.desc().nulls_last(),desc(HardwareRecord.received_at)).limit(limit)]
    return overview_extra, classification_history
