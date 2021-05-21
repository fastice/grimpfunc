#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr  7 08:43:45 2021

@author: ian basedon prototype by Scott Henderson
"""

import xarray as xr
import rioxarray
import os
import dask
import pandas as pd
# from dask.diagnostics import ProgressBar

# ProgressBar().register()

productTypeDict = {'velocity': {'bands': ['vv', 'vx', 'vy'], 'template': 'vv'},
                   'image': {'bands': ['image'], 'template': 'image'},
                   'gamma0': {'bands': ['gamma0'], 'template': 'gamma0'},
                   'sigma0': {'bands': ['sigma0'], 'template': 'sigma0'}}

# valid bands and the reference url type
bandsDict = {'vv': {'template': 'vv', 'noData': -1., 'name': 'velocity'},
             'vx': {'template': 'vv', 'noData': -2.e9, 'name': 'velocity'},
             'vy': {'template': 'vv', 'noData': -2.e9, 'name': 'velocity'},
             'ex': {'template': 'vv', 'noData': -1., 'name': 'velocity'},
             'ey': {'template': 'vv', 'noData': -1., 'name': 'velocity'},
             'dT': {'template': 'vv', 'noData': -2.e9, 'name': 'velocity'},
             'image': {'template': 'image', 'noData': 0, 'name': 'image'},
             'gamma0': {'template': 'gamma0', 'noData': -30.,
                        'name': 'gamma0'},
             'sigma0': {'template': 'sigma0', 'noData': -30., 'name': 'sigma0'}
             }


class GIMPSubsetter():
    ''' Class to open remote data set and create a rioxarry. The result can
    then be cropped to create a subset, which can then be saved to a netcdf'''

    def __init__(self, bands=['vv'], urls=None):
        self.urls = urls
        self.DA = None
        self.dataArrays = None
        self.subset = None
        self.bands = self._checkBands(bands)

    @dask.delayed
    def lazy_open(self, url, masked=False, productType='velocity'):
        ''' Lazy open of a single url '''
        # print(href)
        if productType not in productTypeDict.keys():
            print(f'Warning in valid productType: {productType}')
            return None
        das = []
        for band in self.bands:
            template = bandsDict[band]['template']
            filename = url.split('/')[-1]
            date = url.split('/')[-2]
            # print(date, pd.to_datetime(date))
            option = '?list_dir=no'
            # swap temnplate for other bands
            vsicurl = f'/vsicurl/{option}&url={url}'.replace(template, band)
            # create rioxarry
            da = rioxarray.open_rasterio(vsicurl, lock=False,
                                         default_name=bandsDict[band]['name'],
                                         chunks=dict(band=1, y='auto', x=-1),
                                         masked=masked).rename(
                                             band='component')
            da['component'] = [band]
            da['time'] = pd.to_datetime(date)
            da['name'] = filename
            da['_FillValue'] = bandsDict[band]['noData']
            das.append(da)
        # Concatenate bands (components)
        return xr.concat(das, dim='component', join='override',
                         combine_attrs='drop')

    def getBounds(self):
        ''' Get the bounding box for the data array '''
        bounds = [min(self.DA.x.values), min(self.DA.y.values),
                  max(self.DA.x.values), max(self.DA.y.values)]
        keys = ['minx', 'miny', 'maxx', 'maxy']
        return dict(zip(keys, bounds))

    def _checkBands(self, bands):
        ''' Check valid band types '''
        if bands is None and self.bands is not None:
            print(bands, self.bands)
            return self.bands
        for band in bands:
            if band not in bandsDict:
                print(f'\x1b[1;33mIgnoring Invalid Band: {band}.\x1b[0m\n'
                      f'Allowed bands: {list(bandsDict.keys())}')
                bands.remove(band)
        return bands

    def loadDataArray(self, bands=None):
        ''' Load and concatenate arrays to create a rioxArray with coordinates
        time, component, y, x'''
        # NOTE: can have server-size issues w/ NSIDC if going above 15 threads
        # if psutil.cpu_count() > 15: num_threads = 12
        self.bands = self._checkBands(bands)
        with dask.config.set({'scheduler': 'threads', 'num_workers': 8}):
            self.dataArrays = dask.compute(*[self.lazy_open(url, masked=False)
                                             for url in self.urls])
        # Concatenate along time dimensions
        self.DA = xr.concat(self.dataArrays, dim='time', join='override',
                            combine_attrs='drop')

    def subSetData(self, bbox):
        ''' Subset dataArray with
        bbox = {'minx': minx, 'miny': miny, 'maxx': maxx, 'miny': miny}
        '''
        self.subset = self.DA.rio.clip_box(**bbox)
        return self.subset

    def saveAll(self, cdfFile, numWorkers=4):
        ''' Save the entire data array as a subset of the entire extent'''
        self.subSetToNetCDF(cdfFile, bbox=self.getBounds(),
                            numWorkers=numWorkers)

    def subSetToNetCDF(self, cdfFile, bbox=None, numWorkers=4):
        ''' Write existing subset or update subset. Will append .nc to cdfFile
        if not already present.
        '''
        if bbox is not None:
            self.subSetData(bbox)
        if self.subset is None:
            print('No subset present - set bbox={"minxx"...}')
            return
        if '.nc' not in cdfFile:
            cdfFile = f'{cdfFile}.nc'
        if os.path.exists(cdfFile):
            os.remove(cdfFile)
        # To many workers can cause a failure
        with dask.config.set({'scheduler': 'threads',
                              'num_workers': numWorkers}):
            self.subset.to_netcdf(path=cdfFile)
        return cdfFile
