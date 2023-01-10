import pytest

pytest_plugins = ["parser"]

def pytest_addoption(parser):
    parser.addoption("--dpl_env", help="dpl environment to run tests in")
    parser.addoption("--dpl_repo_bucket", help="dpl_repo_bucket to get files from")
    parser.addoption("--dpl_cache_bucket", help="Output location for dpl files")
    parser.addoption("--username", help="username of person who registered pipelines for test if running in dev", default=None)
                
                
@pytest.fixture
def dpl_env(request):
    return request.config.getoption("--dpl_env")
                    
@pytest.fixture
def dpl_repo_bucket(request):
    return request.config.getoption("--dpl_repo_bucket")
                        
@pytest.fixture
def dpl_cache_bucket(request):
    return request.config.getoption("--dpl_cache_bucket")

@pytest.fixture
def username(request):
    return request.config.getoption("--username")