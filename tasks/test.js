const gulp = require('gulp');
const shell = require('gulp-shell')

gulp.task('test', function() {
  return gulp.src('')
    .pipe(shell(
`
set -e
BIX_TOOL=$(jq -r .\\"generator-bix-tool\\".project .yo-rc.json)

rm -rf $(pwd)/tests
mkdir $(pwd)/tests
mkdir $(pwd)/tests/results
results_dir=$(pwd)/tests/results

echo "docker run -v $results_dir:/scratch --entrypoint py.test $BIX_TOOL --verbose --json /scratch/all_tests_results.json --junitxml=/scratch/all_tests_results.xml --html=/scratch/all_tests_results.html --ignore=/opt/project/tests/dpl_tests /opt/project/tests"

cd docker

docker run -v "$results_dir":/scratch --entrypoint py.test $BIX_TOOL --verbose --json /scratch/all_tests_results.json --junitxml=/scratch/all_tests_results.xml --html=/scratch/all_tests_results.html --cov=/opt/project/src --cov-report=html:/scratch/all_tests_cov_report.html --ignore=/opt/project/tests/dpl_tests /opt/project/tests


`));
});

