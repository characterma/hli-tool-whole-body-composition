import pytest
import numpy as np
import os, sys
from predictions.post_prediction_processor import PostPredictionProcessor
from predictions.pre_prediction_processor import PrePredictionProcessor
import mock
import os, shutil
import json
import pydicom as dcm

working_dir = '../tests/integration_tests/working_dir'
output_dir  = '../tests/integration_tests/output_dir'
logging_dir = '../tests/integration_tests/logging_dir'
muscle_dicom = '../tests/resources/test_inputs/water'
fat_dicom = '../tests/resources/test_inputs/fat'
range_file = '../tests/resources/AMRA_NORMAL_RANGES.xlsx' # newly added
colors = {}
colors['muscle_color'] = '119,252,226'
colors['vat_color'] = '252,111,130'
colors['asat_color'] = '115,220,255'

def setup_module(self):
    if not os.path.exists(logging_dir): os.makedirs(logging_dir)
    if not os.path.exists(working_dir): os.makedirs(working_dir)

def teardown_module(self):
    if os.path.exists(logging_dir): shutil.rmtree(logging_dir)
    if os.path.exists(working_dir): shutil.rmtree(working_dir)

def test_resize_to_original_dims():
    post_prediction_processor = PostPredictionProcessor(logging_dir, "FAT", range_file, None, colors) # newly updated
    predictions=np.random.randint(0,2,size=[240,256,320])
    origin_imgs_array = np.random.randint(0, 1, size=[556, 260, 320])
    complete_predictions = post_prediction_processor.resize_to_original_dims(predictions, origin_imgs_array, slice_interval=[120, 360], slice_or_resize='resize')
    assert complete_predictions.shape == origin_imgs_array.shape
    
def test_slice_to_original_dims():
    post_prediction_processor = PostPredictionProcessor(logging_dir, "FAT", range_file, None, colors) # newly updated
    predictions=np.random.randint(0,2,size=[240,256,320])
    origin_imgs_array = np.random.randint(0, 1, size=[556, 260, 320])
    complete_predictions = post_prediction_processor.resize_to_original_dims(predictions, origin_imgs_array, slice_interval=[120, 360], slice_or_resize='slice')
    assert complete_predictions.shape == origin_imgs_array.shape

def test_output_json():
    '''Tests that the output json contains the expected format and text.
    
    :Satisfies: SRS Requirements 3.1 and 3.3
    '''
    post_prediction_processor = PostPredictionProcessor(logging_dir, "FAT", range_file, None, colors) # newly updated
    # Create a 3x3 matrix with 6 pixels for each SAT and 1 Pixel for VAT, 7 pixels is
    # fake_results = np.eye(3) * [0, 1, 2]
    fake_results = np.ones((3,3,3)) # newly added
    fake_results[0][1][1] = fake_results[1][1][1] = fake_results[2][1][1] = 1
    fake_results[0][2][2] = fake_results[1][2][2] = fake_results[2][2][2] = 2
    fat_dicom_objs = [dcm.read_file(os.path.join(fat_dicom, file)) for file in os.listdir(fat_dicom) if file.endswith('.dcm')]
    stats = post_prediction_processor.calculate_stats(fake_results, fat_dicom_objs)
    patient_normal_ranges = [88,'Female','1.82-3.91L','23.25%-33.02%','0.71-1.50L/m2','5.47-8.80L','7.82-9.53kg/L','6.84-8.12L','19000101', 'rrc_01_w', '089Y', 'M', 'rrc_01_w', 'rrc_01_w_with_age_sex'] # newly added
    post_prediction_processor.write_output_json(stats, working_dir, 'FAT', '222', 'output.json', patient_normal_ranges) # newly updated
    
    with open(os.path.join(working_dir,'output.sat_volume.json'), 'r') as f:
        data = json.load(f)
        assert data['resourceType'] == 'Observation'
        assert data['id'] == 'MR'
        assert data['text']['status'] == 'generated'
        assert 'tissue volume' in data['text']['div']
        assert data['status'] == 'final'
        assert data['code']['coding'][0]['system'] == 'https://www.humanlongevity.com'
        assert data['code']['coding'][0]['code'] == '123456-2'
        assert data['code']['coding'][0]['display'] == 'Abdominal subcutaneous adipose tissue volume'
        assert data['subject']['reference'] == 'Patient/222'
        assert data['performer'][0]['reference'] == 'Organization/Human Longevity, Inc.'
        assert data['device']['display'] == 'MRI: Siemens'
        assert data['valueQuantity']['value'] == 0 # updated from 0.0
        assert data['valueQuantity']['unit'] == 'L'
        assert data['valueQuantity']['system'] == 'http://unitsofmeasure.org'
        assert data['valueQuantity']['code'] == 'L'
        assert data['bodySite']['text'] == 'MR Whole body'
        assert data['bodySite']['coding'][0]['system'] == 'http://loinc.org'
        assert data['bodySite']['coding'][0]['code'] == '46358-8'       


