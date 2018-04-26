from . import config
from importlib.machinery import ModuleSpec
from importlib.util import module_from_spec
import sys, requests, os, json


class GitHubConnect(config):
    def __init__(self, repo='cezanne', folder='python'):
        super().__init__()
        gh = self.config['github']
        self.params = {'token': gh['token']}
        self.netloc = requests.utils.urlparse(gh['api']).netloc
        self.base_url = gh['api'] + '/repos/' + gh['user'] + '/' + repo + '/contents/' + folder
        r = requests.get(self.base_url)
        if r.ok:
            self.base_folder = self.list2dict(r.text)

    def list2dict(self, text):
        return {os.path.splitext(f['name'])[0]: f for f in json.loads(text)}

    def child(self, node):
        if node['type'] == 'file':
            name, ext = os.path.splitext(node['name'])
            if ext == '.py':
                self.files.append(name)
            return {'type': 'file', 'url': node['download_url']}
        else:
            r = requests.get(node['_links']['self'])
            return {'type': 'dir', 'content': self.list2dict(r.text)}

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
            print(fullname, path)
            return self.spec
        except:
            return None

    def load_module(self, fullname):
        print('load ', fullname)
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

sys.meta_path.append(GithubImporter())