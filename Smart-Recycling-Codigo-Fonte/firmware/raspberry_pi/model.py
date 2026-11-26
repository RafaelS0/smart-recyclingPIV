"""TFLite adapter for the upstream 60x30 RGB classifier; no generated predictions."""
import hashlib
import json
import time
from pathlib import Path
import numpy as np

class WasteModel:
    def __init__(self,model_path,manifest_path,threshold=.75,interpreter=None):
        self.manifest=json.loads(Path(manifest_path).read_text())
        if not 0<=threshold<=1:raise ValueError('Confidence threshold must be between 0 and 1')
        self.threshold=threshold
        self.version=self.manifest['model_version']
        if self.manifest.get('class_names')!=['organico','reciclavel']:
            raise ValueError('Unexpected class order: expected O=organico, R=reciclavel')
        if self.manifest.get('color_order')!='RGB':raise ValueError('RGB preprocessing must be explicit')
        if hashlib.sha256(Path(model_path).read_bytes()).hexdigest()!=self.manifest['sha256']:
            raise ValueError('Model SHA256 does not match manifest')
        if interpreter is None:
            try:from ai_edge_litert.interpreter import Interpreter
            except ImportError:
                try:from tflite_runtime.interpreter import Interpreter
                except ImportError:from tensorflow.lite import Interpreter
            interpreter=Interpreter(model_path=str(model_path),num_threads=2)
        self.interpreter=interpreter;interpreter.allocate_tensors()
        self.input=interpreter.get_input_details()[0];self.output=interpreter.get_output_details()[0]
        self.height=int(self.manifest['height']);self.width=int(self.manifest['width'])
        if list(self.input['shape'])!=[1,self.height,self.width,3] or list(self.output['shape'])!=[1,2]:raise ValueError('Invalid model input/output shape')

    def predict_rgb(self,rgb):
        from PIL import Image
        if rgb.ndim!=3 or rgb.shape[2]!=3:raise ValueError('Expected RGB camera image')
        rgb=np.asarray(Image.fromarray(rgb.astype(np.uint8)).resize((self.width,self.height),Image.Resampling.NEAREST),dtype=np.float32)
        value=rgb*float(self.manifest['input_scale'])+float(self.manifest['input_offset'])
        dtype=self.input['dtype']
        if np.issubdtype(dtype,np.integer):
            scale,zero=self.input['quantization']
            if scale<=0:raise ValueError('Missing input quantization scale')
            info=np.iinfo(dtype);value=np.clip(np.rint(value/scale+zero),info.min,info.max)
        self.interpreter.set_tensor(self.input['index'],value[np.newaxis].astype(dtype))
        start=time.perf_counter();self.interpreter.invoke();elapsed=(time.perf_counter()-start)*1000
        scores=self.interpreter.get_tensor(self.output['index'])[0].astype(np.float32)
        if np.issubdtype(self.output['dtype'],np.integer):
            scale,zero=self.output['quantization'];scores=(scores-zero)*scale
        if not np.isfinite(scores).all() or np.any(scores<0) or np.any(scores>1.01) or abs(float(scores.sum())-1)>.05:raise ValueError('Model output must be softmax probabilities')
        index=int(np.argmax(scores));confidence=float(np.clip(scores[index],0,1))
        return {'material':self.manifest['class_names'][index] if confidence>=self.threshold else 'indefinido','confidence':confidence,'model_version':self.version,'inference_ms':elapsed}