def test_fat_calculate_stats():
    '''Tests that the machine learning algorithm can calculate sat/vat volumes
    as well as return other related statistics using FAT input images.
    
    :Satisfies: SRS Requirement 2.1
    '''
    
    post_prediction_processor = PostPredictionProcessor(logging_dir, "FAT", range_file, None, colors) # newly updated
    # Create a 3x3 matrix with 6 pixels for each SAT and 1 Pixel for VAT, 7 pixels is
    #fake_results = np.eye(3) * [0, 1, 2]
    fake_results = np.zeros((3,3,3))
    fake_results[0][1][1] = fake_results[1][1][1] = fake_results[2][1][1] = 1
    fake_results[0][2][2] = fake_results[1][2][2] = fake_results[2][2][2] = 2
    fat_dicom_objs = [dcm.read_file(os.path.join(fat_dicom, file)) for file in os.listdir(fat_dicom) if file.endswith('.dcm')]
    stats = post_prediction_processor.calculate_stats(fake_results, fat_dicom_objs)
    assert stats["sat_volume"] == '0.00' # b/c single image
    assert stats["vat_volume"] == '0.00' # b/c single image
    assert stats["manufacturer"] == 'Siemens'
    assert stats["patient_weight"] == '71'
    assert stats["vat_index"] == '0.00' # b/c single image
    assert stats["vat_ratio"] == '50.00' # b/c single image
    assert stats["height_meters"] == '1.68'


def test_muscle_calculate_stats():
    '''Tests that the machine learning algorithm can calculate sat/vat volumes
    as well as return other related statistics using MUSCLE input images.
    
    :Satisfies: SRS Requirement 2.1
    '''
    post_prediction_processor = PostPredictionProcessor(logging_dir, "MUSCLE", range_file, None, colors) # newly updated
    # Create a 2x2 matrix with 3 pixels for Muscle and 1 pixel for background
    #fake_results = np.eye(2) * [0, 1]
    fake_results = np.zeros((2,2,2))
    fake_results[0][1][1] = fake_results[1][1][1] = 1
    muscle_dicom_objs = [dcm.read_file(os.path.join(muscle_dicom, file)) for file in os.listdir(muscle_dicom) if file.endswith('.dcm')]
    stats = post_prediction_processor.calculate_stats(fake_results, muscle_dicom_objs)
    assert stats["manufacturer"] == 'Siemens' # updated from 'GE MEDICAL SYSTEMS'
    assert stats["patient_weight"] == '58' # updated from '54'
    assert stats["muscle_volume"] == '0.00' # b/c single image
    assert stats["muscle_ratio"] == '4653812.22' # updated from '6341717.23'    


def test_select_most_confident():
    '''Test verifies the most confident (highest probability value) prediction is selected.
    '''
    post_prediction_processor = PostPredictionProcessor(logging_dir, "MUSCLE", range_file, None, colors) # newly updated
    # Creates a small test matrix which contains fake probabilities, should return the index location of the highest
    # value, in this case in the first column position 1, and in the second column position 0
    fake_matrix = np.random.rand(3, 240, 256, 320)
    fake_matrix = np.expand_dims(fake_matrix, 0)
    most_confident = post_prediction_processor.select_most_confident(fake_matrix)
    assert most_confident.shape == (240, 256, 320)
    


