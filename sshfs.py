#!/usr/bin/env python
"""
SSHFS
-----

.. _sshfs: https://github.com/althonos/fs.sshfs

Import machinery to load code directly over a ssh connection (either one initiated from the machine this module runs on or via local port forwarding when it is run on a remote machine)::

    import condor
    condor.enable_sshfs_import(port=...)

All parameters (see :class:`SSHFSConnect`) are configurable via the `traitlets  <https://traitlets.readthedocs.io/en/stable/config.html>`_ mechanism, i.e. they can be set via a config file, ``__init__`` arguments, or `the command line <https://traitlets.readthedocs.io/en/stable/config.html#command-line-arguments>`_.
Downloading of the remote files imported in a python session to the local filesystem is also supported via the :attr:`.SSHFSConnect.download` trait (arguments to :func:`.enable_sshfs_import` will be handed up to :class:`SSHFSConnect`).

Script Running
==============

Running scripts is supported via the :class:`SSHFSRunner` class, which uses the `subcommand <https://traitlets.readthedocs.io/en/stable/config.html#subcommands>`_ mechanism. Subcommands can be configured via a file, either loaded via sshfs or locally. To use the runner, simply execute this file as a script with the desired subcommand and command-line options.

.. Warning::

    While `fs.sshfs <sshfs_>`_ honors the ssh config file (can be given as parameter ``config_path``), at present, it doesn't seem to be working with proxy setups (however, in that case one can still set up local port forwarding and connect to localhost instead).


"""
from importlib.machinery import ModuleSpec
from importlib.util import module_from_spec
from importlib import import_module
from traitlets.config import Application
from traitlets.config.loader import PyFileConfigLoader
from traitlets import Unicode, Integer, Bool, Dict
from fs.sshfs import SSHFS
import sys, os, re

class SSHFSConnect(Application):
    """Connection instance used by :class:`.SSHFSImporter`.

    All of the kwargs can also be set via a config file or command-line args (see module docstring).

    :Keyword arguments:
        * :attr:`host`
        * :attr:`user`
        * :attr:`port`
        * :attr:`path`
        * :attr:`pkey`
        * :attr:`download`

    """
    host = Unicode('localhost').tag(config=True)
    """sshfs hostname (localhost in case of port forwarding)"""

    user = Unicode().tag(config=True)
    """sshfs username"""

    port = Integer().tag(config=True)
    """sshfs port (possibly forwarded one)"""

    pkey = Unicode().tag(config=True)
    """pkey parameter to :class:`fs.sshfs.SSHFS`"""

    path = Unicode().tag(config=True)
    """path on host from which the import statements should be executed"""

    download = Bool(False).tag(config=True)
    """whether or not to download the imported files to the local filesystem (right now, it will download the directory tree to the folder from which executed)"""


    def __init__(self, *args, **kwargs):
        config = PyFileConfigLoader('config.py', os.path.dirname(os.path.realpath(__file__))).load_config()
        if 'config' in kwargs:
            config.merge(kwargs.pop('config', {}))
        super().__init__(*args, config=config, **kwargs)
        self.sshfs = SSHFS(self.host, self.user, port=self.port, pkey=None if self.pkey=='' else self.pkey)
        self.base_folder = [os.path.splitext(f)[0] for f in self.sshfs.listdir(self.path)]
        self.nodes = {}

class SSHFSImporter(SSHFSConnect):
    """Class to import code directly via a ssh connection (with local port forwarded) by means of a regular import statement. Added to :data:`sys.meta_path` via the :func:`.enable_sshfs_import` method of the :mod:`condor` package. All parameters are described under :class:`.SSHFSConnect`.

    """
    _id = 'condor.SSHFSImporter' # hack to overcome isinstance problems

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
        with self.sshfs.open(os.path.join(self.path, module.__file__)) as f:
            exec(f.read(), module.__dict__)
        print('reloaded {} from sshfs host {}'.format(module.__name__, self.host))

    def __del__(self):
        try:
            self.sshfs.close()
        except: pass

class SSHFSImportDisabled(Exception):
    pass

def enable_sshfs_import(*args, **kwargs):
    """Call once in order to enable the direct import of modules from text files on a :mod:`fs.sshfs` filesystem. This inserts an instance of :class:`~.sshfs.SSHFSImporter` into the beginning of :data:`sys.meta_path`. All arguments are directly passed to :class:`~.sshfs.SSHFSConnect`.

    """
    # NOTE: appending the loader works in normal ipython, but trips up in jupyter notebooks
    # (presumably because loaders earlier in the path return something unwanted)
    try:
        disable_sshfs_import()
    except SSHFSImportDisabled: pass
    finally:
        sys.meta_path.insert(0, SSHFSImporter(*args, **kwargs))

def disable_sshfs_import():
    """Remove all instances of :class:`~.sshfs.SSHFSImporter` from :data:`sys.meta_path`, thereby disabling the direct import of modules from a GitHub repo.

    """
    for m in sys.meta_path:
        try:
            if m._id == 'condor.SSHFSImporter':
                m.sshfs.close() # to be on the safe side
                sys.meta_path.remove(m)
        except: raise SSHFSImportDisabled

def get_sshfs():
    """Get the connected :class:`fs.sshfs.SSHFS` instance of an installed :class:`SSHFSImporter`."""
    for m in sys.meta_path:
        try:
            if m._id == 'condor.SSHFSImporter':
                return m.sshfs
        except: pass
    raise SSHFSImportDisabled('no SSHFSImporter installed, run enable_sshfs_import() first')


class SSHFSRunner(Application):
    """Script runner class with loads a class as a traitlet subcommand via sshfs and executes its :meth:`start` method. Mostly inteded to be run as a command-line application - it is the entry point when this file is run as a script.

    **All arguments before '--' pertain to this class, and all arguments after '--' pertain to the class being run as subcommand.**

    """

    subcommands = Dict().tag(config=True)
    """Subcommands defined as a mapping <command: class>, with the class being loadable via sshfs."""

    sshfs_config = Unicode().tag(config=True)
    """Config file path on the target sshfs host, if needed. Subcommands can also be defined here. This is different from the local config file - it's only available on the remote side."""

    aliases = {'p': 'SSHFSConnect.port', 'key': 'SSHFSConnect.pkey', 'cfg': 'SSHFSRunner.sshfs_config'}

    def __init__(self):
        super().__init__()
        self.load_config_file('config.py', os.path.dirname(os.path.realpath(__file__)))

    def initialize(self):
        # for SSHFSRunner app
        scmd, args = [], sys.argv[1:]
        if re.match('^\w(\-?\w)*$', args[0]):
            scmd.append(args.pop(0))
        self.parse_command_line(args)
        imptr = SSHFSImporter(config=self.config)
        sys.meta_path.insert(0, imptr)
        if self.sshfs_config != '':
            loader = import_module('traitlets.config.loader')
            c = loader.ConfigLoader()
            c.clear() # creates config instance
            exec(imptr.sshfs.open(self.sshfs_config).read(),
                 {'c': c.config, 'get_config': lambda: c.config})
            self.update_config(c.config)
        # for subapp
        scmd.extend(self.extra_args)
        self.parse_command_line(scmd)

if __name__ == '__main__':
    app = SSHFSRunner()
    app.initialize()
    app.subapp.start()
