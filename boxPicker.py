#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Apr  9 13:03:41 2021

@author: ian
"""

import panel as pn
import holoviews as hv
import hvplot.xarray
import gimpfunc as gimp
import rioxarray
import os
import yaml
import numpy as np

boxDefault = {'minx': -243500, 'miny': -2295000, 'maxx': -149000,
              'maxy': -2255000}


class boxPicker():
    ''' Pick a box on a SAR map '''

    def __init__(self, mapUrl=None, bbox=boxDefault, boxFile=None):
        self.mapUrl = mapUrl
        if self.mapUrl is None:
            self.mapUrl = self._getDefaultMap()
        env = dict(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR')
        os.environ.update(env)
        # Read box from file - will override bbox
        if boxFile is not None:
            bbox = self.readBox(boxFile)
        # Avoids error if user passes undefined bbox in notebook
        try:
            self.box = hv.streams.BoundsXY(bounds=tuple(bbox.values()))
        except Exception:
            self.box = hv.streams.BoundsXY(bounds=tuple(boxDefault.values()))

    def _getDefaultMap(self):
        ''' Get the latest version of a in image map '''
        version = 3
        # Increment version if not found
        for i in range(0, 5):
            urls = gimp.get_urls('NSIDC-0723', str(int(version) + i),
                                 '2020-01-01T00:00:01Z', '2020-01-05T00:23:59',
                                 None, None, '*image*')
            if len(urls) > 0:
                return list(filter(lambda x: '.tif' in x, urls))[0]
        print('Warning could not find default map')

    def plotMap(self):
        ''' Plot the map'''
        da = rioxarray.open_rasterio(self.mapUrl, overview_level=3,
                                     chunks=dict(band=1, y="auto", x=-1),
                                     masked=False).squeeze('band')
        da = da.rename(dict(x='easting', y='northing'))
        img = da.hvplot.image(rasterize=True, cmap='gray',
                              aspect='equal', frame_width=400,
                              title=os.path.basename(self.mapUrl)
                              ).opts(active_tools=['box_select'])
        self.box.source = img
        bounds = hv.DynamicMap(lambda bounds: hv.Bounds(bounds),
                               streams=[self.box]).opts(color='red')
        mapview = pn.Column(img * bounds)
        return mapview

    def boxBounds(self, decimals=-3):
        ''' Return a dictionary with bounding box '''
        keys = ['minx', 'miny', 'maxx', 'maxy']
        bounds = tuple(np.around(self.box.bounds, decimals=decimals))
        return dict(zip(keys, bounds))

    def saveBox(self, boxFile):
        ''' Save the box to a yaml file'''
        if not boxFile.endswith('.yaml'):
            boxFile += '.yaml'
        with open(boxFile, 'w') as fp:
            yaml.dump(self.boxBounds(), fp)

    def readBox(self, boxFile):
        ''' Read a box file '''
        if not boxFile.endswith('.yaml'):
            boxFile += '.yaml'
        # Existence check
        if not os.path.exists(boxFile):
            print('readBox: Box file does not not exist, using default box')
            return boxDefault
        # read the box
        with open(boxFile, 'r') as fp:
            bbox = yaml.load(fp, Loader=yaml.FullLoader)
        return bbox
