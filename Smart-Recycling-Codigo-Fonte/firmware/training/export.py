"""Export real trained weights. No pretrained weights are included upstream."""
import argparse,hashlib,json
from pathlib import Path

def export_model(model,output,input_scale=1.0,input_offset=0.0,version=None):
    import tensorflow as tf
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    if tuple(model.input_shape[1:])!=(60,30,3) or model.output_shape[-1]!=2:raise ValueError('Expected 60x30 RGB input and 2 classes')
    saved=output/'saved_model'
    if saved.exists():raise FileExistsError('Use a fresh output directory; existing SavedModel will not be overwritten')
    # Explicit SavedModel signature avoids dependence on legacy Keras optimizer serialization.
    signature=tf.function(lambda images:model(images,training=False),input_signature=[tf.TensorSpec([1,60,30,3],tf.float32,name='images')])
    tf.saved_model.save(model,str(saved),signatures={'serving_default':signature})
    converter=tf.lite.TFLiteConverter.from_saved_model(str(saved));converter.optimizations=[tf.lite.Optimize.DEFAULT]
    binary=converter.convert();(output/'waste.tflite').write_bytes(binary);digest=hashlib.sha256(binary).hexdigest()
    manifest={'schema_version':1,'model_version':version or 'waste-'+digest[:12],'sha256':digest,'width':30,'height':60,'color_order':'RGB','resize':'nearest','input_scale':input_scale,'input_offset':input_offset,'class_names':['organico','reciclavel'],'upstream':'https://github.com/techSash/Waste-classification','note':'Confidence is a model probability, not validated deployment accuracy.'}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2))
    return manifest

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--model',required=True);parser.add_argument('--output',required=True);parser.add_argument('--input-scale',required=True,type=float,help='1.0 for upstream raw 0..255 training; match your actual training');parser.add_argument('--input-offset',type=float,default=0);parser.add_argument('--version');args=parser.parse_args()
    import tensorflow as tf
    model=tf.keras.models.load_model(args.model,compile=False);print(json.dumps(export_model(model,args.output,args.input_scale,args.input_offset,args.version),indent=2))
if __name__=='__main__':main()
