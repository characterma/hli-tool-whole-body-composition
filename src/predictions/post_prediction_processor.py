import copy
import logging
import logging
import os
import sys
import time

import SimpleITK as sitk
import cv2
import cv2
import hli_python3_utils
import matplotlib.image as image  # newly added
import numpy as np
import pandas as pd  # newly added
import pydicom
from scipy.ndimage import zoom
from skimage.filters import gaussian
from skimage.transform import resize  # newly added

logging_utils = hli_python3_utils.client("LoggingUtils")


class PostPredictionProcessor:
    def __init__(self, logging_dir, modality, range_file, local_images_dir, colors, model_version='torch'):
        ''' Configures the post prediction processor module.
        :param colors: Dictionary with definitions for muscle, vat and asat colors.
        :param local_images_dir: Directory containing the input images.
        :param range_file: local normal range file.
        :param modality: Specifies which Model we used in order to predict, valid values are [FAT, MUSCLE]
        '''
        self.logger = logging_utils.get_logger(os.path.join(logging_dir, "post_predition_processor.log"))
        self.model_version = model_version
        self.modality = modality
        self.range_file = range_file
        self.local_images_dir = local_images_dir
        self.alpha = 0.3
        self.vat_label = 1
        self.asat_label = 2
        self.muscle_label = 1
        self.other_label = 0
        if modality == "MUSCLE":
            self.colors = {
                self.muscle_label: colors['muscle_color']
            }

        elif modality == "FAT":
            self.colors = {
                self.vat_label: colors['vat_color'],
                self.asat_label: colors['asat_color']
            }

    def execute(self, predictions, origin_imgs_array, dcm_objs, slice_interval, dicom_path, sample_id, output_filename, slice_or_resize='slice'):
        '''Flow of control mechanism for the post prediction processor.
        1. Selects the most confident prediction.
        2. Resizes the output images to the original input image dimensions.
        3. Calculates the stats.
        4. Creates the overlays on the output images including stats.
        5. Writes the images out to a subfolder in the working directory.
        6. Writes the stats jsons out to the working directory.
        
        :param predicitions: The predictions output from prior steps
        :param dcm_objs: The original dicom image objects
        :param dicom_path: The original dicom images
        :param sample_id: Patient identifier
        :output_filename: The prefix for all output jsons
        '''
        self.logger.info("Post-Prediction Processing Started, selecting highest probability indexes")
        predictions = self.select_most_confident(predictions)
        self.logger.info("Resizing Predictions to original dicom dimensions")
        resized_predictions = self.resize_to_original_dims(predictions, origin_imgs_array, slice_interval, slice_or_resize)
        self.logger.info("Calculating volumes")
        stats = self.calculate_stats(resized_predictions, dcm_objs)

        # newly added
        self.logger.info("Returning patient normal ranges")
        patient_normal_ranges = self.return_amra_normal_ranges(dcm_objs)
        self.logger.info("patient normal ranges: " + str(patient_normal_ranges))

        self.logger.info("Creating Overlays")
        overlayed_images = self.create_overlays(resized_predictions, dcm_objs, stats,
                                                patient_normal_ranges)  # newly updated


        self.logger.info("Writing 3D array2dcm")
        coronal_factor_calc = self.write_3D_array2dcm(overlayed_images, dicom_path, self.local_images_dir,
                                                      1)  # newly updated

        self.logger.info("Writing output json")
        self.write_output_json(stats, self.local_images_dir, self.modality, sample_id, output_filename,
                               patient_normal_ranges)  # newly updated
        # https://www.hl7.org/fhir/json.html

        # newly added
        self.logger.info("Saving Muscle/Fat Coronal Images for Report, pixel spacing: " + str(coronal_factor_calc))
        self.save_imgs_4_report(overlayed_images, self.local_images_dir, self.modality, stats, coronal_factor_calc)

    # newly added
    def save_imgs_4_report(self, overlayed_images, outputdir, modality, stats, coronal_factor_calc):
        img_no = int(stats['img2display'])
        self.logger.info("img_no: " + str(img_no))

        array3D = np.array(overlayed_images)
        self.logger.info("shape of array3D: " + str(array3D.shape) + ", shape number: " + str(len(array3D.shape)))

        if len(array3D.shape) == 4:
            image_slice = array3D[:, img_no, :]
            self.logger.info(
                "shape of array3D: " + str(array3D.shape) + "; shape of image_slice: " + str(image_slice.shape))

            factor = coronal_factor_calc[1] / coronal_factor_calc[0]
            self.logger.info(str(coronal_factor_calc[0]) + " " + str(coronal_factor_calc[1]) + " " + str(factor))

            new_image_slice = resize(image_slice, (image_slice.shape[0], int(image_slice.shape[1] / factor)))
            self.logger.info("factor: " + str(factor) + "; shape of new_image_sclie:  " + str(new_image_slice.shape))

            filename = os.path.join(outputdir, modality + '_4_report' + '.png')
            image.imsave(filename, new_image_slice)

    # newly added
    def return_amra_normal_ranges(self, sample_dicom):
        # check DICOM file to get patient_age, patient_sex, acquisition_date
        """
        read origin dicom data from local path
        :param sample_dicom: origin dicom data, [dicom_obj1, dicom_obj2, dicom_obj3,…… dicom_obj556]
        :return:
        """
        patient_age = sample_dicom[0].PatientAge
        patient_sex = sample_dicom[0].PatientSex
        acquisition_date = sample_dicom[0].AcquisitionDate
        patient_name = str(sample_dicom[0].PatientName)
        patient_id = sample_dicom[0].PatientID
        accession_number = sample_dicom[0].AccessionNumber

        self.logger.info("range_file: " + self.range_file)
        # search the lookup table to get patient normal ranges
        if patient_sex == 'F':
            df = pd.read_excel(self.range_file, sheet_name='AMRA_NORMAL_RANGES_female')
        else:
            df = pd.read_excel(self.range_file, sheet_name='AMRA_NORMAL_RANGES_male')

        for i in range(len(df)):
            age = df.loc[i].values[0]

            if age == int(patient_age[:-1]):
                self.logger.info("the returned amra normal ranges: " + str(df.loc[i].values) + str(acquisition_date))
                patient_normal_ranges = df.loc[i].values.tolist()
                self.logger.info(f"patient_normal_ranges：{patient_normal_ranges}")
                patient_normal_ranges = patient_normal_ranges + [acquisition_date, patient_name, patient_age,
                                                                 patient_sex, patient_id, accession_number]
                self.logger.info(f"complete patient_normal_ranges：{patient_normal_ranges}")
                return patient_normal_ranges
        self.logger.info(f"patient age is {patient_age}, No normal range data about this age")
        patient_normal_ranges = [patient_age, patient_sex] + ["No Normal Range Established"] * 6
        patient_normal_ranges = patient_normal_ranges + [acquisition_date, patient_name, patient_age, patient_sex,
                                                         patient_id, accession_number]
        self.logger.info(f"fix complete patient_normal_ranges info: {patient_normal_ranges}")
        return patient_normal_ranges

    def write_output_json(self, stats_dict, working_dir, modality, sample_id, output_filename, patient_normal_ranges):
        ''' Creates an HL7 FHIR v4.0.1 compliant output json to report statistics.
        
        :param stats_dict: dictionary containing all calculated stats
        :param working_dir: local working directory
        :param modality: FAT or MUSCLE mode
        :param sample_id: patient identifier
        :output_filename: The prefix for all output jsons
        '''
        # https://www.hl7.org/fhir/observation-example-bmd.json.html
        # Of course, there's the generic LOINC term 29463-7 Body weight.
        # https://search.loinc.org/searchLOINC/search.zul?query=mri

        output_json = os.path.join(working_dir, output_filename)

        if modality == 'MUSCLE':

            ##### muscle_volume https://search.loinc.org/searchLOINC/search.zul?query=26235-2 <-bilateral thigh
            ##### perhaps also search for MR lower extremity hip pelvic

            output_json = os.path.join(working_dir, output_filename.replace('.json', '.muscle_volume.json'))

            json_dict = {}
            json_dict['feature_system'] = 'https://www.humanlongevity.com'
            json_dict['feature_system_acronym'] = 'HLI'
            json_dict['feature_code'] = '123456-1'
            json_dict['feature_name'] = 'Thigh muscle volume'
            json_dict['feature_value'] = stats_dict['muscle_volume']
            json_dict['manufacturer'] = stats_dict['manufacturer']
            json_dict['units_of_measure'] = 'L'
            json_dict['body_site_sytem_name'] = 'LOINC MR code'
            json_dict['body_site_code'] = '46358-8'
            json_dict['body_site_system'] = 'http://loinc.org'
            json_dict['units_of_measure_system'] = 'http://unitsofmeasure.org'
            json_dict['units_of_measure_system_name'] = 'UCUM'
            json_dict['normal_range'] = patient_normal_ranges[7]

            json_dict['acquisition_date'] = patient_normal_ranges[8]
            json_dict['patient_name'] = patient_normal_ranges[9]
            json_dict['patient_age'] = patient_normal_ranges[10]
            json_dict['patient_sex'] = patient_normal_ranges[11]
            json_dict['patient_id'] = patient_normal_ranges[12]
            json_dict['accession_number'] = patient_normal_ranges[13]

            self.make_observation(output_json, json_dict, sample_id)

            ##### muscle_ratio https://search.loinc.org/searchLOINC/search.zul?query=73965-6

            output_json = os.path.join(working_dir, output_filename.replace('.json', '.muscle_ratio.json'))

            json_dict['feature_system'] = 'http://loinc.org'
            json_dict['feature_system_acronym'] = 'HLI'
            json_dict['feature_code'] = '00000-1'
            json_dict['feature_name'] = 'Thigh muscle ratio'
            json_dict['feature_value'] = stats_dict['muscle_ratio']
            json_dict['manufacturer'] = stats_dict['manufacturer']
            json_dict['units_of_measure'] = 'kg/L'
            json_dict['body_site_sytem_name'] = 'LOINC MR code'
            json_dict['body_site_code'] = '46358-8'
            json_dict['body_site_system'] = 'http://loinc.org'
            json_dict['units_of_measure_system'] = 'http://unitsofmeasure.org'
            json_dict['units_of_measure_system_name'] = 'UCUM'
            json_dict['normal_range'] = patient_normal_ranges[6]

            json_dict['acquisition_date'] = patient_normal_ranges[8]
            json_dict['patient_name'] = patient_normal_ranges[9]
            json_dict['patient_age'] = patient_normal_ranges[10]
            json_dict['patient_sex'] = patient_normal_ranges[11]
            json_dict['patient_id'] = patient_normal_ranges[12]
            json_dict['accession_number'] = patient_normal_ranges[13]

            self.make_observation(output_json, json_dict, sample_id)

            ##### patient weight https://search.loinc.org/searchLOINC/search.zul?query=29463-7

            output_json = os.path.join(working_dir, output_filename.replace('.json', '.patient_weight.json'))

            json_dict['feature_system'] = 'http://loinc.org'
            json_dict['feature_system_acronym'] = 'LOINC'
            json_dict['feature_code'] = '29463-7'
            json_dict['feature_name'] = 'Body weight'
            json_dict['feature_value'] = stats_dict['patient_weight']
            json_dict['manufacturer'] = stats_dict['manufacturer']
            json_dict['units_of_measure'] = 'kg'
            json_dict['body_site_sytem_name'] = 'LOINC MR code'
            json_dict['body_site_code'] = '46358-8'
            json_dict['body_site_system'] = 'http://loinc.org'
            json_dict['units_of_measure_system'] = 'http://unitsofmeasure.org'
            json_dict['units_of_measure_system_name'] = 'UCUM'
            json_dict['normal_range'] = ''

            json_dict['acquisition_date'] = ''
            json_dict['patient_name'] = patient_normal_ranges[9]
            json_dict['patient_age'] = patient_normal_ranges[10]
            json_dict['patient_sex'] = patient_normal_ranges[11]
            json_dict['patient_id'] = patient_normal_ranges[12]
            json_dict['accession_number'] = ''

            self.make_observation(output_json, json_dict, sample_id)

        elif modality == 'FAT':

            ##### SAT Volume

            output_json = os.path.join(working_dir, output_filename.replace('.json', '.sat_volume.json'))

            json_dict = {}
            json_dict['feature_system'] = 'https://www.humanlongevity.com'
            json_dict['feature_system_acronym'] = 'HLI'
            json_dict['feature_code'] = '123456-2'
            json_dict['feature_name'] = 'Abdominal subcutaneous adipose tissue volume'
            json_dict['feature_value'] = stats_dict['sat_volume']
            json_dict['manufacturer'] = stats_dict['manufacturer']
            json_dict['units_of_measure'] = 'L'
            json_dict['body_site_sytem_name'] = 'LOINC MR code'
            json_dict['body_site_code'] = '46358-8'
            json_dict['body_site_system'] = 'http://loinc.org'
            json_dict['units_of_measure_system'] = 'http://unitsofmeasure.org'
            json_dict['units_of_measure_system_name'] = 'UCUM'
            json_dict['normal_range'] = patient_normal_ranges[5]

            json_dict['acquisition_date'] = patient_normal_ranges[8]
            json_dict['patient_name'] = patient_normal_ranges[9]
            json_dict['patient_age'] = patient_normal_ranges[10]
            json_dict['patient_sex'] = patient_normal_ranges[11]
            json_dict['patient_id'] = patient_normal_ranges[12]
            json_dict['accession_number'] = patient_normal_ranges[13]

            self.make_observation(output_json, json_dict, sample_id)

            ##### VAT_volume

            output_json = os.path.join(working_dir, output_filename.replace('.json', '.vat_volume.json'))

            json_dict['feature_system'] = 'https://www.humanlongevity.com'
            json_dict['feature_system_acronym'] = 'HLI'
            json_dict['feature_code'] = '123456-3'
            json_dict['feature_name'] = 'Visceral adipose tissue volume'
            json_dict['feature_value'] = stats_dict['vat_volume']
            json_dict['manufacturer'] = stats_dict['manufacturer']
            json_dict['units_of_measure'] = 'L'
            json_dict['body_site_sytem_name'] = 'LOINC MR code'
            json_dict['body_site_code'] = '46358-8'
            json_dict['body_site_system'] = 'http://loinc.org'
            json_dict['units_of_measure_system'] = 'http://unitsofmeasure.org'
            json_dict['units_of_measure_system_name'] = 'UCUM'
            json_dict['normal_range'] = patient_normal_ranges[2]

            json_dict['acquisition_date'] = patient_normal_ranges[8]
            json_dict['patient_name'] = patient_normal_ranges[9]
            json_dict['patient_age'] = patient_normal_ranges[10]
            json_dict['patient_sex'] = patient_normal_ranges[11]
            json_dict['patient_id'] = patient_normal_ranges[12]
            json_dict['accession_number'] = patient_normal_ranges[13]

            self.make_observation(output_json, json_dict, sample_id)

            ##### patient weight https://search.loinc.org/searchLOINC/search.zul?query=29463-7

            output_json = os.path.join(working_dir, output_filename.replace('.json', '.patient_weight.json'))

            json_dict['feature_system'] = 'http://loinc.org'
            json_dict['feature_system_acronym'] = 'LOINC'
            json_dict['feature_code'] = '29463-7'
            json_dict['feature_name'] = 'Body weight'
            json_dict['feature_value'] = stats_dict['patient_weight']
            json_dict['manufacturer'] = stats_dict['manufacturer']
            json_dict['units_of_measure'] = 'kg'
            json_dict['body_site_sytem_name'] = 'LOINC MR code'
            json_dict['body_site_code'] = '46358-8'
            json_dict['body_site_system'] = 'http://loinc.org'
            json_dict['units_of_measure_system'] = 'http://unitsofmeasure.org'
            json_dict['units_of_measure_system_name'] = 'UCUM'
            json_dict['normal_range'] = ''

            json_dict['acquisition_date'] = ''
            json_dict['patient_name'] = patient_normal_ranges[9]
            json_dict['patient_age'] = patient_normal_ranges[10]
            json_dict['patient_sex'] = patient_normal_ranges[11]
            json_dict['patient_id'] = patient_normal_ranges[12]
            json_dict['accession_number'] = ''

            self.make_observation(output_json, json_dict, sample_id)

            ##### VAT_index

            output_json = os.path.join(working_dir, output_filename.replace('.json', '.vat_index.json'))

            json_dict['feature_system'] = 'https://www.humanlongevity.com'
            json_dict['feature_system_acronym'] = 'HLI'
            json_dict['feature_code'] = '123456-4'
            json_dict['feature_name'] = 'Visceral adipose tissue index'
            json_dict['feature_value'] = stats_dict['vat_index']
            json_dict['manufacturer'] = stats_dict['manufacturer']
            json_dict['units_of_measure'] = 'L/m2'
            json_dict['body_site_sytem_name'] = 'LOINC MR code'
            json_dict['body_site_code'] = '46358-8'
            json_dict['body_site_system'] = 'http://loinc.org'
            json_dict['units_of_measure_system'] = 'http://unitsofmeasure.org'
            json_dict['units_of_measure_system_name'] = 'UCUM'
            json_dict['normal_range'] = patient_normal_ranges[4]

            json_dict['acquisition_date'] = patient_normal_ranges[8]
            json_dict['patient_name'] = patient_normal_ranges[9]
            json_dict['patient_age'] = patient_normal_ranges[10]
            json_dict['patient_sex'] = patient_normal_ranges[11]
            json_dict['patient_id'] = patient_normal_ranges[12]
            json_dict['accession_number'] = patient_normal_ranges[13]

            self.make_observation(output_json, json_dict, sample_id)

            ##### VAT_ratio

            output_json = os.path.join(working_dir, output_filename.replace('.json', '.vat_ratio.json'))

            json_dict['feature_system'] = 'https://www.humanlongevity.com'
            json_dict['feature_system_acronym'] = 'HLI'
            json_dict['feature_code'] = '123456-5'
            json_dict['feature_name'] = 'Visceral adipose tissue ratio'
            json_dict['feature_value'] = stats_dict['vat_ratio']
            json_dict['manufacturer'] = stats_dict['manufacturer']
            json_dict['units_of_measure'] = '%'
            json_dict['body_site_sytem_name'] = 'LOINC MR code'
            json_dict['body_site_code'] = '46358-8'
            json_dict['body_site_system'] = 'http://loinc.org'
            json_dict['units_of_measure_system'] = 'http://unitsofmeasure.org'
            json_dict['units_of_measure_system_name'] = 'UCUM'
            json_dict['normal_range'] = patient_normal_ranges[3]

            json_dict['acquisition_date'] = patient_normal_ranges[8]
            json_dict['patient_name'] = patient_normal_ranges[9]
            json_dict['patient_age'] = patient_normal_ranges[10]
            json_dict['patient_sex'] = patient_normal_ranges[11]
            json_dict['patient_id'] = patient_normal_ranges[12]
            json_dict['accession_number'] = patient_normal_ranges[13]

            self.make_observation(output_json, json_dict, sample_id)

            ##### patient height

            output_json = os.path.join(working_dir, output_filename.replace('.json', '.height_meters.json'))

            json_dict['feature_system'] = 'http://loinc.org'
            json_dict['feature_system_acronym'] = 'LOINC'
            json_dict['feature_code'] = '8302-2'
            json_dict['feature_name'] = 'Body height'
            json_dict['feature_value'] = stats_dict['height_meters']
            json_dict['manufacturer'] = stats_dict['manufacturer']
            json_dict['units_of_measure'] = 'm'
            json_dict['body_site_sytem_name'] = 'LOINC MR code'
            json_dict['body_site_code'] = '46358-8'
            json_dict['body_site_system'] = 'http://loinc.org'
            json_dict['units_of_measure_system'] = 'http://unitsofmeasure.org'
            json_dict['units_of_measure_system_name'] = 'UCUM'
            json_dict['normal_range'] = ''

            json_dict['acquisition_date'] = ''
            json_dict['patient_name'] = patient_normal_ranges[9]
            json_dict['patient_age'] = patient_normal_ranges[10]
            json_dict['patient_sex'] = patient_normal_ranges[11]
            json_dict['patient_id'] = patient_normal_ranges[12]
            json_dict['accession_number'] = ''

            self.make_observation(output_json, json_dict, sample_id)

        else:
            self.logger.error('Invalid modality selection: {} valid entries are MUSCLE or FAT.'.foramt(modality))
            sys.exit(1)

    def make_observation(self, output_json, json_dict, sample_id):
        '''Writes HL7/FHIR v4.0.1 output json files.  One output file per observation.
        
        :param output_json: The output json suffix
        :param json_dict: Dictionary with inputs for all of the json features.
        '''

        with open(output_json, 'w') as output:
            output.write('{\n')
            output.write('  "resourceType": "Observation",\n')
            output.write('  "id": "MR",\n')
            output.write('  "text": {\n')
            output.write('    "status": "generated",\n')
            output.write(
                '    "div": "<div xmlns=\\"http://www.w3.org/1999/xhtml\\"><p><b>Generated Narrative with Details</b></p><p><b>id</b>: MR</p><p><b>status</b>: final</p><p><b>code</b>: MR Whole body <span>(Details : {' +
                json_dict['feature_system_acronym'] + ' code \'' + json_dict['feature_code'] + '\' = \'' + json_dict[
                    'feature_name'] + '\', given as \'' + json_dict[
                    'feature_name'] + '\'})</span></p><p><b>subject</b>: <a>Patient/' + sample_id + '</a></p><p><b>performer</b>: <a>Human Longevity, Inc.</a></p><p><b>value</b>: ' +
                json_dict['feature_value'] + '' + json_dict['units_of_measure'] + '<span> (Details: ' + json_dict[
                    'units_of_measure_system_name'] + ' code ' + json_dict['units_of_measure'] + ' = \'' + json_dict[
                    'units_of_measure'] + '\')</span></p><p><b>bodySite</b>: MR Whole body <span>(Details : {' +
                json_dict['body_site_sytem_name'] + ' \'' + json_dict[
                    'body_site_code'] + '\' = \'MR Whole Body)</span></p></div>"\n')
            output.write('  },\n')
            output.write('  "status": "final",\n')
            output.write('  "code": {\n')
            output.write('    "coding": [\n')
            output.write('      {\n')
            output.write('        "system": "' + json_dict['feature_system'] + '",\n')
            output.write('        "code": "' + json_dict['feature_code'] + '",\n')
            output.write('        "display": "' + json_dict['feature_name'] + '"\n')
            output.write('      }\n')
            output.write('    ],\n')
            output.write('  "text": "MR Whole Body - ' + json_dict['feature_name'] + '"\n')
            output.write('  },\n')
            output.write('  "subject": {\n')
            output.write('    "reference": "Patient/' + sample_id + '"\n')
            output.write('  },\n')
            output.write('  "performer": [\n')
            output.write('    {\n')
            output.write('      "reference": "Organization/Human Longevity, Inc.",\n')
            output.write('      "display": "Human Longevity, Inc."\n')
            output.write('    }\n')
            output.write('  ],\n')
            output.write('  "device": {\n')
            output.write('    "display": "MRI: ' + json_dict['manufacturer'] + '"\n')
            output.write('  },\n')
            output.write('  "valueQuantity": {\n')
            output.write('    "value": ' + json_dict['feature_value'] + ',\n')
            output.write('    "unit": "' + json_dict['units_of_measure'] + '",\n')
            output.write('    "system": "' + json_dict['units_of_measure_system'] + '",\n')
            output.write('    "code": "' + json_dict['units_of_measure'] + '",\n')
            output.write('    "normal_range": "' + json_dict['normal_range'] + '",\n')
            output.write('    "acquisition_date": "' + json_dict['acquisition_date'] + '",\n')
            output.write('    "patient_name": "' + json_dict['patient_name'] + '",\n')
            output.write('    "patient_age": "' + json_dict['patient_age'] + '",\n')
            output.write('    "patient_sex": "' + json_dict['patient_sex'] + '",\n')
            output.write('    "patient_id": "' + json_dict['patient_id'] + '",\n')
            output.write('    "accession_number": "' + json_dict['accession_number'] + '"\n')
            output.write('  },\n')
            output.write('  "bodySite": {\n')
            output.write('    "coding": [\n')
            output.write('      {\n')
            output.write('        "system": "' + json_dict['body_site_system'] + '",\n')
            output.write('        "code": "' + json_dict['body_site_code'] + '"\n')
            output.write('      }\n')
            output.write('    ],\n')
            output.write('    "text": "MR Whole body"\n')
            output.write('  }\n')
            output.write('}\n')

    def calculate_stats(self, processed_predictions, dcm_objs):
        '''
        Calculates or aquires the statistics from dicom tags.
        
        :param processed_predictions: The processed predictions
        :param dcm_objs: The dicom objects
        
        :return: stats dictionary
        '''
        stats = dict()

        voxel_volume = np.prod(dcm_objs[0].PixelSpacing) * dcm_objs[0].SliceThickness * .000001

        manufacturer = dcm_objs[0][0x08, 0x70].value
        patient_weight = float(dcm_objs[0][0x10, 0x1030].value)
        img2display = -1  # newly added

        stats['manufacturer'] = manufacturer
        stats['patient_weight'] = "{0:.0f}".format(patient_weight)

        if self.modality == 'MUSCLE':

            muscle_volume = len(processed_predictions[processed_predictions == self.muscle_label]) * voxel_volume

            stats['muscle_volume'] = "{0:.2f}".format(muscle_volume)
            stats['muscle_ratio'] = "{0:.2f}".format(patient_weight / muscle_volume)

            # newly added, to return the most informative coronal slice
            counter = 0
            self.logger.info("processed_predictions.shape: " + str(processed_predictions.shape))

