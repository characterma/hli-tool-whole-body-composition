import logging
import hli_python3_utils
import os
from predictions.pre_prediction_processor import PrePredictionProcessor

import torch
import torch.nn.functional as F

from model.vnet3d import VNet_Parallelism

file_utils = hli_python3_utils.client("FileUtils")
logging_utils = hli_python3_utils.client("LoggingUtils")


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
        self.model = VNet_Parallelism(in_channels=1, classes=num_classes)
        self.logger.info(f'model_file_path: {model_file_path}')
        self.model.load_state_dict(torch.load(model_file_path))
        self.logger.info(f'model load success')
        self.model.eval()


    # We'll need to tune how large the predict on batch can be...the more you can fit in memory the faster it will go.
    def predict(self, processed_images):
        '''The main call to the model for the predictions.
        
        :param processed_images: The pre-processed images
        '''
        self.logger.info(f"precessed images shape is : {processed_images.shape}")
        with torch.no_grad():
            predictions = self.model(torch.from_numpy(processed_images))
            predictions_prob = F.softmax(predictions, dim=1)
        self.logger.info(f"predictions shape: {predictions_prob.shape}")
        return predictions_prob.numpy()
