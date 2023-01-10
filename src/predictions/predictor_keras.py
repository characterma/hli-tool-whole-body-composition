import tensorflow as tf
from tensorflow.keras import backend as K
from tensorflow.python.keras.models import load_model
import logging
import hli_python3_utils
import os
from predictions.pre_prediction_processor import PrePredictionProcessor
from model.unet3d import get_model, UNet3D

file_utils = hli_python3_utils.client("FileUtils")
logging_utils = hli_python3_utils.client("LoggingUtils")


num_cores = 4
num_CPU = 1
num_GPU = 0
config = tf.compat.v1.ConfigProto(intra_op_parallelism_threads=num_cores,\
        inter_op_parallelism_threads=num_cores, allow_soft_placement=True,\
        device_count = {'CPU' : num_CPU, 'GPU' : num_GPU})
session = tf.compat.v1.Session(config=config)
tf.compat.v1.keras.backend.set_session(session)



class Predictor:
    '''
    Performs the actual prediction on the the pre-processed images. Loads the model definition file and runs
    predict on batch.
    '''
    def __init__(self, logging_dir, input_shape, num_classes, model_file_path):
        '''Initializes the predictor.
        
        :param logging_dir: The logging directory
        :param model_file_path: The path to the local model file
        '''
        self.logger = logging_utils.get_logger(os.path.join(logging_dir, "predictor.log"))
        # self.model = UNet3D(num_classes=int(num_classes))
        # self.model.build(input_shape =(None,*input_shape, 1))
        with tf.device('/cpu:0'):
            self.model = get_model(input_shape + [1], num_classes)
            # self.model.summary()            
            self.logger.info(f'model_file_path: {model_file_path}')
            if os.path.exists(model_file_path):
                self.logger.info(f"weight file path is exists: {model_file_path}， input_shape： {input_shape}")
                self.model.load_weights(model_file_path)

    # We'll need to tune how large the predict on batch can be...the more you can fit in memory the faster it will go.
    def predict(self, processed_images):
        '''The main call to the model for the predictions.
        
        :param processed_images: The pre-processed images
        '''
        with tf.device('/cpu:0'):
            predictions = self.model.predict(processed_images, batch_size=1, verbose=1)
            return predictions

