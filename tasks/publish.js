const gulp = require('gulp');
const shell = require('gulp-shell')

gulp.task('publish_snapshot', function() {
  return gulp.src('.')
    .pipe(shell(
`
set -e
BIX_TOOL=$(jq -r .\\"generator-bix-tool\\".project .yo-rc.json)
echo "BIX Tool Name: $BIX_TOOL"

BIX_TOOL_VERSION=$(jq -r .version package.json)
echo "BIX Tool Version: $BIX_TOOL_VERSION"

#ECR_PREFIX=sandbox/devops/devops-teamcity
#ECR_REPO=$ECR_PREFIX/$BIX_TOOL
#ECR_REPO_PREFIX=205134639408.dkr.ecr.us-west-2.amazonaws.com/$ECR_PREFIX
#BIX_TOOL_REPO=205134639408.dkr.ecr.us-west-2.amazonaws.com/$ECR_PREFIX/$BIX_TOOL:$BIX_TOOL_VERSION
#DPL_ENV=dev

# Create Repo
#echo "Creating ECR Repository if necessary"
#aws-switch master-teamcity-devops
#$(aws ecr get-login --region us-west-2 --registry-id 205134639408 --no-include-email --profile master-teamcity-devops)
#aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 205134639408.dkr.ecr.us-west-2.amazonaws.com
#if aws ecr create-repository --repository-name $ECR_REPO --profile master-teamcity-devops --region us-west-2 &>/dev/null ; then
#  echo "Repository created"
#else
#  echo "Repository already exists"
#fi

# Push Docker Image
#echo "Pushing Docker image: $BIX_TOOL_REPO"
#docker tag $BIX_TOOL $BIX_TOOL_REPO
#docker push $BIX_TOOL_REPO

#-------CN Site
ECR_PREFIX_CN=sandbox/devops/devops-teamcity
ECR_REPO_CN=$ECR_PREFIX_CN/$BIX_TOOL
ECR_REPO_PREFIX_CN=436227880023.dkr.ecr.cn-northwest-1.amazonaws.com.cn/$ECR_PREFIX_CN
BIX_TOOL_REPO_CN=436227880023.dkr.ecr.cn-northwest-1.amazonaws.com.cn/$ECR_PREFIX_CN/$BIX_TOOL:$BIX_TOOL_VERSION
#$(aws ecr get-login --region cn-northwest-1 --registry-id 436227880023 --no-include-email --profile apollo8_bj_dev)
aws ecr get-login-password --region cn-northwest-1 --profile apollo8_bj_dev | docker login --username AWS --password-stdin 436227880023.dkr.ecr.cn-northwest-1.amazonaws.com.cn
if aws ecr create-repository --repository-name $ECR_REPO_CN --region cn-northwest-1 --profile apollo8_bj_dev&>/dev/null ; then
    echo "CN Repository created"
    touch ecr-policy.json
    cat >> ./ecr-policy.json << EOF
{
    "Version": "2008-10-17",
    "Statement": [
        {
        "Sid": "allow-bj-prod-cn",
        "Effect": "Allow",
        "Principal": {
            "AWS": "arn:aws-cn:iam::585145728788:root"
        },
        "Action": [
            "ecr:BatchGetImage",
            "ecr:GetDownloadUrlForLayer"
        ]
        }
    ]
}
EOF
    aws ecr set-repository-policy  --repository-name $ECR_REPO_CN  --policy-text file://ecr-policy.json --region cn-northwest-1 --profile apollo8_bj_dev
    echo "Set CN Repository policy to allow bj-prod use"
else
    echo "CN Repository already exists"
fi
# Push Docker Image To CN
echo "Pushing Docker image: $BIX_TOOL_REPO_CN"
docker tag $BIX_TOOL $BIX_TOOL_REPO_CN
docker push $BIX_TOOL_REPO_CN


# Modifying tasks.json
#echo "Modifying and Registering Tasks files"
#source venv/bin/activate
#for file in dpl/task/*
#do
#  echo "Modifying task: $file"
#  jq --arg BIX_TOOL_REPO "$BIX_TOOL_REPO" --arg BIX_TOOL_VERSION "$BIX_TOOL_VERSION" '.task.image = $BIX_TOOL_REPO | .task.version = $BIX_TOOL_VERSION' $file > $file.temp
#  mv $file.temp $file
#  echo "Registering task to $DPL_ENV: $file"
#  dpl task register --force --task-file=$file --env=$DPL_ENV
#done

# Register internal pipelines
#echo "Registering Internal Pipelines"
#for directory in dpl/pipelines/*
#do
#  directory_name=$(basename $directory)
#  echo "Modifying steps.json: $directory/steps.json"
#  jq --arg BIX_TOOL_VERSION "$BIX_TOOL_VERSION" '.steps[].taskVersion = $BIX_TOOL_VERSION' $directory/steps.json > $directory/steps.json.temp
#  mv $directory/steps.json.temp $directory/steps.json
#  dpl pipeline register --pipeline-name=$directory_name --env=$DPL_ENV --content=$directory
#done

# Run Internal BIX Tool DPL Tests
#echo "Run Internal $BIX_TOOL DPL Tests"
#cd docker
#make REPO=$ECR_REPO_PREFIX DPL_ENV=$DPL_ENV DPL_REPO_BUCKET=hli-dplrepo-dev-pdx DPL_CACHE_BUCKET=hli-dpl-dev-pdx dpl_test_team_city
`));
});

