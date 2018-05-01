"""
Remote imports
==============

.. Note::

    * Not checking against sys.modules before loading the code right now - appears to be done by the machinery already.
    * The *__path__* attribute on the module is normally a list - I use either a str or a dict, maybe that needs to be modified in the future.

.. TODO::

    * set a __cached__ property (https://docs.python.org/3/library/importlib.html#importlib.abc.Loader.load_module)
    * maybe add a check that files are actually .py files

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
    from . import github
    for mod in [m for m in sys.meta_path if isinstance(m, github.GithubImporter)]:
        sys.meta_path.remove(mod)

def enable_sshfs_import(*args, **kwargs):
    """Call once in order to enable the direct import of modules from text files on a :mod:`fs.sshfs` filesystem. This inserts an instance of :class:`~.sshfs.sshfsImporter` into the beginning of :data:`sys.meta_path`. All arguments are directly passed to :class:`~.sshfs.sshfsConnect`.

    """
    import sys
    from . import sshfs
    # NOTE: appending the loader works in normal ipython, but trips up in jupyter notebooks
    # (presumably because loaders earlier in the path return something unwanted)
    sys.meta_path.insert(0, sshfs.sshfsImporter(*args, **kwargs))

def disable_sshfs_import():
    """Remove all instances of :class:`~.github.GithubImporter` from :data:`sys.meta_path`, thereby disabling the direct import of modules from a GitHub repo.

    """
    from . import sshfs
    for mod in [m for m in sys.meta_path if isinstance(m, sshfs.sshfsImporter)]:
        sys.meta_path.remove(mod)


def reload(module):
    module.__loader__.reload(module)
