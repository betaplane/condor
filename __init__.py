"""
.. automodule:: condor.github
    :members:

"""
from configparser import ConfigParser
config = ConfigParser()
config.read('/HPC/arno/general.cfg')

def enable_github_import(*args, **kwargs):
    """Call once in order to enable the direct import of modules from text files in a `GitHub <http://www.github.com>`_ repo. This inserts an instance of :class:`~.github.GithubImporter` into the beginning of :data:`sys.meta_path`. All arguments are directly passed to :class:`~.github.GithubConnect`.

    """
    import sys
    from . import github
    # NOTE: appending the loader works in normal ipython, but trips up in jupyter notebooks
    # (presumably because loaders earlier in the path return something unwanted)
    sys.meta_path.insert(0, github.GithubImporter(*args, **kwargs))

def disable_github_import():
    """Remove all instances of :class:`~.github.GithubImporter` from :data:`sys.meta_path`, thereby disabling the direct import of modules from a GitHub repo.

    """
    for mod in [m for m in sys.meta_path if isinstance(m, github.GithubImporter)]:
        sys.meta_path.remove(mod)
