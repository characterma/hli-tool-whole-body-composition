"""
Usage:
    main.py  --sample_id <sample_id> --model_file <model_file> --input_dir <input_dir> --modality <modality> --range_file <range_file> [--output_filename <output_filename>] [--working_dir <working_dir>] [--logging_dir <logging_dir>] [--output_dir <output_dir>] [--muscle_color <muscle_color>] [--vat_color <vat_color>] [--asat_color <asat_color>]


Arguments:
    --sample_id <sample_id>                The health data ID
    --input_dir <input_dir>                Directory of dicoms to process (local or s3)
    --model_file <model_file>              Location of model file (local or S3)
    --modality <modality>                  Indicates wether processing fat or muscle
    --range_file <range_file>              Normal range excel file for output biomarkers
    --num_classes <num_classes>            class number, fat: (ASAT, VAT, OTHRE) is 3, water: (tight muscle, other) is 2
    --slice_interval <slice_interval>      Slice interval range on the cross section of the original image [default: 1:556]
    --resize_shape <resize_shape>          Resize the image data after slicing to the corresponding size [default: 160,128,232]
    --slice_or_resize <slice_or_resize>    Ways to reduce data size："slice" or "resize" [default: slice]

    
Options:
    --output_filename <output_filename>  The name of the output json filename [default: whole_body_composition.json]
    --working_dir <working_dir>          Working directory to use for downloading and processing files [default: /scratch]
    --logging_dir <logging_dir>          Directory to write log files to [default: /clogs]
    --output_dir <output_dir>            Output directory (local or s3) folder path [default: /mnt]
    --muscle_color <muscle_color>        Color for muscle tissue [default: 119,252,226]
    --vat_color <vat_color>              Color for viceral adipose fat tissue [default: 252,111,130]
    --asat_color <asat_color>            Color for subcutaneous fat tissue [default: 115,220,255]
    


   Uses a machine learning algorithm to perform segmentation of visceral adipose tissue (VAT), abdominal subcutaneous adipose tissue (ASAT) and thigh muscle.
   Colors the output dicom images by tissue type, calculates volume and other statistics which are written to the dicom images and HL7 FHIR compliant output json.
"""

import hli_python3_utils
import logging
import sys
import argparse
import os
import utils
from docopt import docopt
from interfaces.run_job import RunJobInterface
import hli_python3_utils
import shutil

file_utils = hli_python3_utils.client("FileUtils")

#Set up logging to file
logging_utils = hli_python3_utils.client("LoggingUtils")

def get_parameters(modality):
    if modality == "MUSCLE":
        slice_interval = [197,501]
        resize_shape = [304,256,320]
        num_classes = 2
        slice_or_resize = 'slice'
    elif modality == "FAT":
        slice_interval = [120,360]
        resize_shape = [240,256,320]
        num_classes = 3
        slice_or_resize = 'slice'
    else:
        raise Exception(f"modality value must be MUSCLE or FAT, current value of get modality is {modality}")
    return slice_interval, resize_shape, num_classes, slice_or_resize


def main(arguments):
    
    parser_utils = hli_python3_utils.client('ParserUtils')

    
    arguments = docopt(__doc__)
    args = parser_utils.convert_docopt_arguments_to_argparse(arguments)
    logger = logging_utils.get_logger(os.path.join(args.logging_dir, "whole-body-composition.log"))

    modality = args.modality.upper()
    if modality != 'MUSCLE' and modality != 'FAT':
        logger.error('Invalid modality type specified: {}, must be either FAT or MUSCLE'.format(modality))
        sys.exit(1)
        
    colors = {}
    colors['muscle_color'] = [int(i) for i in args.muscle_color.split(',')]
    colors['vat_color']    = [int(i) for i in args.vat_color.split(',')]
    colors['asat_color']   = [int(i) for i in args.asat_color.split(',')]
    
    # resize_shape = [int(i) for i in args.resize_shape.split(",")]
    # slice_interval = [int(i) for i in args.slice_interval.split(",")]
    
    slice_interval, resize_shape, num_classes, slice_or_resize = get_parameters(modality)
    
    assert len(slice_interval) == 2, Exception("The length of the slice interval variable must be 2")
    logger.info(f'resize shape is {resize_shape}, slice interval is {slice_interval}')

    if not os.path.exists(args.logging_dir):
        logger.error('Missing logging_dir: {}'.format(args.logging_dir))
        os.makedirs(args.logging_dir)
        # sys.exit(1)
    else:
        shutil.rmtree(args.logging_dir)
        os.makedirs(args.logging_dir)
        
    if not os.path.exists(args.working_dir):
        logger.error('Missing working_dir: {}'.format(args.working_dir))
        os.makedirs(args.working_dir)
    else:
        shutil.rmtree(args.working_dir)
        os.makedirs(args.working_dir)
        
        

    # validate files exist in s3
    utils.validate_file('Model file', args.model_file)
   
    # download the files from s3   
    model_file  = utils.copy_model_file(args.model_file, args.working_dir)
    dicom_path = utils.copy_input_dir_to_working_dir(args.input_dir, args.working_dir)
    range_file = utils.copy_range_file(args.range_file, args.working_dir) # newly added

    logger.info('Executing Analysis...')
    run_interface = RunJobInterface(args.logging_dir, modality, int(num_classes), model_file, range_file, args.working_dir, args.sample_id, args.output_filename, colors, resize_shape)
    run_interface.execute(dicom_path, slice_interval, resize_shape, slice_or_resize=slice_or_resize)
    
    utils.write_results_to_output(args.working_dir, args.output_dir, args.output_filename)
    logger.info('Analysis complete...')

if __name__ == '__main__':
    main(sys.argv[1:])
