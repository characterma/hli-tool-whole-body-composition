import pytest
import os, sys
from predictions.pre_prediction_processor import PrePredictionProcessor
import numpy as np
import mock
logging_dir = './tests/integration_tests/logging_dir'


class FakeDCMObject():
    def __init__(self, location=1):
        self.PixelSpacing = [1, 1]
        self.SliceThickness = 1
        self.HighBit = 15
        self.Rows = 176
        self.Columns = 180
        self.pixel_array = np.random.random_integers(0, 65535, size=(176, 180))
        self.SliceLocation = location


def test_normalize():
    '''
    tests the normalize between 0-1 function, for both 11 bit and 15 bit high
    '''
    preprocessor = PrePredictionProcessor(logging_dir)
    # test for 15 bit max numbers
    fake_matrix_15 = np.random.random_integers(0, 65535)
    fake_matrix_11 = np.random.random_integers(0, 4095)
    result15 = preprocessor.normalize_0_1(fake_matrix_15, 15)
    result11 = preprocessor.normalize_0_1(fake_matrix_11, 11)

    assert result15.min() >= 0
    assert result15.max() <= 1

    assert result11.min() >= 0
    assert result15.max() <= 1


def test_resize_images():
    '''
    Tests to ensure resize method actually resizes to the correct dimensions of 256x256
    '''
    preprocessor = PrePredictionProcessor(logging_dir)
    fake_img = np.random.random_integers(0, 1, size=(180, 176))
    resize_ratio = [256/180, 256/176]
    resized = preprocessor.resize_images(fake_img, resize_ratio)
    assert resized.shape[0] == 256
    assert resized.shape[1] == 256


@mock.patch('predictions.pre_prediction_processor.PrePredictionProcessor.load_dicom_series')
@mock.patch('predictions.pre_prediction_processor.PrePredictionProcessor.denoise')
@mock.patch('predictions.pre_prediction_processor.PrePredictionProcessor.n4_bias_correction')
@mock.patch('predictions.pre_prediction_processor.PrePredictionProcessor.resize_images')
@mock.patch('predictions.pre_prediction_processor.PrePredictionProcessor.normalize_0_1')
def test_execute_correct_iterations(mock_normalize, mock_resize, mock_n4, mock_denoise, mock_dicoms):
    '''
    Tests to ensure processing functions are called on a group of images, one at a time, in this test scenario
    there are two dicoms...generally there are about 556ish...
    '''
    dcms = [FakeDCMObject(), FakeDCMObject()]
    mock_dicoms.return_value = dcms
    preprocessor = PrePredictionProcessor(logging_dir)
    processed, _, results = preprocessor.execute(mock_dicoms, slice_interval=[120, 240],
            resize_shape=[240, 256, 320],
            slice_or_resize="resize")
    assert mock_denoise.call_count == 1
    assert mock_n4.call_count == 1
    assert mock_resize.call_count == 1
    assert mock_normalize.call_count == 1
    # Setting slice position to test out the sorting mechanism, sorts in descending order...


@mock.patch('predictions.pre_prediction_processor.PrePredictionProcessor.load_dicom_series')
@mock.patch('predictions.pre_prediction_processor.PrePredictionProcessor.denoise')
@mock.patch('predictions.pre_prediction_processor.PrePredictionProcessor.n4_bias_correction')
@mock.patch('predictions.pre_prediction_processor.PrePredictionProcessor.resize_images')
@mock.patch('predictions.pre_prediction_processor.PrePredictionProcessor.normalize_0_1')
def test_execute_dicom_sorting(mock_normalize, mock_resize, mock_n4, mock_denoise, mock_dicoms):
    dcms = [FakeDCMObject(1), FakeDCMObject(54)]
    mock_dicoms.return_value = dcms
    preprocessor = PrePredictionProcessor(logging_dir)
    processed, origin_imgs_array, results = preprocessor.execute(None,
            slice_interval=[120, 240],
            resize_shape=[240, 256, 320],
            slice_or_resize="slice"
    )
    assert results[0].SliceLocation == 54
