from . import config, config_file
from importlib.machinery import ModuleSpec
from types import ModuleType
import sys, requests, os, json


class GitHubConnect(config):
    def list(self, path):
        gh = self.config['github']
        self.params = {'token': gh['token']}
        r = requests.get(gh['api'] + gh['cezanne'] + path)
        return json.loads(r.text)

    @property
    def python(self):
        if not hasattr(self, '_python'):
            self._python = {os.path.splitext(f['name'])[0]: f for f in self.list('python')}
        return self._python

    @staticmethod
    def child(node, name):
        c = node.get('child')
        if c is None:
            r = requests.get(node['_links']['self'])
            node['child'] = {os.path.splitext(f['name'])[0]: f for f in json.loads(r.text)}
        return node['child'][name]

    def walk(self, names):
        node = self.python.get(names[0])
        for n in names[1:]:
            node = self.child(node, n)
        return names[-1], node

class GithubImporter(GitHubConnect):
    def find_spec(self, fullname, path, target=None):
        names = fullname.split('.')
        return ModuleSpec(fullname, self) if names[0] == 'cezanne' else None

    def load_module(self, fullname):
        print('load ', fullname)
        names = fullname.split('.')
        m = ModuleType(names[-1])
        sys.modules[names[-1]] = m
        if len(names) == 1:
            return m
        node = self.walk(names[1:])
        if node['type'] == 'file':
            r = requests.get(node['download_url'], params=self.params)
            if r.ok:
                exec(r.text, m.__dict__)
        else:
            m.__path__ = names[-1]
        return m

sys.meta_path.append(GithubImporter())
