# this requires jq to be installed (sudo apt-get install jq) 
BIX_TOOL = $(shell jq -r .\"generator-bix-tool\".project ../.yo-rc.json)
GITHUB_REPO = $(shell jq -r .\"generator-bix-tool\".repo ../.yo-rc.json)

DEV_USER = $(shell whoami)

# change the DEV_USER to your own sandbox environment when working on this container
DEV_REPO = 205134639408.dkr.ecr.us-west-2.amazonaws.com/sandbox/dev/$(GITHUB_REPO)

# change the VERSION to the desired version
VERSION = $(shell jq -r .version ../package.json)

CWD = $(shell pwd)
PARDIR = $(shell dirname $(CWD))
DPL_ENV = dev

# decrypt Artifactory API key to pass to Dockerfile
DEV_KEY=$(shell python decrypt.py key.kms)

DOCKER_RUN_LOCAL = docker run \
                   -e AWS_DEFAULT_REGION=us-west-2 \
                   -e AWS_REGION=us-west-2 \
                   -e AWS_ASSUME_ROLE_TTL=${AWS_ASSUME_ROLE_TTL} \
                   -e AWS_SESSION_TTL=${AWS_SESSION_TTL} \
                   -e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} \
                   -e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
                   -e AWS_SESSION_TOKEN=${AWS_SESSION_TOKEN} \
                   -e AWS_SECURITY_TOKEN=${AWS_SECURITY_TOKEN} \
                   -e jaw_issue_handler_lambda=arn:aws:lambda:us-west-2:136074505599:function:jaw-issue-handler-dev


### Prod commands should never be called manually.  These will be called by TeamCity when automating build/release ###
build_team_city:
	docker build --no-cache=true -f Dockerfile --build-arg USER=$(USER) --build-arg KEY=$(KEY) -t $(REPO)/$(BIX_TOOL):$(VERSION) ..

push_team_city:
	docker push $(REPO)/$(BIX_TOOL):$(VERSION)

unit_test_team_city:
	docker run -v $(CWD):/scratch --entrypoint py.test $(REPO)/$(BIX_TOOL):$(VERSION) --cov=/opt/project/src --cov-report term-missing --cov-report=xml:/scratch/unit_tests_cov_report.xml --cov-report=html:/scratch/unit_tests_cov_report.html --json /scratch/unit_tests_results.json --junitxml=/scratch/unit_tests_results.xml --html=/scratch/unit_tests_results.html /opt/project/tests/unit_tests --verbose

integration_test_team_city:
	docker run -v $(CWD):/scratch --entrypoint py.test $(REPO)/$(BIX_TOOL):$(VERSION) --json /scratch/integration_tests_results.json --junitxml=/scratch/integration_tests_results.xml --html=/scratch/integration_tests_results.html /opt/project/tests/integration_tests --verbose

dpl_test_team_city:
	docker run -v $(CWD):/scratch --entrypoint py.test $(REPO)/$(BIX_TOOL):$(VERSION) --json /scratch/dpl_tests_results.json --junitxml=/scratch/dpl_test_results.xml --html=/scratch/dpl_tests_results.html /opt/project/tests/dpl_tests --dpl_env $(DPL_ENV) --dpl_repo_bucket $(DPL_REPO_BUCKET) --dpl_cache_bucket $(DPL_CACHE_BUCKET)


build_docs_team_city:
	docker run -v $(PARDIR)/docs:/opt/project/docs -e CONFLUENCE_USER=$(CONFLUENCE_USER) -e CONFLUENCE_PASS=$(CONFLUENCE_PASS) --workdir /opt/project/docs --entrypoint sh $(REPO)/$(BIX_TOOL):$(VERSION) /opt/project/docs/build_docs.sh $(VERSION)


### Call these to test things locally ###
run_interactive: build_dev
	docker run -it --entrypoint /bin/bash -v $(CWD):/scratch \
	$(DEV_REPO)/$(BIX_TOOL):$(VERSION)

build_docs: build_dev
	$(DOCKER_RUN_LOCAL) \
    -v $(PARDIR)/docs:/opt/project/docs --workdir /opt/project/docs --entrypoint sh $(DEV_REPO)/$(BIX_TOOL):$(VERSION) /opt/project/docs/build_docs.sh $(VERSION)

build_dev:
	docker build -f Dockerfile --build-arg USER=svc_bix --build-arg KEY=$(DEV_KEY) -t $(DEV_REPO)/$(BIX_TOOL):$(VERSION) ..

push_dev: build_dev
	docker push $(DEV_REPO)/$(BIX_TOOL):$(VERSION)

unit_test_dev: build_dev
	sudo rm -rf unit_tests
	$(DOCKER_RUN_LOCAL) \
	-v $(CWD)/unit_tests:/scratch \
	--entrypoint py.test \
	$(DEV_REPO)/$(BIX_TOOL):$(VERSION) --cov=/opt/project/src --cov-report term-missing /opt/project/tests/unit_tests
	
integration_test_dev_local: build_dev
	sudo rm -rf integration_tests
	$(DOCKER_RUN_LOCAL) \
	-v $(CWD)/integration_tests:/scratch \
	--entrypoint py.test \
	$(DEV_REPO)/$(BIX_TOOL):$(VERSION) --cov=/opt/project/src --cov-report term-missing /opt/project/tests/integration_tests
    
# to test on aws
integration_test_dev_aws: push_dev
	docker run \
	-v /scratch:/scratch \
	-e jaw_issue_handler_lambda=arn:aws:lambda:us-west-2:136074505599:function:jaw-issue-handler-dev \
	--entrypoint py.test \
	$(DEV_REPO)/$(BIX_TOOL):$(VERSION) /opt/project/tests/integration_tests

dpl_register_dev: push_dev
	python ../dpl/register_all.py --task_dir ../dpl/task --pipeline_dir ../dpl/pipelines --version $(VERSION)

dpl_dev: dpl_register_dev
	#ensure pipeline registration completes before kicking off a run (this is done internally in the test_dpl.py)
	sleep 15
	$(DOCKER_RUN_LOCAL) \
	-v $(CWD)/dpl_tests:/scratch \
	--entrypoint py.test \
	$(DEV_REPO)/$(BIX_TOOL):$(VERSION) /opt/project/tests/dpl_tests --dpl_env dev --dpl_repo_bucket hli-dplrepo-dev-pdx --dpl_cache_bucket hli-dpl-dev-pdx --username $(DEV_USER)


