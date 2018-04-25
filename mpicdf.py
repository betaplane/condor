from mpi4py import MPI
from netCDF4 import Dataset, num2date

class Data(object):
    def __init__(self, path=None, **kwargs):
        """Open, read and attach - as :attr:`x` - a slice of netCDF data.

        :param path: path to the netCDF file to open

        Keyword arguments::

            **var** - the variable in the netCDF dataset to read
            **dim** - the dimension along which to slice the data (each processor gets len(dim) / nproc of the data)
            **copy** - development hack to copy the data (``x``) over to a fresh instance of :class:`Data`

        Either **var** and **dim** or **copy** are needed. Any additional **kwargs** should be in the form of ``name=slice()``, where **name** refers to a dimension name, and the corresponding slice will be applied to the read operation.

        Attributes::

            **x** - the data
            **read_time** - the wall time needed to read the data

        """
        if 'copy' in kwargs:
            copy = kwargs.pop('copy')
            for a in ['x', 'netcdf', 'var', 'mpi_dim', 'slices']:
                setattr(self, a, getattr(copy, a))
        else:
            start = MPI.Wtime()
            self.netcdf = Dataset(path, parallel=True, comm=MPI.COMM_WORLD)
            self.var = self.netcdf[kwargs.pop('var')]
            self.mpi_dim = kwargs.pop('dim')
            n = int(self.netcdf[self.mpi_dim].shape[0] / MPI.COMM_WORLD.Get_size())
            self.slices = self._slicer(n, **kwargs)
            self.x = self.var[self.slices]
            self.read_time = MPI.Wtime() - start

    def _slicer(self, n = None, **kwargs):
        slices = []
        rank = MPI.COMM_WORLD.rank
        for d in self.var.dimensions:
            if d == self.mpi_dim and n is not None:
                slices.append(slice(rank * n, (rank+1) * n))
            elif d in kwargs:
                slices.append(kwargs[d])
            else:
                slices.append(slice(None))
        return slices

    def xr_wrap(self, time='time'):
        import xarray as xr
        coords = []
        for d in range(self.var.ndim):
            if self.var.shape[d] > 1:
                name = self.var.dimensions[d]
                var = self.netcdf[name]
                if var.name == time:
                    coords.append((name, num2date(var[:], var.units)))
                else:
                    coords.append((name, var[self.slices[d]]))
        self.xr = xr.DataArray(self.x.squeeze(), coords=coords)

    def np_op(self, op, **kwargs):
        x = self.x[self._slicer(**kwargs)] if len(kwargs) > 0 else self.x
        start = MPI.Wtime()
        ax, func = op.popitem()
        dim = self.var.dimensions.index(ax)
        self.op_time = MPI.Wtime() - start
        return getattr(x, func)(dim)

    def trend(self, ax):
        start = MPI.Wtime()
        n = x.shape[ax]
        i = list(range(x.ndim))
        i.remove(ax)
        i.append(ax)
        x = self.x.transpose(i).reshape((-1, n)).T
        t = np.r_['1', np.ones((n, 1)), np.arange(n).reshape((-1, 1))]
        return np.linalg.lstsq(t, x)[0][1, :], self.dim, self.read_time, MPI.Wtime() - start

# rearrangement for the np-function call
def concat_np(view, var, dim):
    import numpy as np
    i = np.argsort(view['mpicdf.MPI.COMM_WORLD.rank'])
    return np.concatenate(np.array(view[var])[i], dim).squeeze()

def concat_xr(view, var, dim):
    import xarray as xr
    return xr.concat(view[var], dim).sortby(dim)

# rearrangement for the 'trend' function call
def concat_trend(view, var):
    x = sorted(var, key=lambda z: z[1][0])
    return np.concatenate([z[0].reshape((192, -1)) for z in x], 1)
