from . import config
from importlib.machinery import ModuleSpec
from importlib.util import module_from_spec
from fs.sshfs import SSHFS
import sys, os

class sshfsConnect(object):
    def __init__(self, host=None, user=None, port=None, folder=None, download=False, **kwargs):
        fs = config['sshfs']
        self.host = fs['host'] if host is None else host
        self.user = fs['user'] if user is None else user
        self.port = fs['port'] if port is None else port
        self.folder = fs['path'] if folder is None else folder
        self.sshfs = SSHFS(self.host, self.user, port=self.port, **kwargs)
        self.base_folder = [os.path.splitext(f)[0] for f in self.sshfs.listdir(self.folder)]
        self.nodes = {}
        self._dl = download

class sshfsImporter(sshfsConnect):
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
        mod.__path__ = os.path.join(self.folder, *self.names)
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
                if self._dl:
                    import pathlib as pl
                    p = pl.Path('.{}'.format(mod.__file__[len(self.folder):]))
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
