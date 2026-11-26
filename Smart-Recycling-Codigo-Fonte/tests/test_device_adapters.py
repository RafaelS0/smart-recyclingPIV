import hashlib,json,sys,tempfile,unittest,urllib.error
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'firmware/raspberry_pi'))
from protocol import LineFramer,encode_bridge,decode_bridge
from outbox import Outbox
from model import WasteModel
class FakeInterpreter:
    def __init__(self,scores=None,dtype=np.float32):self.scores=np.array(scores or [.1,.9],dtype=np.float32);self.dtype=dtype
    def allocate_tensors(self):pass
    def get_input_details(self):return [{'index':0,'shape':np.array([1,60,30,3]),'dtype':self.dtype,'quantization':(1,-128)}]
    def get_output_details(self):return [{'index':1,'shape':np.array([1,2]),'dtype':np.float32,'quantization':(0,0)}]
    def set_tensor(self,index,value):self.value=value
    def invoke(self):pass
    def get_tensor(self,index):return self.scores[np.newaxis]
class DeviceTests(unittest.TestCase):
    def test_frames(self):
        event={'type':'telemetry','data':{'metal':None}};frame=encode_bridge(event);framer=LineFramer()
        self.assertEqual(framer.feed(frame[:12]),[])
        self.assertEqual(decode_bridge(framer.feed(frame[12:])[0]),event)
        damaged=frame.replace(b'telemetry',b'telemetrx')
        with self.assertRaises(ValueError):decode_bridge(damaged)
        self.assertEqual(LineFramer(3).feed(b'overflow\nOK\n'),[b'OK'])
    def test_durable_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'outbox.db';box=Outbox(path);body={'event_id':'fixed-id','type':'heartbeat'};box.enqueue(body)
            def fail(*args,**kwargs):raise urllib.error.URLError('offline')
            self.assertEqual(box.deliver_one('https://invalid.local','secret',fail),0);box.close();box=Outbox(path)
            self.assertEqual(json.loads(box.db.execute('SELECT body FROM outbox').fetchone()[0]),body)
            box.db.execute('UPDATE outbox SET next_try=0');box.db.commit();sent=[]
            class Response:
                status=200
                def __enter__(self):return self
                def __exit__(self,*args):pass
            def transport(request,**kwargs):sent.append(json.loads(request.data));return Response()
            self.assertEqual(box.deliver_one('https://invalid.local','secret',transport),200);self.assertEqual(sent,[body]);self.assertEqual(box.db.execute('SELECT COUNT(*) FROM outbox').fetchone()[0],0);box.close()
    def test_model_preprocessing(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder);model=folder/'fixture.tflite';model.write_bytes(b'fake-interpreter-test-only')
            manifest={'model_version':'fixture','sha256':hashlib.sha256(model.read_bytes()).hexdigest(),'class_names':['organico','reciclavel'],'color_order':'RGB','height':60,'width':30,'input_scale':1.0,'input_offset':0.0}
            meta=folder/'manifest.json';meta.write_text(json.dumps(manifest));interpreter=FakeInterpreter();adapter=WasteModel(model,meta,interpreter=interpreter)
            result=adapter.predict_rgb(np.full((100,100,3),255,dtype=np.uint8));self.assertEqual(result['material'],'reciclavel');self.assertEqual(interpreter.value.shape,(1,60,30,3));self.assertEqual(float(interpreter.value.max()),255)
            uncertain=WasteModel(model,meta,threshold=.95,interpreter=FakeInterpreter()).predict_rgb(np.zeros((60,30,3),dtype=np.uint8));self.assertEqual(uncertain['material'],'indefinido')
            quant=FakeInterpreter(dtype=np.int8);WasteModel(model,meta,interpreter=quant).predict_rgb(np.full((60,30,3),255,dtype=np.uint8));self.assertEqual(int(quant.value.max()),127)
            with self.assertRaises(ValueError):WasteModel(model,meta,interpreter=FakeInterpreter([float('nan'),0])).predict_rgb(np.zeros((60,30,3),dtype=np.uint8))
            model.write_bytes(b'tampered')
            with self.assertRaises(ValueError):WasteModel(model,meta,interpreter=interpreter)
if __name__=='__main__':unittest.main()
