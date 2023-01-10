FROM 205134639408.dkr.ecr.us-west-2.amazonaws.com/release/devops/devops-teamcity/ubuntu:18.4.0
# UNCOMMENT BELOW TO USE SPARK BASE IMAGE
# FROM 205134639408.dkr.ecr.us-west-2.amazonaws.com/release/devops/devops-teamcity/spark:2.4.2.1

ARG KEY
ENV KEY=$KEY
ARG USER
ENV USER=$USER

RUN rm /etc/apt/sources.list \
  && echo "deb https://$USER:$KEY@artifactory.hli.io/artifactory/ubuntu-remote bionic main restricted" >> /etc/apt/sources.list \
  && echo "deb https://$USER:$KEY@artifactory.hli.io/artifactory/ubuntu-remote bionic-updates main restricted" >> /etc/apt/sources.list \
  && echo "deb https://$USER:$KEY@artifactory.hli.io/artifactory/ubuntu-remote bionic universe" >> /etc/apt/sources.list \
  && echo "deb https://$USER:$KEY@artifactory.hli.io/artifactory/ubuntu-remote bionic-updates universe" >> /etc/apt/sources.list \
  && echo "deb https://$USER:$KEY@artifactory.hli.io/artifactory/ubuntu-remote bionic-backports main restricted universe multiverse" >> /etc/apt/sources.list \
  && echo "deb https://$USER:$KEY@artifactory.hli.io/artifactory/ubuntu-remote-security bionic-security main restricted" >> /etc/apt/sources.list \
  && echo "deb https://$USER:$KEY@artifactory.hli.io/artifactory/ubuntu-remote-security bionic-security universe" >> /etc/apt/sources.list \
  && echo "deb https://$USER:$KEY@artifactory.hli.io/artifactory/ubuntu-remote-security bionic-security multiverse" >> /etc/apt/sources.list

# SET ENVIRONMENT VARIABLE FOR PIP HLI ARTIFACTORY REPO
ENV PIP_EXTRA_INDEX_URL="https://$USER:$KEY@artifactory.hli.io/artifactory/api/pypi/python-virtual-release/simple"

# ADD ADDITIONAL PYTHON PACKAGES TO REQUIREMENTS.TXT
COPY ./docker/requirements.txt /opt/requirements.txt

# PYTHON VERSION MUST BE 3.6
RUN pip3 install --upgrade pip
RUN pip3 install -r /opt/requirements.txt

# MAKE LOGS DIR
RUN mkdir /clogs

# COPY FILES TO DOCKER CONTAINER
COPY ./src /opt/project/src
COPY ./tests /opt/project/tests
COPY ./docs /opt/project/docs
COPY ./docker /opt/project/docker
COPY ./dpl /opt/project/dpl
COPY ./train /opt/project/train

# SET WORKING DIR
WORKDIR /opt/project/src

# ADD STUFF TO PYTHON PATH
ENV PYTHONPATH /opt:/:$PYTHONPATH
ENV PYTHONPATH /opt/project/src:/opt/project/test:$PYTHONPATH

#For DPL
ENV AWS_DEFAULT_REGION="us-west-2"

# WHOLE BODY COMPOSITION
RUN mkdir working 

# DEFINE ENTRYPOINT
# CHANGE TO CORRECT ENTRYPOINT SCRIPT NAME IN SRC FOLDER
ENTRYPOINT ["python3", "main.py"]
