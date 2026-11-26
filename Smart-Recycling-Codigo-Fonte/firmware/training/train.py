"""Modern training adaptation of techSash/Waste-classification (Apache-2.0).
Retains six conv layers, two dense layers, O/R class order and raw 60x30 RGB input.
"""
import argparse,json
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--dataset',required=True,help='Root containing TRAIN/O, TRAIN/R, TEST/O, TEST/R');parser.add_argument('--output',required=True);parser.add_argument('--epochs',type=int,default=50);parser.add_argument('--batch-size',type=int,default=32);args=parser.parse_args()
    if args.epochs<1 or args.batch_size<1:parser.error('epochs and batch-size must be positive')
    dataset=Path(args.dataset);out=Path(args.output)
    for split in ['TRAIN','TEST']:
        for category in ['O','R']:
            if not (dataset/split/category).is_dir():parser.error(f'Missing {split}/{category}')
    if out.exists():parser.error('Output already exists; choose a new directory to preserve weights')
    import tensorflow as tf
    from export import export_model
    tf.keras.utils.set_random_seed(42);out.mkdir(parents=True)
    common=dict(image_size=(60,30),interpolation='nearest',batch_size=args.batch_size,class_names=['O','R'],seed=42,label_mode='categorical')
    train=tf.keras.utils.image_dataset_from_directory(dataset/'TRAIN',validation_split=.2,subset='training',**common)
    validation=tf.keras.utils.image_dataset_from_directory(dataset/'TRAIN',validation_split=.2,subset='validation',**common)
    test=tf.keras.utils.image_dataset_from_directory(dataset/'TEST',shuffle=False,**common)
    layers=tf.keras.layers
    model=tf.keras.Sequential([layers.Input((60,30,3)),layers.RandomRotation(.125,fill_mode='nearest'),layers.RandomTranslation(.2,.2,fill_mode='nearest'),layers.RandomFlip('horizontal'),layers.Conv2D(32,3,padding='same',activation='relu'),layers.Conv2D(32,3,activation='relu'),layers.Conv2D(32,3,activation='relu'),layers.MaxPooling2D(2),layers.Dropout(.25),layers.Conv2D(64,3,activation='relu'),layers.Conv2D(64,3,activation='relu'),layers.Conv2D(64,3,activation='relu'),layers.Dropout(.25),layers.Flatten(),layers.Dense(512,activation='relu'),layers.Dropout(.5),layers.Dense(512,activation='relu'),layers.Dropout(.5),layers.Dense(2,activation='softmax')])
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4),loss='categorical_crossentropy',metrics=['accuracy'])
    callbacks=[tf.keras.callbacks.ModelCheckpoint(str(out/'best.keras'),save_best_only=True,monitor='val_loss'),tf.keras.callbacks.EarlyStopping(patience=10,restore_best_weights=True,monitor='val_loss')]
    history=model.fit(train,validation_data=validation,epochs=args.epochs,callbacks=callbacks)
    model=tf.keras.models.load_model(out/'best.keras',compile=False)
    # Exclude random augmentation from exported inference graph; weights are unchanged.
    inference=tf.keras.Sequential([layers.Input((60,30,3))]+[layer for layer in model.layers if not layer.name.startswith('random_')])
    inference.compile(loss='categorical_crossentropy',metrics=['accuracy'])
    metrics=inference.evaluate(test,return_dict=True)
    count=sum(1 for file in (dataset/'TEST').rglob('*') if file.suffix.lower() in {'.jpg','.jpeg','.png','.bmp','.gif'})
    (out/'evaluation.json').write_text(json.dumps({'held_out_test':metrics,'test_images_on_disk':count,'class_order':['O','R'],'training_history':history.history,'note':'Dataset accuracy is not physical conveyor accuracy.'},indent=2))
    export_model(inference,out/'export',1.0,0.0)
    print('Saved trained weights, held-out evaluation, TFLite and preprocessing manifest:',out)
if __name__=='__main__':main()