gulp.task('publish_release', function() {
  return gulp.src('.')
    .pipe(shell(
`
set -e
BIX_TOOL=$(jq -r .\\"generator-bix-tool\\".project .yo-rc.json)
echo "BIX Tool Name: $BIX_TOOL"

BIX_TOOL_VERSION=$(jq -r .version package.json)
echo "BIX Tool Version: $BIX_TOOL_VERSION"

ECR_PREFIX=release/devops/devops-teamcity
ECR_REPO=$ECR_PREFIX/$BIX_TOOL
BIX_TOOL_REPO=205134639408.dkr.ecr.us-west-2.amazonaws.com/$ECR_REPO:$BIX_TOOL_VERSION
DPL_ENV_DEV=dev
DPL_ENV_TEST=test
DPL_ENV_STAGE=stage
DPL_ENV_PROD=prod

# Create Repo
echo "Creating ECR Repository if necessary"
aws-switch master-teamcity-devops
#$(aws ecr get-login --region us-west-2 --registry-id 205134639408 --no-include-email --profile master-teamcity-devops)
aws ecr get-login-password --region us-west-2 --profile master-teamcity-devops | docker login --username AWS --password-stdin 205134639408.dkr.ecr.us-west-2.amazonaws.com 
if aws ecr create-repository --repository-name $ECR_REPO --profile master-teamcity-devops --region us-west-2 &>/dev/null
then
  echo "Repository created"
else
  echo "Repository already exists"
fi

# Push Docker Image
echo "Pushing Docker image: $BIX_TOOL_REPO"
docker tag $BIX_TOOL $BIX_TOOL_REPO
if ! (aws ecr describe-images --repository-name $ECR_REPO --registry-id 205134639408 --image-ids imageTag=$BIX_TOOL_VERSION)
then
  docker push $BIX_TOOL_REPO
else
  echo "Docker image $BIX_TOOL_REPO already exists in ECR"
  exit 1
fi

#-------CN Site
ECR_PREFIX_CN=release/devops/devops-teamcity
ECR_REPO_CN=$ECR_PREFIX/$BIX_TOOL
ECR_REPO_PREFIX_CN=436227880023.dkr.ecr.cn-northwest-1.amazonaws.com.cn/$ECR_PREFIX
BIX_TOOL_REPO_CN=436227880023.dkr.ecr.cn-northwest-1.amazonaws.com.cn/$ECR_PREFIX/$BIX_TOOL:$BIX_TOOL_VERSION
#$(aws ecr get-login --region cn-northwest-1 --registry-id 436227880023 --no-include-email --profile apollo8_bj_dev)
aws ecr get-login-password --region cn-northwest-1 --profile apollo8_bj_dev | docker login --username AWS --password-stdin 436227880023.dkr.ecr.cn-northwest-1.amazonaws.com.cn
if aws ecr create-repository --repository-name $ECR_REPO_CN --region cn-northwest-1 --profile apollo8_bj_dev&>/dev/null ; then
    echo "CN Repository created"
    touch ecr-policy.json
    cat >> ./ecr-policy.json << EOF
{
    "Version": "2008-10-17",
    "Statement": [
        {
        "Sid": "allow-bj-prod-cn",
        "Effect": "Allow",
        "Principal": {
            "AWS": "arn:aws-cn:iam::585145728788:root"
        },
        "Action": [
            "ecr:BatchGetImage",
            "ecr:GetDownloadUrlForLayer"
        ]
        }
    ]
}
EOF
    aws ecr set-repository-policy  --repository-name $ECR_REPO_CN  --policy-text file://ecr-policy.json --region cn-northwest-1 --profile apollo8_bj_dev
    echo "Set CN Repository policy to allow bj-prod use"
else
    echo "CN Repository already exists"
fi
# Push Docker Image To CN
echo "Pushing Docker image: $BIX_TOOL_REPO_CN"
docker tag $BIX_TOOL $BIX_TOOL_REPO_CN
docker tag $BIX_TOOL $BIX_TOOL_REPO_CN:latest
docker push $BIX_TOOL_REPO_CN
docker push $BIX_TOOL_REPO_CN:latest

# Modifying tasks.json
#echo "Modifying and Registering Tasks files"
#source venv/bin/activate
#for file in dpl/task/*
#do
#  echo "Modifying task: $file"
#  jq --arg BIX_TOOL_REPO "$BIX_TOOL_REPO" --arg BIX_TOOL_VERSION $BIX_TOOL_VERSION '.task.image = $BIX_TOOL_REPO | .task.version = $BIX_TOOL_VERSION' $file > $file.temp
#  mv $file.temp $file

#  echo "Registering task to $DPL_ENV_DEV: $file"
#  dpl task register --force --task-file=$file --env=$DPL_ENV_DEV

#  echo "Registering task to $DPL_ENV_TEST: $file"
#  dpl task register --task-file=$file --env=$DPL_ENV_TEST

#  echo "Registering task to $DPL_ENV_STAGE: $file"
#  aws-switch prod-teamcity-devops
#  export AWS_DEFAULT_PROFILE="prod-teamcity-devops"
#  export AWS_PROFILE="prod-teamcity-devops"
#  export AWS_DEFAULT_REGION="us-west-2"
#  dpl task register --task-file=$file --env=$DPL_ENV_STAGE

#  echo "Registering task to $DPL_ENV_PROD: $file"
#  dpl task register --task-file=$file --env=$DPL_ENV_PROD
#done

GIT_REPO=$(git config --get remote.origin.url | sed "s/\\:/\\//g" | sed "s/\\git@/https:\\/\\/$GIT_USER:$GIT_TOKEN@/g")

git config user.email "$GIT_USER@humanlongevity.com"
git config user.name "$GIT_USER"

git tag $BIX_TOOL_VERSION
git push $GIT_REPO $BIX_TOOL_VERSION

`));
});