#             for i in range(processed_predictions.shape[1]):
#                 transition = processed_predictions[:, i, :]
#                 temp = len(transition[transition == self.muscle_label])
#                 if temp > counter:
#                     img2display = i
#                     counter = temp

#             stats['img2display'] = img2display
            stats['img2display'] = 130

        elif self.modality == 'FAT':

            sat_volume = len(processed_predictions[processed_predictions == self.asat_label]) * voxel_volume
            vat_volume = len(processed_predictions[processed_predictions == self.vat_label]) * voxel_volume

            if manufacturer == 'GE MEDICAL SYSTEMS':
                tokens = dcm_objs[0][0x10, 0x21b0].value.split()
                if tokens[0] != 'HEIGHT' or tokens[2] != 'INCHES':
                    self.logger.error('Invalid dicom tag format for height: {} should be: {}'.format(
                        dcm_objs[0][0x10, 0x21b0].value, 'HEIGHT (value) INCHES'))
                    sys.exit(1)

                height_inches = int(tokens[1])
                height_meters = height_inches * 0.0254
            else:
                height_meters = float(dcm_objs[0][0x10, 0x1020].value)

            vat_index = (vat_volume / (height_meters * height_meters))
            vat_ratio = (vat_volume / (vat_volume + sat_volume)) * 100

            stats["sat_volume"] = "{0:.2f}".format(sat_volume)
            stats["vat_volume"] = "{0:.2f}".format(vat_volume)

            stats['vat_index'] = "{0:.2f}".format(vat_index)
            stats['vat_ratio'] = "{0:.2f}".format(vat_ratio)

            stats['height_meters'] = "{0:.2f}".format(height_meters)

            # newly added, to return the most informative coronal slice
            counter = 0
            self.logger.info("processed_predictions.shape: " + str(processed_predictions.shape))

