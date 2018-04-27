"""
GitHub
------

Import machinery to load code directly from GitHub. Simply import condor.github, and subsequently import statements consider code from the repo with which :class:`GithubImporter` was initialized. The key statement is the ``sys.meta_path.append`` at the end of the file.

.. Note::

    * Not checking against sys.modules before loading the code right now - appears to be done by the machinery already.
    * The *__path__* attribute on the module is normally a list - I use either a str or a dict, maybe that needs to be modified in the future.

.. todo::

    * set a __cached__ property (https://docs.python.org/3/library/importlib.html#importlib.abc.Loader.load_module)

"""
from . import config
from importlib.machinery import ModuleSpec
from importlib.util import module_from_spec
import sys, requests, os, json
from urllib3.util import Url


class GithubConnect(object):
    """Connection base class, currently only used by :class:`GithubImporter`. Initialises the attribute :attr:`base_folder` with contents of a specified directory in a repo on `GitHub <http://www.github.com>`_. Keywords that are not given are read from the global config file.

    :Keyword arguments:

        * **user** - GitHub user name
        * **repo** - GitHub repo name
        * **folder** - root folder within repo in which to anchor any search

    """
    def __init__(self, user=None, repo=None, folder=None):
        super().__init__()
        gh = config['github']
        self.params = {'token': gh['token']}
        api = requests.utils.urlparse(gh['api'])
        self.user = gh['user'] if user is None else user
        self.repo = gh['repo'] if repo is None else repo
        self.folder = gh['folder'] if folder is None else folder
        self.netloc = api.netloc
        self.base_url = Url(api.scheme, host=api.netloc, path=os.path.join(
            'repos', self.user, self.repo, 'contents', self.folder)).url
        r = requests.get(self.base_url)
        assert r.ok, r.status_code
        self.base_folder = self.list2dict(r.text)
        self.nodes = {}

    def list2dict(self, text):
        return {os.path.splitext(f['name'])[0]: f for f in json.loads(text)}

class GithubImporter(GithubConnect):
    """Module finder / loader for text files from a `GitHub <http://www.github.com>`_ repo. Init arguments are inherited from :class:`GithubConnect`.

    """
    def find_spec(self, fullname, path, target=None):
        name = fullname.rpartition('.')[-1]
        if path is None and fullname in self.base_folder:
            node = self.base_folder
        elif isinstance(path, str) and path in self.nodes:
            node = self.nodes[path]
        try:
            self.spec = ModuleSpec(fullname, self, loader_state=node[name])
            return self.spec
        except:
            return None

    def load_module(self, fullname):
        print('loading {} from github repo {}'.format(fullname, self.repo))
        if fullname != self.spec.name:
            return None
        mod = module_from_spec(self.spec)
        mod.__name__ = fullname
        mod.__file__ = self.spec.loader_state['download_url']
        sys.modules[self.spec.name] = mod
        if self.spec.loader_state['type'] == 'dir':
            url = self.spec.loader_state['_links']['self']
            if url in self.nodes:
                node = self.nodes[url]
            else:
                r = requests.get(url)
                if r.ok:
                    node = self.list2dict(r.text)
                    self.nodes[url] = node
            mod.__path__ = url
            mod.__package__ = fullname.rpartition('.')[0]
            if '__init__' in node:
                mod.__file__ = node['__init__']['download_url']
        if mod.__file__ is not None:
            r = requests.get(mod.__file__, params=self.params)
            if r.ok:
                exec(r.text, mod.__dict__)
        return mod
