# execute on linux: fat
nohup python3 /mnt/sdma/100plus_algorithm_project/hli-tool-whole-body-composition/src/main.py \
--sample_id HDAT18B5B27F \
--working_dir /mnt/sdma/data/hli-tool-whole-body-composition-dev/working/ \
--logging_dir /mnt/sdma/data/hli-tool-whole-body-composition-dev/logging/ \
--output_dir /mnt/sdma/data/hli-tool-whole-body-composition-dev/output/ \
--model_file s3://apollo8-datalake-nv-bj-prod-cn-northwest-1-prod/whole_body_composition/new_version_models/cpu_epoch51_trainloss_0.070_validacc_0.942.pth \
--input_dir s3://apollo8-datalake-nv-bj-prod-cn-northwest-1-prod/external/receive/P1/S3/imaging/HSUB21337B55/HORD05157BB1/fat/ \
--modality FAT \
--range_file s3://apollo8-datalake-nv-bj-dev-cn-northwest-1-dev/whole_body_composition/AMRA_NORMAL_RANGES.xlsx >log.txt 2>&1 &


# execute on linux: water
nohup python3 /mnt/sdma/100plus_algorithm_project/hli-tool-whole-body-composition/src/main.py \
--sample_id HDAT18B5B27F \
--working_dir /mnt/sdma/data/hli-tool-whole-body-composition-dev/working/ \
--logging_dir /mnt/sdma/data/hli-tool-whole-body-composition-dev/logging/ \
--output_dir /mnt/sdma/data/hli-tool-whole-body-composition-dev/output/ \
--model_file s3://apollo8-datalake-nv-bj-prod-cn-northwest-1-prod/whole_body_composition/new_version_models/cpu_epoch35_trainloss_0.037_validacc_0.961.pth \
--input_dir s3://apollo8-datalake-nv-bj-prod-cn-northwest-1-prod/external/receive/P1/S3/imaging/HSUB21337B55/HORD05157BB1/water/ \
--modality MUSCLE \
--range_file s3://apollo8-datalake-nv-bj-dev-cn-northwest-1-dev/whole_body_composition/AMRA_NORMAL_RANGES.xlsx >log.txt 2>&1 &


# execute through docker image
docker run hli-tool-whole-body-composition_torch_update:2.0.0 \
--working_dir /tmp/working \
--logging_dir /tmp/logging \
--output_dir /tmp \
--range_file s3://apollo8-datalake-nv-bj-prod-cn-northwest-1-prod/whole_body_composition/AMRA_NORMAL_RANGES.xlsx \
--sample_id HDAT2AB21BEF \
--input_dir s3://apollo8-datalake-nv-bj-prod-cn-northwest-1-prod/external/receive/P1/S3/imaging/HSUB59EED7D9/HORD4B2EEDE2/fat/ \
--modality FAT \
--model_file s3://apollo8-datalake-nv-bj-prod-cn-northwest-1-prod/whole_body_composition/new_version_models/cpu_epoch51_trainloss_0.070_validacc_0.942.pth

# execute test
docker run -it --entrypoint py.test hli-tool-whole-body-composition_torch_update:2.0.0 /opt/project/tests/unit_tests 