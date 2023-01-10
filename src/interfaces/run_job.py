import logging
import os

import hli_python3_utils
import numpy as np
from predictions.post_prediction_processor import PostPredictionProcessor
from predictions.pre_prediction_processor import PrePredictionProcessor
from predictions.predictor_torch import Predictor

file_utils = hli_python3_utils.client("FileUtils")
logging_utils = hli_python3_utils.client("LoggingUtils")


class RunJobInterface:
    def __init__(self, logging_dir, modality, num_classes, model_file, range_file, local_images_dir, sample_id, output_filename,
                 colors, resize_shape, model_version='torch'):
        """
        Initializes the run job interface.
        :param logging_dir: The logging directory
        :param modality: MUSCLE or FAT
        :param model_file: The local model file
        :param range_file: The local range file
        :param local_images_dir: The local images directory
        :param sample_id: The patient identifier
        :param output_filename: The output json file prefix
        :param colors: Dictionary of colors for each modality
        """
        self.model_version = model_version
        self.pre_processor = PrePredictionProcessor(logging_dir)
        self.post_processor = PostPredictionProcessor(logging_dir, modality, range_file, local_images_dir, colors)
        self.predictor = Predictor(logging_dir, resize_shape, num_classes, model_file)
        self.sample_id = sample_id
        self.output_filename = output_filename
        self.logger = logging_utils.get_logger(os.path.join(logging_dir, "run_job.log"))

    def execute(self,
                dicom_path,
                slice_interval,
                resize_shape,
                slice_or_resize='slice',
                horizontal_mirror_sign=False,
                rot_number=3
                ):
        """
        Main flow control for the run job interface.
        :param dicom_paths: The path to the original input dicom images.
        """
        self.logger.info("Beginning Job Run, preprocessing")
        pre_processed_imgs, origin_imgs_array, dcm_objs = self.pre_processor.execute(
            dicom_path=dicom_path,
            slice_interval=slice_interval,
            resize_shape=resize_shape,
            slice_or_resize=slice_or_resize
        )
        
        if self.model_version == 'keras':
            pre_processed_imgs = np.expand_dims(np.expand_dims(pre_processed_imgs, 0), -1)
        elif self.model_version == 'torch':
            pre_processed_imgs = np.expand_dims(np.expand_dims(pre_processed_imgs, 0), 0)
        self.logger.info(f"Preprocessing complete, "
                         f"pre_processed_imgs: {pre_processed_imgs.shape}, "
                         f"origin_imgs_array: {origin_imgs_array.shape}, "
                         f"dcm_objs: {len(dcm_objs)}, "
                         f"starting prediction")

        predicted_imgs = self.predictor.predict(pre_processed_imgs)


        self.logger.info("Prediction complete, beginning post processing")
        self.post_processor.execute(predicted_imgs, origin_imgs_array, dcm_objs, slice_interval, dicom_path, self.sample_id, self.output_filename, slice_or_resize=slice_or_resize)

        self.logger.info("Post Processing Complete...")
