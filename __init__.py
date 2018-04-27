"""
.. automodule:: condor.github
    :members:

"""
from configparser import ConfigParser
config = ConfigParser()
config.read('/HPC/arno/general.cfg')

def enable_github_import(*args, **kwargs):
    from . import github
    import sys
    # NOTE: appending the loader works in normal ipython, but trips up in jupyter notebooks
    # (presumably because loaders earlier in the path return something unwanted)
    sys.meta_path.insert(0, github.GithubImporter(*args, **kwargs))
