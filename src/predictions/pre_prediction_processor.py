import logging
import os

import ants
import hli_python3_utils
import matplotlib.mlab as mlab
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pydicom as dcm
from scipy.ndimage import zoom

logging_utils = hli_python3_utils.client("LoggingUtils")

class Nifit2DicomArray:
    """
    itk-snap processed array shape is (length, width, slice_number), dicom array shape is (slice_number, width, length), data shape transfrom
    """

    def horizontal_mirror(self, imgs: np.array):
        """
        The horizontal mirror image is inverted after 180 degrees of counterclockwise rotation
        水平镜像是将原始数据逆时针旋转180度，并进行逆转置
        """
        return np.rot90(imgs, 2)[::-1]

    def __call__(self, imgs_arr: np.array, rot_number=1):
        imgs = self.horizontal_mirror(imgs_arr)
        imgs = np.rot90(imgs, rot_number)
        transform_dicom_array = np.zeros((556, 260, 320))
        for i, j in zip(range(imgs.shape[-1]), range(imgs.shape[-1]-1, 0-1, -1)):
            transform_dicom_array[i, :, :] = imgs[:, :, j]
        return transform_dicom_array

class PrePredictionProcessor:
    def __init__(self, logging_dir):
        """
        Initializes the pre-prediction processor.
        :param logging_dir: The logging directory
        """
        # normalize_0_1 configs
        self.normalize_lg = 65535.0
        self.normalize_sm = 4095.0
        # n4_bias_correction configs
        self.spline_param = 100
        self.logger = logging_utils.get_logger(os.path.join(logging_dir, "pre_prediction_processor.log"))


    def resize_to_256_128_128(self, img: np.array, resize_shape: tuple = (256, 128, 128)):
        """
        Resizes an image to 256.
        :param img: An input image
        """
        self.logger.debug(f'origin image shape: {img.shape}, {resize_shape}')
        resize_ratio = []
        for i, s in enumerate(img.shape):
            resize_ratio.append(resize_shape[i] / s)
        img = zoom(img, resize_ratio)
        return img
    
    def resize_images(self, img: np.array, resize_ratio=None):
        if resize_ratio is None:
            resize_ratio = [0.5] * len(img.shape)
        self.logger.debug(f"resize ratio: {resize_ratio}")
        img = zoom(img, resize_ratio, order=0, mode='nearest')
        return img

    def normalize_0_1(self, img: np.array, bit: int = 11):
        """
        Normalizes an image based on bit.
        :param img: An input image
        :param bit: A bit
        """
        if bit == 15:
            return (img - img.min()) / (self.normalize_lg - img.min())
        elif bit == 11:
            return (img - img.min()) / (self.normalize_sm - img.min())
        else:
            return (img - img.min()) / (img.max() - img.min())

    def n4_bias_correction(self, img: np.array):
        """
        Peforms n4 bias correction for an image.
        :param img: An input image
        """
        ants_img = ants.from_numpy(img.astype(np.float64))
        result = ants.n4_bias_field_correction(
            ants_img,
            spline_param=self.spline_param
        )
        return result.numpy()

    def n4_bias_correction_every_slice(self, img: np.array):
        ants_img = ants.from_numpy(img.astype(np.float64))
        for i in range(img.shape[-1]):
            ants_img[:, :, i] = ants.n4_bias_field_correction(ants_img, spline_param=self.spline_param).numpy
        return ants_img

    def denoise(self, img: np.array):
        """
        Denoises an image.
        :param img: An input image
        """
        ants_img = ants.from_numpy(img.astype(np.float64))
        result = ants.denoise_image(ants_img)
        return result.numpy()

    @classmethod
    def load_dicom_series(cls, path):
        imgs = None
        if os.path.isdir(path) and len(os.listdir(path)) > 1 and os.listdir(path)[1].endswith('.dcm'):
            imgs = [dcm.read_file(os.path.join(path, file)) for file in os.listdir(path) if file.endswith('.dcm')]
            print(f"=================== dicom series number: {len(imgs)} ======================")
        else:
            print("=================== dicom file format error =======================")
        return imgs

    @classmethod
    def load_nii_image(cls, path):
        """
        Loads the dicom objects into a list.
        :param dicom_path: Path to a local directory containing dicom images
        """
        imgs = nib.load(path).get_data().astype(np.float32)
        return imgs

    def horizontal_mirror(self, imgs: np.array):
        """
        The horizontal mirror image is inverted after 180 degrees of counterclockwise rotation
        水平镜像是将原始数据逆时针旋转180度，并进行逆转置
        """
        return np.rot90(imgs, 2)[::-1]

    def process(self, data_path, slice_interval, resize_shape=None, rot_number=1):
        # imgs = self.horizontal_mirror(imgs)
        # imgs = np.rot90(imgs, rot_number)
        imgs = PrePredictionProcessor.load_nii_image(data_path)
        self.logger.info(f"origin images shape is {imgs.shape}")
        origin_imgs = Nifit2DicomArray()(imgs)
        self.logger.info(f'rotate and horizontal mirror after image shape: {origin_imgs.shape}')
        imgs_denoise = self.denoise(origin_imgs)
        imgs_n4_bais = self.n4_bias_correction(imgs_denoise)
        imgs_normal = self.normalize_0_1(imgs_n4_bais)
        self.logger.info(f'processed imgs shape: {imgs_normal.shape}')
        
        slice_imgs = imgs_normal[slice_interval[0] - 1:slice_interval[1]-1]
        
        if resize_shape is None:
            resize_ratio = [0.5] * len(slice_imgs.shape)
        else:
            resize_ratio = [j / i for i, j in zip(slice_imgs.shape, resize_shape)]
        self.logger.info(
            f"slice shape: {slice_imgs.shape}, resize shape: {resize_shape} resize ratio: {resize_ratio}")
        
        imgs_resize = self.resize_images(img=slice_imgs, resize_ratio=resize_ratio)
        self.logger.info(f"processed complete array shape: {imgs_resize.shape}")
        return imgs_resize, imgs_normal, imgs

    def execute(self, dicom_path, slice_interval, slice_or_resize="slice", resize_shape=None, rot_number=3):
        """
        The flow control for the pre-process prediction module.
        read dicom file after, sort by SliceLocation,
        because dicom SliceLocation is from foot to head, so reverse must be True
        :param dicom_path: Path local dicom images.
        """
        self.logger.info("Started Pre-Processing")
        imgs = PrePredictionProcessor.load_dicom_series(dicom_path)
        imgs.sort(key=lambda x: int(x.SliceLocation), reverse=True)
        self.logger.info("Loaded Dicoms, beginning processing on {0} dicoms".format(len(imgs)))
        bit = imgs[0].HighBit
        # todo: Crop image size through slice interval, slice interval is location number,
        # The minimum and maximum values in the interval should be 1 greater than the index value
        imgs_array = np.array([img.pixel_array.astype(np.float32) for img in imgs])
        imgs_denoise = self.denoise(imgs_array)
        imgs_n4_bais = self.n4_bias_correction(imgs_denoise)
        imgs_normal = self.normalize_0_1(imgs_n4_bais, bit)
        self.logger.info(f'processed imgs shape: {imgs_normal.shape}')
        
        if slice_or_resize=='slice':
            self.logger.info(f'Ways to reduce data size is {slice_or_resize}')
            imgs_resize = imgs_normal[slice_interval[0]:slice_interval[1], 2:-2, :]
        else:
            self.logger.info(f'Ways to reduce data size is {slice_or_resize}')
            slice_imgs = imgs_normal[slice_interval[0]:slice_interval[1]]
            self.logger.info(f'slice_imgs shape: {slice_imgs.shape}')
            if resize_shape is None:
                resize_ratio = [0.5] * len(slice_imgs.shape)
            else:
                resize_ratio = [j / i for i, j in zip(slice_imgs.shape, resize_shape)]
            self.logger.info(
                f"slice interval: {slice_interval}, slice imgs shape: {slice_imgs.shape}, resize shape: {resize_shape}, resize ratio: {resize_ratio}")
            imgs_resize = self.resize_images(img=slice_imgs, resize_ratio=resize_ratio)
        self.logger.info(f"Pre-Processing Complete， array shape: {imgs_resize.shape}")
        return imgs_resize, imgs_normal, imgs

