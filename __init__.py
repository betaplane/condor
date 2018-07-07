"""
Remote imports
==============

.. Note::

    * Not checking against sys.modules before loading the code right now - appears to be done by the machinery already.
    * The *__path__* attribute on the module is normally a list - I use either a str or a dict, maybe that needs to be modified in the future.

.. TODO::

    * set a __cached__ property (https://docs.python.org/3/library/importlib.html#importlib.abc.Loader.load_module)
    * maybe add a check that files are actually .py files
    * maybe add a ``if __file__ == __main__`` statement so that the modules can be run as files

.. autofunction:: condor.enable_sshfs_import
.. autofunction:: condor.disable_sshfs_import

.. autofunction:: condor.enable_github_import
.. autofunction:: condor.disable_github_import

.. automodule:: condor.sshfs
    :members: sshfsConnect, sshfsImporter

.. automodule:: condor.github
    :members: GithubConnect, GithubImporter

"""
from .sshfs import enable_sshfs_import, disable_sshfs_import
from .github import enable_github_import, disable_github_import

def reload(module):
    """Reload the module via the mechanism used to load it in the first place.

    """
    module.__loader__.reload(module)
