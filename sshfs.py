"""
SSHFS
-----

.. _sshfs: https://github.com/althonos/fs.sshfs

Import machinery to load code directly over a ssh connection (either one initiated from the machine this module runs on or via local port forwarding when it is run on a remote machine)::

    import condor
    condor.enable_sshfs_import(port=...)

Downloading of the remote files imported in a python session to the local filesystem is also supported via the ``download=True`` parameter to the :func:`.enable_sshfs_import` function of the parent module :mod:`condor`.

.. Warning::

    While `fs.sshfs <sshfs_>`_ honors the ssh config file (can be given as parameter ``config_path``), at present, it doesn't seem to be working with proxy setups (however, in that case one can still set up local port forwarding and connect to localhost instead).


"""
from importlib.machinery import ModuleSpec
from importlib.util import module_from_spec
from traitlets.config import Application
from traitlets import Unicode, Integer, Bool
from fs.sshfs import SSHFS
import sys, os

class sshfsConnect(Application):
    """Connection instance used by :class:`.sshfsImporter`.

    :Keyword arguments:
        * **host** - hostname (localhost in case of port forwarding)
        * **user** - username
        * **port** - port
        * **path** - folder on host machine where to root the import statements
        * **download** (:obj:`bool`) - whether or not to download the imported files to the local filesystem (right now, it will download the directory tree to the folder from which executed)

        All arguments that are not given will be searched for in the :data:`python.data.config` values.

        Further kwargs are handed over to the `fs.sshfs.SSHFS <sshfs_>`_ instantiation.

    """

    host = Unicode('localhost').tag(config=True)
    user = Unicode().tag(config=True)
    port = Integer().tag(config=True)
    path = Unicode().tag(config=True)
    download = Bool(False).tag(config=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_config_file('config.py', os.path.dirname(__file__))
        # self.sshfs = SSHFS(self.host, self.user, port=self.port, **sshfs_kw)
        # self.base_folder = [os.path.splitext(f)[0] for f in self.sshfs.listdir(self.path)]
        # self.nodes = {}

class sshfsImporter(sshfsConnect):
    """Class to import code directly via a ssh connection (with local port forwarded) by means of a regular import statement. Added to :data:`sys.meta_path` via the :func:`.enable_sshfs_import` method of the :mod:`condor` package. All parameters given to that method are handed to :class:`.sshfsConnect`, where they are described.

    """
    def find_spec(self, fullname, path, targ=None):
        self.names = fullname.split('.')
        if path is None and fullname in self.base_folder:
            node = self.base_folder
        elif isinstance(path, str) and path in self.nodes:
            node = self.nodes[path]
        try:
            if self.names[-1] in node:
                self.spec = ModuleSpec(fullname, self)
                return self.spec
        except:
            return None

    def load_module(self, fullname):
        if fullname in sys.modules:
            print('module {} already loaded'.format(fullname))
            return sys.modules[fullname]
        print('loading {} from sshfs host {}'.format(fullname, self.host))
        if fullname != self.spec.name:
            return None
        mod = module_from_spec(self.spec)
        mod.__name__ = fullname
        mod.__path__ = os.path.join(self.path, *self.names)
        mod.__package__ = self.names[0]
        sys.modules[self.spec.name] = mod
        if self.sshfs.isdir(mod.__path__):
            if mod.__path__ in self.nodes:
                node = self.nodes[mod.__path__]
            else:
                node = [os.path.splitext(f)[0] for f in self.sshfs.listdir(mod.__path__)]
                self.nodes[mod.__path__] = node
            if '__init__' in node:
                mod.__file__ = os.path.join(mod.__path__, '__init__.py')
        else:
            mod.__file__ = '{}.py'.format(mod.__path__)
        try:
            with self.sshfs.open(mod.__file__) as f:
                s = f.read()
                exec(s, mod.__dict__)
                if self.download:
                    import pathlib as pl
                    p = pl.Path('.{}'.format(mod.__file__[len(self.path):]))
                    mod.__file__ = p.as_posix()
                    p.parent.mkdir(parents = True, exist_ok=True)
                    with open(mod.__file__, 'w') as w:
                        w.write(s)
        except:
            raise
            sys.modules.pop(self.spec.name)
        return mod

    def reload(self, module):
        with self.sshfs.open(module.__file__) as f:
            exec(f.read(), module.__dict__)
        print('reloaded {} from sshfs host {}'.format(module.__name__, self.host))

    def __del__(self):
        self.sshfs.close()


def enable_sshfs_import(*args, **kwargs):
    """Call once in order to enable the direct import of modules from text files on a :mod:`fs.sshfs` filesystem. This inserts an instance of :class:`~.sshfs.sshfsImporter` into the beginning of :data:`sys.meta_path`. All arguments are directly passed to :class:`~.sshfs.sshfsConnect`.

    """
    # NOTE: appending the loader works in normal ipython, but trips up in jupyter notebooks
    # (presumably because loaders earlier in the path return something unwanted)
    sys.meta_path.insert(0, sshfsImporter(*args, **kwargs))

def disable_sshfs_import():
    """Remove all instances of :class:`~.github.GithubImporter` from :data:`sys.meta_path`, thereby disabling the direct import of modules from a GitHub repo.

    """
    for mod in [m for m in sys.meta_path if isinstance(m, sshfsImporter)]:
        mod.sshfs.close() # to be on the safe side
        sys.meta_path.remove(mod)

def update_local_startup():
    pass
