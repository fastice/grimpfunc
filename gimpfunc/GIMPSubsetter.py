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
import stackstac
import datetime
import numpy as np
import rio_stac
import pystac

CHUNKSIZE = 512

productTypeDict = {'velocity': {'bands': ['vv', 'vx', 'vy'], 'template': 'vv'},
                   'image': {'bands': ['image'], 'template': 'image'},
                   'gamma0': {'bands': ['gamma0'], 'template': 'gamma0'},
                   'sigma0': {'bands': ['sigma0'], 'template': 'sigma0'}}

# valid bands and the reference url type
# NOTE NSIDC-0481: TSX Individual Glacier Velocity resolution=100
# Other resolutions = 200m
bandsDict = {'vv': {'template': 'vv', 'noData': -1., 'name': 'velocity'},
             'vx': {'template': 'vv', 'noData': -2.e9, 'name': 'velocity'},
             'vy': {'template': 'vv', 'noData': -2.e9, 'name': 'velocity'},
             'ex': {'template': 'vv', 'noData': -1., 'name': 'velocity'},
             'ey': {'template': 'vv', 'noData': -1., 'name': 'velocity'},
             'dT': {'template': 'vv', 'noData': -2.e9, 'name': 'velocity'},
             'image': {'template': 'image', 'noData': 0, 'dtype': 'uint8',
                       'resolution': 25, 'name': 'image'},
             'gamma0': {'template': 'gamma0', 'noData': -30.,
                        'dtype': 'float32', 'resolution': 50,
                        'name': 'gamma0'},
             'sigma0': {'template': 'sigma0', 'noData': -30.,
                        'dtype': 'float32', 'resolution': 50, 'name': 'sigma0'}
             }


class GIMPSubsetter():
    ''' Class to open remote data set and create a rioxarry. The result can
    then be cropped to create a subset, which can then be saved to a netcdf'''

    def __init__(self, bands=['vv'], urls=None, tiffs=None):
        self.urls = urls
        self.tiffs = tiffs
        self.DA = None
        self.dataArrays = None
        self.subset = None
        self.bands = self._checkBands(bands)

    def get_stac_item_template(self, URLs):
        '''
        read first geotiff to get STAC Item template (returns pystac.Item)
        '''
        first_url = URLs[0]

        date = datetime.datetime.strptime(first_url.split('/')[-2], '%Y.%m.%d')
        # collection = first_url.split('/')[-3],

        item = rio_stac.create_stac_item(first_url,
                                         input_datetime=date,
                                         asset_media_type=str(
                                             pystac.MediaType.COG),
                                         with_proj=True,
                                         with_raster=True,
                                         )
        # Could remove: #['links'] #['assets']['asset']['roles']
        # Remove statistics and histogram, b/c only applies to first
        item.assets['asset'].extra_fields['raster:bands'][0].pop('statistics')
        item.assets['asset'].extra_fields['raster:bands'][0].pop('histogram')

        return item

    def construct_stac_items(self, URLs):
        ''' construct STAC-style dictionaries of CMR urls for stackstac '''

        item_template = self.get_stac_item_template(URLs)
        asset_template = item_template.assets.pop('asset')
        band_template = asset_template.href.split('/')[-1].split('_')[-3]

        ITEMS = []
        for url in URLs:
            item = item_template.clone()
            # works with single asset per item datasets (e.g. only gamma0 urls)
            item.id = os.path.basename(url)
            item.datetime = datetime.datetime.strptime(url.split('/')[-2],
                                                       '%Y.%m.%d')
            for band in self.bands:
                asset_template.href = url.replace(band_template, band)
                item.add_asset(band, asset_template)

            ITEMS.append(item.to_dict())

        return ITEMS

    def lazy_open_stackstac(self, items):
        ''' return stackstac xarray dataarray '''
        da = stackstac.stack(items,
                             assets=self.bands,
                             chunksize=CHUNKSIZE,
                             # NOTE: use native projection, match rioxarray
                             snap_bounds=False,  # default=True
                             xy_coords='center',  # default='topleft'
                             )
        da = da.rename(band='component')
        return da

    @dask.delayed
    def lazy_openTiff(self, tiff, masked=False, productType='velocity'):
        ''' Lazy open of a single url '''
        # print(href)d
        if productType not in productTypeDict.keys():
            print(f'Warning in valid productType: {productType}')
            return None
        das = []
        for band in self.bands:
            template = bandsDict[band]['template']
            filename = tiff.split('/')[-1]
            tmp = tiff.split('/')[-3].replace('Vel-', '')
            date1 = tmp.split('.')[0]
            date2 = tmp.split('.')[1]
            bandTiff = tiff.replace(template, band)
            # create rioxarry
            da = rioxarray.open_rasterio(bandTiff, lock=False,
                                         default_name=bandsDict[band]['name'],
                                         chunks=dict(band=1,
                                                     y=CHUNKSIZE, x=CHUNKSIZE),
                                         masked=masked).rename(
                                             band='component')
            da['component'] = [band]
            da['time'] = pd.to_datetime(date1) + \
                (pd.to_datetime(date2) - pd.to_datetime(date1)) * 0.5
            da['name'] = filename
            da['_FillValue'] = bandsDict[band]['noData']
            das.append(da)
        # Concatenate bands (components)
        return xr.concat(das, dim='component', join='override',
                         combine_attrs='drop')

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
                                         chunks=dict(band=1,
                                                     y=CHUNKSIZE, x=CHUNKSIZE),
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
            # print(bands, self.bands)
            return self.bands
        for band in bands:
            if band not in bandsDict:
                print(f'\x1b[1;33mIgnoring Invalid Band: {band}.\x1b[0m\n'
                      f'Allowed bands: {list(bandsDict.keys())}')
                bands.remove(band)
        return bands

    def loadStackStac(self, bands=None):
        ''' construct dataarray with stackstac '''
        self.bands = self._checkBands(bands)
        items = self.construct_stac_items(self.urls)
        self.DA = self.lazy_open_stackstac(items)

    def loadDataArray(self, bands=None):
        ''' Load and concatenate arrays to create a rioxArray with coordinates
        time, component, y, x'''
        # NOTE: can have server-size issues w/ NSIDC if going above 15 threads
        # if psutil.cpu_count() > 15: num_threads = 12
        self.bands = self._checkBands(bands)
        with dask.config.set({'scheduler': 'threads', 'num_workers': 8}):
            if self.urls is not None:
                self.dataArrays = dask.compute(
                    *[self.lazy_open(url, masked=False) for url in self.urls])
            else:
                self.dataArrays = dask.compute(
                    *[self.lazy_openTiff(tiff, masked=False)
                      for tiff in self.tiffs])
        # Concatenate along time dimensions
        self.DA = xr.concat(self.dataArrays, dim='time', join='override',
                            combine_attrs='drop')

    def subSetData(self, bbox):
        ''' Subset dataArray with
        bbox = {'minx': minx, 'miny': miny, 'maxx': maxx, 'maxy': maxy}
        '''
        self.subset = self.DA.rio.clip_box(**bbox)
        return self.subset

    def saveAll(self, cdfFile, numWorkers=4):
        ''' Save the entire data array as a subset of the entire extent'''
        self.subSetToNetCDF(cdfFile, bbox=self.getBounds(),
                            numWorkers=numWorkers)

    def subSetToNetCDF(self, cdfFile, bbox=None, numWorkers=1):
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
