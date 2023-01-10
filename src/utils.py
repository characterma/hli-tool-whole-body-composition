import hli_python3_utils
import logging
import os
import sys
import subprocess
import shlex, shutil
import glob

logging_utils = hli_python3_utils.client("LoggingUtils")
file_utils    = hli_python3_utils.client("FileUtils")

logger = logging_utils.get_logger("utils.log")


def validate_file(description, the_file):
    '''Confirms files exists using hli_python3_utils if not then exit: 1
    :param description: A file description, for error reporting purposes
    :param the_file: The file to check for existence
    '''
    if not file_utils.is_file(the_file):
        logger.error('Missing {}: {}'.format(description, the_file))
        sys.exit(1)


def run_command(cmd):
    '''Generalize the Popen command.
    '''
    try:
        process = subprocess.Popen(shlex.split(cmd),
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)

        for line in process.stdout.readlines():
            logger.info(line)

        process.wait()
        logger.info(f"process.returncode: {process.returncode}")
        if process.returncode != 0:
            raise Exception('Error calling command: {}'.format(cmd))

    except Exception as e:
        logger.error('Error : ' + str(e))
        sys.exit(1)


def copy_input_dir_to_working_dir(input_dir, working_dir):
    '''Copies a clinical data 'directory' from s3 to working_dir.
       So far bix_python_utils only has api to copy single files.
    '''
    local_dir = os.path.join(working_dir, 'input_images')
    local_dir_1 = os.path.join(working_dir, 'images')

    # newly updated
    if not os.path.exists(local_dir):
        os.makedirs(local_dir)
    else:
        shutil.rmtree(local_dir)
        os.makedirs(local_dir)
    
    if os.path.exists(local_dir_1):
        shutil.rmtree(local_dir_1)

    if 's3' in input_dir:

        cmd = 'aws s3 cp --recursive ' + input_dir + ' ' + local_dir 
        run_command(cmd)

    else:
        files_2_copy = glob.glob(os.path.join(input_dir, '*'))
        for in_file in files_2_copy:
            file_utils.get_file(in_file, local_dir, os.path.basename(in_file))

    return local_dir

def copy_model_file(model_path, working_dir):
    '''Copies the model file for use locally'''
    path = os.path.join(working_dir, "model.h5")
    cmd = "aws s3 cp " + model_path + " " + path
    run_command(cmd)
    return path

# newly added
def copy_range_file(range_file, working_dir):
    '''Copies the normal range file for use locally'''
    path = os.path.join(working_dir, "AMRA_NORMAL_RANGES.xlsx")
    cmd = "aws s3 cp " + range_file + " " + path
    run_command(cmd)
    return path

def write_results_to_output(working_dir, output_dir, output_filename):
    '''Writes the resulting images to output/images and the json to output.
    '''    
    if not output_dir.endswith(os.path.sep): output_dir+=os.path.sep
    
    logger.info('Writing results to: {}'.format(output_dir))

    # newly added
    from_output_pngs = glob.glob(os.path.join(working_dir, '*.png'))

    for from_output_png in from_output_pngs:
        to_output_png = os.path.join(output_dir, os.path.basename(from_output_png))
        file_utils.copy(from_output_png, to_output_png)

    from_output_jsons = glob.glob(os.path.join(working_dir, '*.json'))
    
    for from_output_json in from_output_jsons:        
        to_output_json = os.path.join(output_dir, os.path.basename(from_output_json))
        file_utils.copy(from_output_json, to_output_json)
    
    from_output_images = os.path.join(working_dir, 'images')
    from_output_images += os.path.sep

    to_output_images = os.path.join(output_dir, 'images')
    to_output_images += os.path.sep
    
    # newly added
    if os.path.exists(to_output_images):
        shutil.rmtree(to_output_images)
        os.makedirs(to_output_images)

    file_utils.copy(from_output_images, to_output_images) 
    

    
