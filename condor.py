from fs.sshfs import SSHFS
from imp import new_module
from os.path import split, splitext, join
from cartopy.io import shapereader
import requests


sshfs = SSHFS('localhost', 'arno', port=9000)
base = '/home/arno/Documents/code/python'

def module(path):
    m = new_module(splitext(split(path)[1])[0])
    with sshfs.open(join(base, path)) as f:
        exec(f.read(), m.__dict__)
    return m

class github(object):
    base_url = 'https://raw.githubusercontent.com/betaplane/cezanne/master/python'
    params = {'token': '94d8a968ec25e77ee2b7c2a5f44386cd7891af54'}

    @classmethod
    def module(cls, path):
        r = requests.get(join(cls.base_url, path), params=cls.params)
        m = new_module(splitext(split(path)[1])[0])
        exec(r.text, m.__dict__)
        return m


class Coquimbo(object):
    path = '/home/arno/Documents/data/geo/GSHHG'
    def __init__(self, proj=None):
        if proj is None:
            from cartopy import crs
            self.proj = crs.PlateCarree()
        else:
            self.proj = proj
        self.coast = list(sshfs_shapereader(join(self.path, 'coast'), sshfs).geometries())
        self.rivers = list(sshfs_shapereader(join(self.path, 'river'), sshfs).geometries())
        self.border = list(sshfs_shapereader(join(self.path, 'border'), sshfs).geometries())

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