#             for i in range(processed_predictions.shape[1]):
#                 transition = processed_predictions[:, i, :]
#                 temp = len(transition[transition == self.vat_label]) + len(transition[transition == self.asat_label])
#                 if temp > counter:
#                     img2display = i
#                     counter = temp

#             stats['img2display'] = img2display
            
            stats['img2display'] = 130


        else:
            msg = 'Unable to process given manufacturer and modality from inputs: {} and {}'.format(manufacturer,
                                                                                                    self.modality)
            self.logger.error(msg)
            msg = 'Valid inputs are FAT or MUSCLE modality and SIEMENS or GE MEDICAL SYSTEMS manufacturer.'
            self.logger.error(msg)
            sys.exit(1)

        return stats
            
    def slice_to_restore(self, predictions, slice_interval, origin_imgs_shape):
        block = np.zeros((predictions.shape[0], 2, origin_imgs_shape[-1]))
        restored_predictions = np.concatenate((block, predictions, block), axis=1)  
        self.logger.info(f"restored_predictions: {restored_predictions.shape}")
        head_shape = (slice_interval[0], origin_imgs_shape[1], origin_imgs_shape[2])
        foot_shape = (origin_imgs_shape[0] - slice_interval[1], origin_imgs_shape[1], origin_imgs_shape[2])
        head_array, foot_array = np.zeros(head_shape), np.zeros(foot_shape)
        complete_predicts = np.concatenate((head_array, restored_predictions, foot_array),axis=0)
        self.logger.info(f'front shape: {head_array.shape}, slice shape: {restored_predictions.shape}, behind shape: {foot_array.shape}， complete_predicts: {complete_predicts.shape}')
        return complete_predicts
        
    def resize_to_restore(self, predictions, slice_interval, origin_imgs_shape):
        resize_shape = [slice_interval[1]-slice_interval[0], origin_imgs_shape[1], origin_imgs_shape[2]]
        resize_ratio = [j/i for i, j in zip(predictions.shape, resize_shape)]
        self.logger.info(f'resize_shape: {resize_shape}, restored image, resize ratio: {resize_ratio}')
        # todo: Judge whether the prediction data has been sliced through the slicing interval. 
        # If it has been sliced, it is necessary to set the part that does not enter the model prediction to other label (0)
        if slice_interval[0] > 0 and slice_interval[1] < origin_imgs_shape[0]:
            self.logger.info('predicts is slicing')
            head_shape = (slice_interval[0], origin_imgs_shape[1], origin_imgs_shape[2])
            foot_shape = (origin_imgs_shape[0] - slice_interval[1], origin_imgs_shape[1], origin_imgs_shape[2])
            head_array, foot_array = np.zeros(head_shape), np.zeros(foot_shape)
            restored_predictions = zoom(predictions, resize_ratio, order=0)
            complete_predicts = np.concatenate((head_array, restored_predictions, foot_array),axis=0)
            self.logger.info(f'front shape: {head_array.shape}, slice shape: {restored_predictions.shape}, behind shape: {foot_array.shape}')
        else:
            self.logger.info("predicts is't slicing")
            complete_predicts = zoom(predictions, resize_ratio, order=0)
        return complete_predicts

    def resize_to_original_dims(self, predictions, origin_imgs_array, slice_interval, slice_or_resize):
        '''
        Resizes the predictions to the original dicom image sizes.
        :param predicitions: The predictions
        :param origin_imgs_array: The original image array
        :param slice_interval: predict result array is in slice interval of origin images array
        :return: resized predictions
        '''
        origin_imgs_shape = origin_imgs_array.shape
        self.logger.info(f"predictions: {predictions.shape}, origin_imgs_array shape: {origin_imgs_shape}")
        if slice_or_resize == 'slice':
            self.logger.info(f'way of restore data size is {slice_or_resize}')
            complete_predicts = self.slice_to_restore(predictions, slice_interval, origin_imgs_shape)
        elif slice_or_resize == 'resize':
            self.logger.info(f'way of restore data size is {slice_or_resize}')
            complete_predicts = self.resize_to_restore(predictions, slice_interval, origin_imgs_shape)
        else:
            raise Exception(f"The value of 'slice_or_resize' can only be 'slice' or 'resize', current argument value is {slice_or_resize}")
        self.logger.info(f"resize to origin shape, complete predicts shape is {complete_predicts.shape}")
        return complete_predicts

    def select_most_confident(self, predicted):
        '''Selects the most confident predicition.
        :param predicted: Nx256x256x2 or Nx256x256x3 dependent on modality
        :return: Nx256x256 matrix where in each position the most confident index is selected
        '''
        if self.model_version == 'torch':
            predicted = np.argmax(predicted, axis=1)
            predicted = predicted.reshape(predicted.shape[1:])
        elif self.model_version == "keras":
            predicted = np.argmax(predicted, axis=-1)
            predicted = predicted.reshape(predicted.shape[1:])
        return predicted

    def create_overlays(self, predicted, dcm_objs, stats, patient_normal_ranges):
        '''Uses the prediction to create the color overlays.  Also writes the statics text to the first axial dicom.
        
        :param predicted: The prediction
        :param dcm_objs: The original dicom image objects
        :param stats: The calculated stats.
        
        :return: The processed predictions
        '''
        processed_predictions = []

        for i in range(0, len(predicted)):
            # Assign each pixel to highest predicted probability
            original = dcm_objs[i].pixel_array
            cvimage = np.floor((original / original.max()) * 255)
            cvimage = cvimage.astype('uint8')

            output = np.array(cvimage.copy())
            output = np.stack((np.squeeze(output),) * 3, -1)

            if i == 0:  # Modify only the 1st axial image

                if self.modality == 'MUSCLE':

                    text = 'Muscle Ratio: {} Kg/L ({})'.format(stats['muscle_ratio'], patient_normal_ranges[6])

                    output = cv2.putText(output, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.25,
                                         (255, 255, 255), 1,
                                         cv2.LINE_AA)

                    text = 'Thigh Muscle Volume: {} L ({})'.format(stats['muscle_volume'], patient_normal_ranges[7])

                    output = cv2.putText(output, text, (10, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.25,
                                         (255, 255, 255), 1,
                                         cv2.LINE_AA)

                elif self.modality == 'FAT':

                    text = f"VAT Index: {stats['vat_index']} L/m2 ({patient_normal_ranges[4]})"

                    output = cv2.putText(output, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.25,
                                         (255, 255, 255), 1,
                                         cv2.LINE_AA)

                    text = f"VAT Ratio: {stats['vat_ratio']}% ({patient_normal_ranges[3]})"

                    output = cv2.putText(output, text, (10, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.25,
                                         (255, 255, 255), 1,
                                         cv2.LINE_AA)

                    text = 'VAT Volume: {} L ({})'.format(stats['vat_volume'], patient_normal_ranges[2])

                    output = cv2.putText(output, text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.25,
                                         (255, 255, 255), 1,
                                         cv2.LINE_AA)

                    text = 'ASAT Volume: {} L ({})'.format(stats['sat_volume'], patient_normal_ranges[5])

                    output = cv2.putText(output, text, (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.25,
                                         (255, 255, 255), 1,
                                         cv2.LINE_AA)

            masks = np.zeros(
                (
                    predicted[i].shape[0],
                    predicted[i].shape[1],
                    3
                ),
                dtype='uint8'
            )

            for key, value in self.colors.items():
                masks[predicted[i] == key] = value

            masks = gaussian(
                masks,
                sigma=.9,
                mode='wrap',
                multichannel=True,
                preserve_range=True
            ).astype('uint8')

            cv2.addWeighted(
                masks, self.alpha,
                output, 1 - self.alpha,
                0, masks
            )
            processed_predictions.append(masks)  # do we apply masks over images?

        return processed_predictions

    def write_3D_array2dcm(self, array3D, sample_dicom_path, outputdir, voxel_size, resolution=[0.25, 0.25, 0.6]):
        """
        Writes a 3D array of data to a dicom series. Future versions could add flexiblility. However, this version expects a coronal 512 x 512 x 512 input and uses a saggital image for the reference.
        
        :param array3D: (numpy array) 3D array of predicition 256x256x256
        :param sample_dicom_path: (str) path to sample dicoms which include the correct tag information (For example the dicoms used to generate ROIs would be useful references for an overlay outputing the ROIs)
        :param outputdir: (str) output directory
        :param voxel_volume: (float) voxel volume
        :param resolution: (list) resolution of array3D [x, y, z] in mm (e.g. use [1.0, 1.0, 1.2] for 128x128x128 or divid by the appropriate factor)
        :return:  None
        """

        orientations = ['axial', 'sagittal', 'coronal']
        omit_tags = ['0028|1052', '0028|1053', '0020|1041', '0018|0050', '0019|1018', '0019|1019', '0019|101a', \
                     '0019|101b', '0019|101e', '0020|1041', '0027|1041', '0027|1060', '0027|1061', '0027|1040']

        array3D = np.array(array3D)
        coronal_factor_calc = list()  # newly added

        for loc in orientations:

            o_dict = {}

            if self.modality == 'MUSCLE':
                o_dict["coronal"] = ["11054", "Cor HLI Quantitative Muscle", map(str, [1, 0, 0, 0, 0, -1])]
                o_dict["axial"] = ["11056", "Ax HLI Quantitative Muscle", map(str, [1, 0, 0, 0, 1, 0])]
                o_dict["sagittal"] = ["11058", "Sag HLI Quantitative Muscle", map(str, [0, 1, 0, 0, 0, -1])]
            else:  # FAT
                o_dict["coronal"] = ["11053", "Cor HLI Quantitative Fat", map(str, [1, 0, 0, 0, 0, -1])]
                o_dict["axial"] = ["11055", "Ax HLI Quantitative Fat", map(str, [1, 0, 0, 0, 1, 0])]
                o_dict["sagittal"] = ["11057", "Sag HLI Quantitative Fat", map(str, [0, 1, 0, 0, 0, -1])]

            arry = np.copy(array3D)

            new_img = sitk.GetImageFromArray(arry)

            z_count = 0

            try:
                sample_dicom = [pydicom.dcmread(
                    sample_dicom_path + '/' + s, force=True) for s in os.listdir(sample_dicom_path)
                    if s.endswith('.dcm')
                ]
                self.logger.info(f"sample_dicom_path: {sample_dicom_path}, sample_dicom number: {len(sample_dicom)}")
            except Exception as e:
                self.logger.error("pydicom.dcmread exception " + str(e))
                sys.exit(1)

            sample_dicom.sort(key=lambda x: int(x.SliceLocation), reverse=True)
            original_pixel_spacing = sample_dicom[0].PixelSpacing
            original_slice_thickness = int(sample_dicom[0].SliceThickness)
            coronal_factor_calc = [original_pixel_spacing[1], original_slice_thickness]  # newly added
            # self.logger.info("original_slice_thickness: " + str(original_slice_thickness))

            # Write the 3D image as a series
            # IMPORTANT: There are many DICOM tags that need to be updated when you modify an
            #            original image. This is a delicate opration and requires knowlege of
            #            the DICOM standard. This example only modifies some. For a more complete
            #            list of tags that need to be modified see:
            #                           http://gdcm.sourceforge.net/wiki/index.php/Writing_DICOM
            #            If it is critical for your work to generate valid DICOM files,
            #            It is recommended to use David Clunie's Dicom3tools to validate the files
            #                           (http://www.dclunie.com/dicom3tools.html).

            writer = sitk.ImageFileWriter()

            # Use the study/series/frame of reference information given in the meta-data
            # dictionary and not the automatically generated information from the file IO

            writer.KeepOriginalImageUIDOn()

            mod_time = time.strftime("%H%M%S")
            mod_date = time.strftime("%Y%m%d")

            # Copy some of the tags and add the relevant tags indicating the change.
            # For the series instance UID (0020|000e), each of the components is a number, cannot start
            # with zero, and separated by a '.' We create a unique series ID using the date and time.
            # tags of interest:

            series_tag_values = [("0028|1050", "127.0"),  # WindowCenter
                                 ("0028|1051", "255.0"),  # WindowLength
                                 ("0008|0008", "DERIVED\\SECONDARY"),  # Image Type
                                 ("0008|0031", mod_time),  # Series Time
                                 ("0008|0021", mod_date)]  # Series Date
            dim_size = None
            if loc == 'coronal':
                dim_size = array3D.shape[1]
            elif loc == 'axial':
                dim_size = array3D.shape[0]
            else:
                dim_size = array3D.shape[2]
            for i in range(dim_size):

                if loc == "coronal":
                    image_slice = new_img[:, i, :]
                    image_slice.SetSpacing([original_pixel_spacing[1], original_slice_thickness])
                elif loc == "axial":
                    image_slice = new_img[:, :, i]
                    image_slice.SetSpacing(original_pixel_spacing)
                else:
                    image_slice = new_img[i, :, :]
                    image_slice.SetSpacing([original_pixel_spacing[0], original_slice_thickness])

                reader = sitk.ImageFileReader()

                reader.SetFileName(os.path.join(sample_dicom_path, os.listdir(sample_dicom_path)[0]))
                reader.LoadPrivateTagsOn()  # LOOKHERE

                reader.ReadImageInformation()

                for k in reader.GetMetaDataKeys():
                    null_tag = False

                    for tag in omit_tags:
                        if k == tag:
                            image_slice.SetMetaData(k, "")
                            null_tag = True
                            break

                    if not null_tag:
                        if k == '0028|0030': continue  # Might over-write SetSpacing?
                        v = reader.GetMetaData(k)
                        if type(v) == str:
                            v = v.encode('utf-8', 'ignore').decode('utf-8')
                        image_slice.SetMetaData(k, v)

                # Tags shared by the series.
                for tag, value in series_tag_values:
                    image_slice.SetMetaData(tag, value)

                # dummy_data is used to set the 0020|0032 tag in dicom metadata, which is "ImagePositionPatient", - it should be set to 1, 1, 1
                dummy_data = map(str, [1, 1, 1])

                copy_dict = copy.deepcopy(o_dict)

                image_slice.SetMetaData("0020|0013", str(i + 1))  # Instance Number
                image_slice.SetMetaData("0020|0011", copy_dict[loc][0])  # Series Number
                image_slice.SetMetaData("0008|103e", copy_dict[loc][1])  # Series Description

                # Series Instance UID
                image_slice.SetMetaData("0020|000E",
                                        "1.2.826.0.1.3680043.2.1125." + mod_date + ".2" + copy_dict[loc][
                                            0] + mod_time)  # Series description

                image_slice.SetMetaData("0020|0037", '\\'.join([*map(str, copy_dict[loc][2])]))  # Image orientation
                image_slice.SetMetaData("0020|0032", '\\'.join([*map(str, dummy_data)]))  # Image position

                image_slice.SetMetaData("0018|0088", "")

                image_slice.SetMetaData("0008|0012", time.strftime("%Y%m%d"))  # Instance Creation Date
                image_slice.SetMetaData("0008|0013", time.strftime("%H%M%S"))  # Instance Creation Time

                # Note: This has to be 64bit
                image_slice.SetMetaData("0008|0018", "1.3.6.1.4.1.9590.100.1.2."
                                        + mod_date + copy_dict[loc][0]
                                        + mod_time + str(i))  # SOP Instance UID
                image_slice.SetMetaData("0028|0107", str(255))  # Largest Image Pixel Value

                # Write to the output directory and add the extension dcm, to force writing in DICOM format.
                images_dir = os.path.join(outputdir, 'images')
                if not os.path.isdir(images_dir):
                    os.makedirs(images_dir)

                writer.SetFileName(os.path.join(images_dir, loc + '-' + str(i) + '.dcm'))
                writer.Execute(image_slice)

        ##### COMMENT BELOW OUT AND TEST.  I SUSPECT WE DO NOT NEED THIS ACTIVITY

        # Re-read the series
        # Read the original series. First obtain the series file names using the
        # image series reader.

        images_dir = os.path.join(outputdir, 'images')
        series_IDs = sitk.ImageSeriesReader.GetGDCMSeriesIDs(images_dir)

        if not series_IDs:
            raise Exception("Given directory \"" + images_dir +
                            "\" does not contain a DICOM series.")

        series_file_names = sitk.ImageSeriesReader.GetGDCMSeriesFileNames(
            images_dir, series_IDs[0])

        series_reader = sitk.ImageSeriesReader()
        series_reader.SetFileNames(series_file_names)

        # Configure the reader to load all of the DICOM tags (public+private):
        # By default tags are not loaded (saves time).
        # By default if tags are loaded, the private tags are not loaded.
        # We explicitly configure the reader to load tags, including the
        # private ones.

        series_reader.LoadPrivateTagsOn()

        image3D = series_reader.Execute()

        # self.logger.info(image3D.GetSpacing())
        # self.logger.info("vs")
        # self.logger.info("new_img.GetSpacing()")

        return coronal_factor_calc
