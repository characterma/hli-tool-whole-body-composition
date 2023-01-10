import pytest
import hli_python3_utils
import os
import re
import glob

file_utils = hli_python3_utils.client("FileUtils")

def test_s3_paths_in_tasks():
    """
    Ensure no s3 paths are used in the task file (these are not allowed as they will not get promoted appropriately
    """
    s3_regex = re.compile("(s3://)|(s3a://)")
    task_dir = "/opt/project/dpl/task"
    task_files = [os.path.join(task_dir, x) for x in os.listdir(task_dir)]
    for task in task_files:
        with open(task, 'r') as task_file:
            for line in task_file:
                assert s3_regex.search(line) is None


def test_task_muscle(dpl_env, dpl_repo_bucket, dpl_cache_bucket, username):
    '''input dir contains 512 GE images
    
    :Satisfies: SRS Requirement 1.2
    '''
    dpl_utils = hli_python3_utils.client("DPLUtils")
    dpl_utils.add_dpl_run(pipeline="whole_body_composition",
                          params={'modality':'MUSCLE','model_file':'s3://hli-anonymous-sdrad-pdx/imaging/agraff/databricks/DeepNetV3_WATER_with_aug_bias_default_dice_transferlr_dup2x/water_production.h5','input_dir':'s3://hli-anonymous-sdrad-pdx/imaging/wbc_input/wbc_radnet_2_w',
                          'sample_id':'222',
                          'output_filename': 'test_filename.json',
                          'muscle_color': '119,252,226',
                          'vat_color': '115,220,255',
                          'asat_color': '252,111,130'},
                          env=dpl_env,
                          username=username)
    dpl_utils.submit_dpl_runs()
    dpl_utils.monitor_dpl_runs(sleep_time=60, max_time=30000, log=2)   #CHANGE THESE IF LONG RUNNING
    workflow_id = dpl_utils.get_dpl_runs()[0].workflow_id

    output_path = os.path.join("s3://", dpl_cache_bucket, workflow_id, "whole_body_composition", 'images')

    for i in range(0, 512):
        assert file_utils.is_file(os.path.join(output_path, 'sagittal-'+str(i)+'.dcm'))

    for i in range(0, 512):
        assert file_utils.is_file(os.path.join(output_path, 'coronal-'+str(i)+'.dcm'))

    for i in range(0, 512):
        assert file_utils.is_file(os.path.join(output_path, 'axial-'+str(i)+'.dcm'))

def test_task_fat(dpl_env, dpl_repo_bucket, dpl_cache_bucket, username):
    '''input dir contains 512 GE images
    
    :Satisfies: SRS Requirement 1.2
    '''
    dpl_utils = hli_python3_utils.client("DPLUtils")
    dpl_utils.add_dpl_run(pipeline="whole_body_composition",
                          params={'modality':'FAT','model_file':'s3://hli-anonymous-sdrad-pdx/imaging/agraff/databricks/DeepNetV3plus_AllSamples2x_dup_aug_dice_pretrained_on_masks_lr_.0001/test_save.h5','input_dir':'s3://hli-anonymous-sdrad-pdx/imaging/wbc_input/wbc_radnet_2_ht_wt_f',
                          'sample_id':'222',
                          'output_filename':'test_filename.json',
                          'muscle_color': '119,252,226',
                          'vat_color': '115,220,255',
                          'asat_color': '252,111,130'},
                          env=dpl_env,
                          username=username)
    dpl_utils.submit_dpl_runs()
    dpl_utils.monitor_dpl_runs(sleep_time=60, max_time=30000, log=2)   #CHANGE THESE IF LONG RUNNING
    workflow_id = dpl_utils.get_dpl_runs()[0].workflow_id

    output_path = os.path.join("s3://", dpl_cache_bucket, workflow_id, "whole_body_composition", 'images')

    for i in range(0, 512):
        assert file_utils.is_file(os.path.join(output_path, 'sagittal-'+str(i)+'.dcm'))

    for i in range(0, 512):
        assert file_utils.is_file(os.path.join(output_path, 'coronal-'+str(i)+'.dcm'))

    for i in range(0, 512):
        assert file_utils.is_file(os.path.join(output_path, 'axial-'+str(i)+'.dcm'))


