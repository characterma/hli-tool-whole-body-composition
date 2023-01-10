import pytest
import shutil, shlex
import os, sys
import json
import glob
import hli_python3_utils
import logging
import pydicom as dcm
import numpy as np
from subprocess import Popen, PIPE
import warnings
warnings.filterwarnings("ignore")

working_dir = './tests/integration_tests/working_dir'
output_dir  = './tests/integration_tests/output_dir'
logging_dir = './tests/integration_tests/logging_dir'

file_utils       = hli_python3_utils.client('FileUtils')
logging_utils    = hli_python3_utils.client('LoggingUtils')

logger = logging.getLogger("test_main.log")

def setup_module(module):
    '''Sets up before tests.'''
    if not os.path.exists(working_dir):
        os.makedirs(working_dir)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    if not os.path.exists(logging_dir):
        os.makedirs(logging_dir)

def teardown_module(module):
    '''Cleans up after tests'''
    shutil.rmtree(working_dir)
    print

def teardown_function(function):
    '''Cleans up after each test.'''
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.mkdir(output_dir)
    print

def call_main(input_dir, modality, model_file, range_file, sample_id, output_filename, output_dir=output_dir, working_dir=working_dir, logging_dir=logging_dir):
    '''Utility function: Calls main.py
    '''
    err = None
    out = None

    command = shlex.split('python3 main.py '
                            '--sample_id {} '
                            '--model_file {} '
                            '--input_dir {} '
                            '--modality {} '
                            '--range_file {} '
                            '--working_dir {} '
                            '--logging_dir {} '
                            '--output_dir  {} '
                            '--output_filename {}'.format(sample_id,
                                                      model_file,
                                                      input_dir,
                                                      modality,
                                                      range_file,
                                                      working_dir,
                                                      logging_dir,
                                                      output_dir,
                                                      output_filename))
    print(f"command: {command}")
    try:

        process = Popen(command, stdout=PIPE, stderr=PIPE)
        out, err = process.communicate()
        exit_code = process.returncode
        print(f"process: {process}, out: {out}, err: {err}, exit_code: {exit_code}")
        if exit_code != 0:
            raise Exception('Error calling command: {}'.format(command))

    except Exception as e:
        logger.error('Failed : ' + str(e))
        logger.error('STDERR : ' + str(err))
        logger.error('STDOUT : ' + str(out))
        sys.exit(1)

    return exit_code, out, err

def test_muscle():
    '''Tests GE instrument for the expected file output and expected file content.
    
    :Satisfies: SRS Requirements 1.2, 3.2, 3.4, and 3.6-3.7
    '''

    model_file = 's3://hli-anonymous-sdrad-pdx/wbc_test/model_2_version/water_epoch35_trainloss_0.037_validacc_0.961.pth'
    input_dir = 's3://hli-anonymous-sdrad-pdx/wbc_test/test_dicom/water/'
    range_file = 's3://hli-anonymous-sdrad-pdx/wbc_test/AMRA_NORMAL_RANGES.xlsx'
    modality  = 'MUSCLE'
    sample_id = '222'
    output_filename = 'outputfilename.json'
    print("begin test muscle")
    call_main(input_dir, modality, model_file, range_file, sample_id, output_filename)
    
    assert os.path.exists(os.path.join(output_dir, "MUSCLE_4_report.png")) == True
    
    images_output_dir = os.path.join(output_dir, 'images')
    dicom_files = glob.glob(images_output_dir + '/*.dcm')
    assert len(dicom_files) == 556+260+320 # updated from 1536
    
    muscle_volume = os.path.join(output_dir, output_filename.replace('.json', '.muscle_volume.json'))
    assert file_utils.is_file(muscle_volume)
    
    muscle_ratio = os.path.join(output_dir, output_filename.replace('.json', '.muscle_ratio.json'))
    assert file_utils.is_file(muscle_ratio)

    patient_weight = os.path.join(output_dir, output_filename.replace('.json', '.patient_weight.json'))
    assert file_utils.is_file(patient_weight)      

def test_fat():
    '''Tests GE instrument for the expected file output and expected file content.
    
    :Satisfies: SRS Requirement 1.2, 3.2, 3.4, and 3.6-3.7
    '''

    model_file = 's3://hli-anonymous-sdrad-pdx/wbc_test/model_2_version/fat_epoch51_trainloss_0.070_validacc_0.942.pth'
    input_dir = 's3://hli-anonymous-sdrad-pdx/wbc_test/test_dicom/fat'
    range_file = 's3://hli-anonymous-sdrad-pdx/wbc_test/AMRA_NORMAL_RANGES.xlsx'
    modality  = 'FAT'
    sample_id = '222'
    output_filename = 'outputfilename.json'
    print("begin test fat")
    call_main(input_dir, modality, model_file, range_file, sample_id, output_filename)
    
    assert os.path.exists(os.path.join(output_dir, "FAT_4_report.png")) == True
    
    images_output_dir = os.path.join(output_dir, 'images')
    dicom_files = glob.glob(images_output_dir + '/*.dcm')
    assert len(dicom_files) == 556+260+320 # updated from 1536
            
    sat_volume = os.path.join(output_dir, output_filename.replace('.json', '.sat_volume.json'))
    assert file_utils.is_file(sat_volume)
    
    vat_volume = os.path.join(output_dir, output_filename.replace('.json', '.vat_volume.json'))
    assert file_utils.is_file(vat_volume)
        
    patient_weight = os.path.join(output_dir, output_filename.replace('.json', '.patient_weight.json'))
    assert file_utils.is_file(patient_weight)

    vat_index = os.path.join(output_dir, output_filename.replace('.json', '.vat_index.json'))
    assert file_utils.is_file(vat_index)
    
    vat_ratio = os.path.join(output_dir, output_filename.replace('.json', '.vat_ratio.json'))
    assert file_utils.is_file(vat_ratio)
    
    height_meters = os.path.join(output_dir, output_filename.replace('.json', '.height_meters.json'))
    assert file_utils.is_file(height_meters)
