import os
import shutil
import fnmatch
import re
import math
import glob
import pytest
import filecmp
from copy import deepcopy
import hli_python3_utils
import json
import shlex
import traceback
from subprocess import Popen, PIPE
from . import _get_abs_path_for_project_root


def test_version_was_bumped():
    ''' This function checks current git diff and if in a repo confirms version number was bumped
        This may be a dumb idea but it will catch a commit where version has not been bumped in unit test to remind us.
    '''

    cmd = "git diff --staged"
    process = Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE, universal_newlines=True)
    out, err = process.communicate()
    exit_code = process.wait()

    # Lets design several ways to pass but otherwise we fail this test case
    if re.search(r'Not a git repository', err):
        assert True
        print('Not a git repository')
    elif re.search(r'\+VERSION[^\n]*\n', out):
        match = re.search(r'\+VERSION[^\n]*\n', out)
        assert True
        print("Evidence of a version bump: {}".format(match.group(0)))
    elif re.search(r'\+__version__[^\n]*\n', out):
        match = re.search(r'\+__version__[^\n]*\n', out)
        assert True
        print("Evidence of a version bump: {}".format(match.group(0)))
    elif re.search(r'\+\s*\"version\"[^\n]*\n', out):
        match = re.search(r'\+\s*\"version\"[^\n]*\n', out)
        assert True
        print("Evidence of a version bump: {}".format(match.group(0)))
    elif exit_code != 0:
        # No git maybe?
        assert True
        print("Assuming not a git repo - unable to execute git command")
    elif out == "":
        print("Ok - no commits staged")
    else:
        assert False, "Looks like you need to commit a version number bump!"

@pytest.mark.skipif(_get_abs_path_for_project_root().endswith('/project'),
                    reason="Skipping unit test intended to run outside docker environment")
def test_version_is_set_and_expected_format():
    ''' This function finds VERSION strings in various text files and confirms they match and format is as expected
        Perhaps this is dumb, but perhaps this will help catch when we fail to bump version numbers or do it inconsistently
    '''

    # All conforming HLI Tools should have package.json
    # And this is the canonical location to define version

    # Allows this test to be invoked at higher level in hierarchy
    package=[]
    for root, dirnames, filenames in os.walk(_get_abs_path_for_project_root()):
        for filename in fnmatch.filter(filenames, 'package.json'):
            package.append(os.path.join(os.path.abspath(root), filename))

    assert (package is not None)
    assert (len(package) == 1)
    with open(package[0], "rt") as json_file:
        json_obj = json.load(json_file)
        version = json_obj['version']
    print("{}".format(version))
    assert(re.match(r'[0-9]+\.[0-9]+\.[0-9]+', version))

    # Now search other candidate files
    fileNamesToMatch=['Makefile', 'Dockerfile', '*.py', 'steps.json']
    files = []
    for root, dirnames, filenames in os.walk(_get_abs_path_for_project_root()):
        # Note we get here for each subdir...

        patterns = []
        patterns += fileNamesToMatch
        # Here, besides matching by file name, we could match by file type (say use the magic library to get text type files)
        # or we could match based on file size etc.
        matchingFiles = []
        for p in patterns:
            for filename in fnmatch.filter(filenames, p):
                matchingFiles.append(filename)

        for filename in matchingFiles:
            print("{} {}".format(os.path.abspath(root), filename))
            files.append(os.path.join(os.path.abspath(root), filename))

    # Now we have text files we want to look into for a VERSION string
    matches = {}
    r = re.compile(r'(?i)(?P<label>\s+"?VERSION"?\s*[=:]\s*)"?(?P<version_string>[0-9\.]+)"?')
    for myfile in files:
        print("Processing: {}".format(myfile))
        with open(myfile, "rt") as f:
            matches[myfile] = [m.groupdict() for m in r.finditer(f.read())]

    for key, matched in matches.items():
        for match in matched:
            print("Confirm Versions match: {} in file {} with label {} and version {}".format(version,
                                                                                              key,
                                                                                              match['label'],
                                                                                              match['version_string']))
            assert(version == match['version_string'])
