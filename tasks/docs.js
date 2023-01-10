const gulp = require('gulp');
const shell = require('gulp-shell')

gulp.task('docs', function() {
  var config = require('../package.json')
  return gulp.src('')
    .pipe(shell(
    
`
set -e
BIX_TOOL=$(jq -r .\\"generator-bix-tool\\".project .yo-rc.json)

#$(aws ecr get-login --region us-west-2 --registry-id 205134639408 --no-include-email)
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 205134639408.dkr.ecr.us-west-2.amazonaws.com

docker run -v $(pwd)/docs:/opt/project/docs --workdir /opt/project/docs --entrypoint sh $BIX_TOOL /opt/project/docs/build_docs.sh ${config.version}

`));
});

