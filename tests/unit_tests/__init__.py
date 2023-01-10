import re
import os

def _get_abs_path_for_test_resource(resource = None):
    '''return an appropriate absolute path for a test resource or throw IOError if it does not exist
    '''

    # Note we assume that all requested resources are rooted in the folder above the location of this __file__
    rooted_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    requested_resource = os.path.abspath(os.path.join(rooted_dir, resource))
    if not os.path.exists(requested_resource):
        raise IOError('The requested resource "' + requested_resource + '" does not exist.')

    return requested_resource

def _get_abs_path_for_project_root():
    '''return an appropriate absolute path for the root of this project.
        Assumes standard HLI project layout
    '''

    # Note we assume that all requested resources are rooted in the folder above the location of this __file__
    project_root = re.sub(r'/tests/unit_tests/__init__.py', r'', __file__)
    return os.path.abspath(project_root)

# These should be imported - i.e. from unit_tests import input_test_data
input_test_data = _get_abs_path_for_test_resource("resources/test_inputs")
input_golden_data = _get_abs_path_for_test_resource("resources/gold_standard_outputs")

working_dir = os.path.join(os.path.abspath(os.path.curdir), "unit_tests/working_dir")
# This is useful because we now direct TMPDIR usage in our code to our test framework working dir
os.environ['TMPDIR'] = working_dir

output_dir = os.path.join(os.path.abspath(os.path.curdir), "unit_tests/output_dir")
logging_dir = os.path.join(os.path.abspath(os.path.curdir), "unit_tests/logging_dir")