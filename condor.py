from imp import new_module
from os.path import split, splitext, join, dirname
from cartopy.io import shapereader
from configparser import ConfigParser


config_file = '/HPC/arno/general.cfg'
"name of the config file"

class condor(object):
    def __init__(self):
        self.config = ConfigParser()
        self.config.read(config_file)

class module(condor):
    def github(self, path):
        import requests
        gh = self.config['github']
        r = requests.get(join(gh['path'], path), params={'token': gh['token']})
        m = new_module(splitext(split(path)[1])[0])
        exec(r.text, m.__dict__)
        return m

    def sshfs(self, path):
        from fs.sshfs import SSHFS
        ssh = self.config['sshfs']
        sshfs = SSHFS(ssh['host'], ssh['user'], port=ssh['port'])
        m = new_module(splitext(split(path)[1])[0])
        with sshfs.open(join(ssh['path'], path)) as f:
            exec(f.read(), m.__dict__)
        return m

class Coquimbo(condor):
    def __init__(self, proj=None):
        super().__init__()
        ssh = self.config['sshfs']
        sshfs = SSHFS(ssh['host'], ssh['user'], port=ssh['port'])
        path = self.config['GSHHG']['path']

        if proj is None:
            from cartopy import crs
            self.proj = crs.PlateCarree()
        else:
            self.proj = proj
        self.coast = list(sshfs_shapereader(join(path, 'coast'), sshfs).geometries())
        self.rivers = list(sshfs_shapereader(join(path, 'river'), sshfs).geometries())
        self.border = list(sshfs_shapereader(join(path, 'border'), sshfs).geometries())

    def __call__(self, ax, lines_only=False, colors=['k']):
        if lines_only:
            ax.add_geometries(self.coast, crs=self.proj, facecolor='none', edgecolor=colors[0], zorder=10)
            ax.add_geometries(self.border, crs=self.proj, facecolor='none', edgecolor=colors[-1], linewidth=.5, zorder=10)
        else:
            ax.background_patch.set_color('lightblue')
            ax.add_geometries(self.coast, crs=self.proj, facecolor='lightgray', edgecolor='k', zorder=0)
            ax.add_geometries(self.rivers, crs=self.proj, facecolor='none', edgecolor='b', zorder=0)
            ax.add_geometries(self.border, crs=self.proj, facecolor='none', edgecolor='g', linewidth=.5, zorder=0)
            ax.set_extent((-72.2, -69.8, -32.5, -28.2), crs=self.proj)

class sshfs_shapereader(shapereader.Reader):
    def __init__(self, path, sshfs):
        from shapefile import Reader
        self._sshfs = {k: sshfs.openbin('.'.join((path, k))) for k in ['shp', 'shx', 'dbf']}
        self._reader = Reader(**self._sshfs)
        self._geometry_factory = shapereader.GEOMETRY_FACTORIES.get(self._reader.shapeType)
        self._fields = self._reader.fields

    def __del__(self):
        for f in self._sshfs.values():
            f.close()
