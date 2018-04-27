"""
GitHub
------

Import machinery to load code directly from GitHub. Simply import condor.github, and subsequently import statements consider code from the repo with which :class:`GithubImporter` was initialized. The key statement is the ``sys.meta_path.append`` at the end of the file.

.. Note::

    * Not checking against sys.modules before loading the code right now - appears to be done by the machinery already.
    * The *__path__* attribute on the module is normally a list - I use either a str or a dict, maybe that needs to be modified in the future.

"""
from . import config
from importlib.machinery import ModuleSpec
from importlib.util import module_from_spec
import sys, requests, os, json
from urllib3.util import Url


class GitHubConnect(object):
    def __init__(self, user=None, repo=None, folder=None):
        super().__init__()
        gh = config['github']
        self.params = {'token': gh['token']}
        api = requests.utils.urlparse(gh['api'])
        self.netloc = api.netloc
        self.base_url = Url(api.scheme, host=api.netloc, path=os.path.join(
            'repos',
            gh['user'] if user is None else user,
            gh['repo'] if repo is None else repo,
            'contents',
            gh['folder'] if folder is None else folder
        )).url
        r = requests.get(self.base_url)
        assert r.ok, r.status_code
        self.base_folder = self.list2dict(r.text)

    def list2dict(self, text):
        return {os.path.splitext(f['name'])[0]: f for f in json.loads(text)}

class GithubImporter(GitHubConnect):
    def find_spec(self, fullname, path, target=None):
        base, _, name = fullname.rpartition('.')
        node = path if isinstance(path, dict) else self.base_folder
        if isinstance(path, str) and requests.utils.urlparse(path).netloc == self.netloc:
            r = requests.get(path)
            if r.ok:
                node = self.list2dict(r.text)
                sys.modules[base].__path__ = node
        try:
            self.spec = ModuleSpec(fullname, self, loader_state=node[name])
            return self.spec
        except:
            return None

    def load_module(self, fullname):
        print('loading {} from github'.format(fullname))
        if fullname != self.spec.name:
            return None
        mod = module_from_spec(self.spec)
        mod.__name__ = fullname
        mod.__file__ = self.spec.loader_state['download_url']
        sys.modules[self.spec.name] = mod
        if self.spec.loader_state['type'] == 'file':
            r = requests.get(mod.__file__, params=self.params)
            if r.ok:
                exec(r.text, mod.__dict__)
        else:
            mod.__path__ = self.spec.loader_state['_links']['self']
            mod.__package__ = fullname.rpartition('.')[0]
        return mod
