const gulp = require('gulp');
const shell = require('gulp-shell')

gulp.task('build', ['build_image'], function() {
});

gulp.task('build_image', function() {
  return gulp.src('')
    .pipe(shell(
`
set -e
BIX_TOOL=$(jq -r .\\"generator-bix-tool\\".project .yo-rc.json)
echo "BIX Tool Name: $BIX_TOOL"
docker build --no-cache=true -f docker/Dockerfile --build-arg USER=$ARTIFACTORY_USERNAME --build-arg KEY=$ARTIFACTORY_APIKEY -t $BIX_TOOL .
`));
});
