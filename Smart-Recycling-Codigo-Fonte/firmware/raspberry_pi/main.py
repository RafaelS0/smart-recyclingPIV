"""Camera -> TFLite -> Mega Serial2. AI never controls motors or counts objects alone."""
import json,logging,os,signal,threading,time,uuid
from pathlib import Path
from protocol import LineFramer
from model import WasteModel
from outbox import Outbox,heartbeat
logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
stop=threading.Event()
def main():
    import cv2,serial
    url=os.getenv('API_URL','https://mrvbot.com/smart_recycling/api/v1/events')
    if not url.startswith('https://'):raise ValueError('HTTPS is required')
    key=os.environ['DEVICE_KEY'];device=os.getenv('DEVICE_ID','smart-recycling-pi-01')
    model_path=Path(os.getenv('MODEL_PATH','models/waste.tflite'));manifest_path=Path(os.getenv('MANIFEST_PATH','models/manifest.json'))
    outbox=Outbox(os.getenv('OUTBOX_PATH','outbox.sqlite3'));faults=[];model=None
    try:model=WasteModel(model_path,manifest_path,float(os.getenv('MIN_CONFIDENCE','.75')))
    except Exception as error:logging.error('Model unavailable: %s',error);faults.append('model_unavailable')
    def upload():
        last_heartbeat=0
        while not stop.is_set():
            if time.monotonic()-last_heartbeat>30:
                try:outbox.enqueue(heartbeat(device,list(faults)))
                except Exception as error:logging.error('Outbox: %s',error)
                last_heartbeat=time.monotonic()
            status=outbox.deliver_one(url,key)
            if status and status not in (200,201):logging.warning('Heartbeat delivery HTTP %s; credentials omitted',status)
            stop.wait(.5)
    thread=threading.Thread(target=upload,daemon=True);thread.start()
    camera=None;port=None;cache={};framer=LineFramer(1024)
    try:
        while not stop.is_set():
            try:
                if port is None:port=serial.Serial(os.getenv('SERIAL_PORT','/dev/ttyUSB0'),115200,timeout=.2,write_timeout=1);framer=LineFramer(1024)
                for line in framer.feed(port.read(1024)):
                    try:request=json.loads(line)
                    except (ValueError,UnicodeError):logging.warning('Malformed serial frame ignored');continue
                    if not isinstance(request,dict):continue
                    if request.get('type')=='ping':
                        port.write(b'{"type":"pong"}\n')
                        continue
                    if request.get('type')=='hello':
                        cache.clear();port.write((json.dumps({'type':'session','session_id':uuid.uuid4().hex[:16]})+'\n').encode());continue
                    obj=request.get('object_id')
                    if request.get('type')!='infer' or not isinstance(obj,str) or not 1<=len(obj)<=100:continue
                    if obj in cache:
                        port.write(cache[obj]);continue
                    response={'type':'ai_result','object_id':obj,'ok':False}
                    try:
                        if model is None:raise RuntimeError('Model not loaded; install a trained model and restart')
                        if camera is None:camera=cv2.VideoCapture(int(os.getenv('CAMERA_INDEX','0')));camera.set(cv2.CAP_PROP_BUFFERSIZE,1)
                        if not camera.isOpened():raise RuntimeError('Camera unavailable')
                        # Drain buffered frames, then capture for this object request.
                        for _ in range(2):camera.grab()
                        ok,bgr=camera.read()
                        if not ok:raise RuntimeError('Camera capture failed')
                        ai=model.predict_rgb(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB));response.update(ok=True,ai=ai)
                        if 'camera_failure' in faults:faults.remove('camera_failure')
                    except Exception as error:
                        logging.error('Inference failed for %s: %s',obj,error)
                        if 'camera_failure' not in faults and model is not None:faults.append('camera_failure')
                        if camera is not None:camera.release();camera=None
                    encoded=(json.dumps(response,separators=(',',':'),allow_nan=False)+'\n').encode()
                    port.write(encoded);cache[obj]=encoded
                    if len(cache)>256:cache.pop(next(iter(cache)))
            except (serial.SerialException,OSError) as error:
                logging.error('Serial disconnected: %s',error)
                if port is not None:port.close();port=None
                stop.wait(3)
    finally:
        stop.set();thread.join(timeout=20)
        if camera is not None:camera.release()
        if port is not None:port.close()
        outbox.close()
if __name__=='__main__':
    signal.signal(signal.SIGTERM,lambda *_:stop.set());signal.signal(signal.SIGINT,lambda *_:stop.set());main()
