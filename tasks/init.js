
const gulp = require('gulp');
const shell = require('gulp-shell');
const hli = require('gulp-hli');

gulp.task('init', ['check_if_released', 'init_ecr', 'init_venv'], hli.yo.checkUpdate)

gulp.task('check_if_released', function() {
  return gulp.src('')
    .pipe(shell(
`
set -e
BIX_TOOL=$(jq -r .\\"generator-bix-tool\\".project .yo-rc.json)
echo "BIX Tool Name: $BIX_TOOL"

BIX_TOOL_VERSION=$(jq -r .version package.json)
echo "BIX Tool Version: $BIX_TOOL_VERSION"

ECR_REPO=release/devops/devops-teamcity/$BIX_TOOL
REG_ID=205134639408

if aws ecr describe-repositories --registry-id=$REG_ID --repository-names=$ECR_REPO --no-include-email --region=us-west-2 &>/dev/null ; then
  echo "$ECR_REPO already exists. Continuing build..."
  if aws ecr describe-images --registry-id=$REG_ID --repository-name=$ECR_REPO --image-ids=imageTag=$BIX_TOOL_VERSION &>/dev/null ; then
    echo "$ECR_REPO:$BIX_TOOL_VERSION has already been released yet. Please BUMP THE VERSION!!\n"
    exit 1
  else
    echo "$ECR_REPO hasn't been released. Continuing build..."
  fi
else
  echo "$ECR_REPO hasn't been released. Continuing build..."
fi

echo "check credentials if have apollo8_bj_dev"
if cat ~/.aws/credentials | grep apollo8_bj_dev &>/dev/null ; then
    echo "apollo8_bj_dev credential has alread exist"
else
    echo "set apollo8_bj_dev's AKSK into ~/.aws/credentials..."
cat >> ~/.aws/credentials << EOF
[apollo8_bj_dev]
aws_access_key_id = $apollo8_bj_dev_ak
aws_secret_access_key = $apollo8_bj_dev_sk
EOF
fi
#$(aws ecr get-login --region cn-northwest-1 --registry-id 436227880023 --no-include-email --profile apollo8_bj_dev)
aws ecr get-login-password --region cn-northwest-1 --profile apollo8_bj_dev | docker login --username AWS --password-stdin 436227880023.dkr.ecr.cn-northwest-1.amazonaws.com.cn
echo "Cersion from package.json: $BIX_TOOL_VERSION"
ECR_REPO_CN=release/devops/devops-teamcity/$BIX_TOOL
REG_ID_CN=436227880023
if aws ecr describe-repositories --registry-id=$REG_ID_CN --repository-names=$ECR_REPO_CN --region=cn-northwest-1 --profile apollo8_bj_dev&>/dev/null ; then
    echo "$ECR_REPO_CN already exists. Continuing build..."
    if aws ecr describe-images --registry-id=$REG_ID_CN --repository-name=$ECR_REPO_CN --image-ids=imageTag=$BIX_TOOL_VERSION &>/dev/null ; then
        echo "$ECR_REPO_CN:$BIX_TOOL_VERSION has already been released. Please BUMP THE VERSION!!\n"
        exit 1
    else
        echo "$ECR_REPO_CN hasn't been released. Continuing build..."
    fi
else
    echo "$ECR_REPO_CN hasn't been released. Continuing build..."
fi
`));
});

gulp.task('init_ecr',['check_if_released'], function() {
  return gulp.src('')
    .pipe(shell(
`
set -e
#$(aws ecr get-login --region us-west-2 --registry-id 205134639408 --no-include-email)
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 205134639408.dkr.ecr.us-west-2.amazonaws.com
docker --version
`));
});

gulp.task('init_venv', ['check_if_released'],function() {
  return gulp.src('')
    .pipe(shell(
`
set -e
virtualenv venv
source venv/bin/activate
if [ -e ~/.pip/pip.conf ]
then
  echo "Copying pip config"
  cp -R ~/.pip/pip.conf $VIRTUAL_ENV/pip.conf
fi
pip install dpl
`));
});

