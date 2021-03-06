"""
GitHub
------
.. _GitHub: http://www.github.com>

Import machinery to load code directly from GitHub. Simply ``import condor`` and invoke :func:`.enable_github_import`, and subsequently import statements consider code from the repo with which :class:`GithubImporter` was initialized.

"""
from importlib.machinery import ModuleSpec
from importlib.util import module_from_spec
import sys, requests, os, json
from urllib3.util import Url


class GithubConnect(object):
    """Connection base class, currently only used by :class:`GithubImporter`. Initialises the attribute :attr:`base_folder` with contents of a specified directory in a repo on GitHub_. Keywords that are not given are read from the global config file.

    :Keyword arguments:

        * **user** - GitHub user name
        * **repo** - GitHub repo name
        * **folder** - root folder within repo in which to anchor any search
        * **token** - GitHub api token

    """
    def __init__(self, user=None, repo=None, folder=None, token=None):
        if not all(user, repo, folder, token):
            if 'cezar' not in globals():
                import runpy
                gh = runpy.run_path(os.path.expanduser(os.environ['PYTHONSTARTUP']))['cezar']['github']
            else:
                gh = cezar['github']

        api = requests.utils.urlparse('https://api.github.com')
        self.params = {'token': gh['token'] if token is None else token}
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
    """Module finder / loader for text files from a GitHub_ repo. Init arguments are inherited from :class:`GithubConnect`.

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
        mod.__package__ = fullname.rpartition('.')[0]
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
            if '__init__' in node:
                mod.__file__ = node['__init__']['download_url']
        if mod.__file__ is not None:
            r = requests.get(mod.__file__, params=self.params)
            if r.ok:
                exec(r.text, mod.__dict__)
        return mod

def enable_github_import(*args, **kwargs):
    """Call once in order to enable the direct import of modules from text files in a `GitHub_ repo. This inserts an instance of :class:`~.github.GithubImporter` into the beginning of :data:`sys.meta_path`. All arguments are directly passed to :class:`~.github.GithubConnect`.

    """
    # NOTE: appending the loader works in normal ipython, but trips up in jupyter notebooks
    # (presumably because loaders earlier in the path return something unwanted)
    sys.meta_path.insert(0, GithubImporter(*args, **kwargs))

def disable_github_import():
    """Remove all instances of :class:`~.github.GithubImporter` from :data:`sys.meta_path`, thereby disabling the direct import of modules from a GitHub repo.

    """
    for mod in [m for m in sys.meta_path if isinstance(m, GithubImporter)]:
        sys.meta_path.remove(mod)
