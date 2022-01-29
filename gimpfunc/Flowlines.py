#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jan 29 12:54:33 2022

@author: ian
"""
import geopandas as gpd
import numpy as np
import functools
import matplotlib.pyplot as plt


class Flowlines():
    ''' Class to read and work with flowlines from shape files '''
    shapeParsers = {'felikson': 'parseFelikson'}

    def __init__(self, shapefile=None, shapeFormat='felikson', length=None):
        self.flowlines = {}
        if shapefile is not None:
            self.readShape(shapefile, shapeFormat=shapeFormat)
            self.truncate(None, length=length)

    def readShape(self, shapefile, length=None, pad=10e3, reuse=False,
                  shapeFormat='felikson'):
        '''
        Read a flowline shape file and return a dict with entries:
        {index: {'x': [], 'y': [], 'd': []}
        Parameters
        ----------
        shapefile : str
            Shapefile name with .shp.
        length : float, optional, the default is 50e3.
            if length > 0, keep the first part of the profile
            if length < 0, keep the last section of the profile
         pad : float, optional
            pad for bounding box. The default is 10e3.
        reuse : bool, optional
            Skip file read and used cached pandas table. The default is False.
        shapeFormat : str, optional
            Specify the parser function for the shapefile. The default is
            'felikson'.
        Returns
        -------
        None.

        '''
        if not reuse:
            self.shapeTable = gpd.read_file(shapefile)
        self.flowlines = {}
        getattr(self, self.shapeParsers[shapeFormat])()
        self.computeBounds(pad=pad)

    def parseFelikson(self):
        '''
        Parse lines from Felikson flowlines from
        https://zenodo.org/record/4284759#.YfWxl4TMLLR
        Returns
        -------
        None.
        '''
        for index, row in self.shapeTable.iterrows():  # loop over features
            fl = {}  # New Flowline
            fl['x'], fl['y'] = np.array(
                [c for c in row['geometry'].coords]).transpose()
            # Compute distance along profile
            fl['d'] = self.computeDistance(fl['x'], fl['y'])
            self.flowlines[row['flowline']] = fl

    def truncate(self, indices, length=50e3, pad=10e3):
        '''
        Parameters
        ----------
        indices : list of indices of flowlines to truncate
            DESCRIPTION.
        length : float, optional, the default is 50e3.
            if length > 0, keep the first part of the profile
            if length < 0, keep the last section of the profile
        pad : float, optional
            pad for bounding box. The default is 10e3.
        Returns
        -------
        None.
        '''
        if length is None:
            return
        if indices is None:
            indices = self.flowlines.keys()
        elif type(indices) is not list:
            indices = [indices]
        # determine portion of profile to keep
        for i in indices:
            if length > 0:
                keep = self.flowlines[i]['d'] < length
            else:
                keep = self.flowlines[i]['d'] > (self.flowlines[i]['d'][-1] +
                                                 length)
            # clip
            for key in ['x', 'y', 'd']:
                self.flowlines[i][key] = self.flowlines[i][key][keep]
        # Update bounding box
        self.computeBounds(pad=pad)

    def computeDistance(self, x, y):
        '''
        Compute distance along a flowline from x and y coordinates.
        Parameters
        ----------
        x, y : np.array
            x, y coordinates.
        Returns
        -------
        np.array
            Distance along profile.
        '''
        dl = np.zeros(x.shape)
        dl[1:] = np.sqrt(np.diff(x)**2 + np.diff(y)**2)
        return np.cumsum(dl)

    def computeBounds(self, pad=10e3):
        '''
        Compute the padded bounding the box for the profiles
        self.bounds = {'minx': ...'maxy': }
        Parameters
        ----------
        pad : float, optional
            Additial padd around the bounding box. The default is 10e3.
        Returns
        -------
        None.

        '''
        self.bounds = {'minx': 1e9, 'miny': 1e9, 'maxx': -1e9, 'maxy': -1e9}
        for fl in self.flowlines.values():

            values = np.around([np.min(fl['x']) - pad, np.min(fl['y']) - pad,
                                np.max(fl['x']) + pad, np.max(fl['y']) + pad],
                               - 2)
            self.bounds = self.mergeBounds(self.bounds, dict(zip(
                self.bounds.keys(), values)))

    def mergeBounds(self, bounds1, bounds2):
        '''
        Merge two bounding bounding boxes as the union of the extents.
        Parameters
        ----------
        bounds1, bounds2 : bounding box dicts
            {'minx': ..., 'miny': ..., 'maxx': ..., 'maxy': ...}.
        Returns
        -------
        bounds1 : bounding box dict
            Merged box.
        '''
        merged = {}
        for c in ['x', 'y']:
            merged[f'min{c}'] = np.min([bounds1[f'min{c}'],
                                        bounds2[f'min{c}']])
            merged[f'max{c}'] = np.max([bounds1[f'max{c}'],
                                        bounds2[f'max{c}']])
        return merged

    def _toKm(func):
        '''
        Decorator for unit conversion
        Parameters
        ----------
        func : function
            function to be decorated.
        Returns
        -------
        float
            Coordinates converted to km from m.
        '''
        @functools.wraps(func)
        def convertKM(*args, **kwargs):
            result = func(*args, **kwargs)
            if type(result) is not tuple:
                return result * 0.001
            else:
                return [x*0.001 for x in result]
        return convertKM

    def xym(self, index=None):
        '''
        Return the x and y flowline coordinates in meters
        Parameters
        ----------
        index : str, optional
            Index of flowline, defaults to the first flowline for if None.
        Returns
        -------
        np.array, np.array
            x, y in coordinates in m
        '''
        if index is None:
            index = list(self.flowlines)[0]
        return self.flowlines[index]['x'], self.flowlines[index]['y']

    @_toKm
    def xykm(self, index=None):
        '''
        Return the x and y flowline coordinates in KILOmeters
        Parameters
        ----------
        index : str, optional
            Index of flowline, defaults to the first flowline for if None.
        Returns
        -------
        np.array, np.array
            x, y in coordinates in km
        '''
        return self.xym(index=index)

    def distancem(self, index=None):
        '''
        Return the distance along a flowline in m.
        Parameters
        ----------
        index : str, optional
            Index of flowline, defaults to the first flowline for if None.
        Returns
        -------
        np.array
            distance along a flowline.
        '''
        if index is None:
            index = list(self.flowlines)[0]
        return self.flowlines[index]['d']

    @_toKm
    def distancekm(self, index=None):
        '''
        Return the distance along a flowline in KILOmeters.
        Parameters
        ----------
        index : str, optional
            Index of flowline, defaults to the first flowline for if None.
        Returns
        -------
        np.array
            distance along a flowline.
        '''
        return self.distancem(index=index)

    def plotFlowlineLocations(self, ax=plt, units='m', indices=None, **kwargs):
        '''
        Plot all flowline locations or a single location given by index
        Parameters
        ----------
        ax : matplotlib ax, optional
            The axis used for the plot. The default is plt.
        units : str, optional
            Units 'm' or 'km'. The default is 'm'.
        index : TYPE, optional
            DESCRIPTION. The default is None.
        **kwargs : TYPE
            DESCRIPTION.

        Returns
        -------
        None.
        '''
        coords = {'m': self.xym, 'km': self.xykm}
        if units not in ['m', 'km']:
            print('Invalid units: must be m or km, reverting to m')
            units = 'm'
        if indices is None:
            lines = self.flowlines.keys()
        else:
            lines = [indices]
        # plot lines
        for line in lines:
            ax.plot(*coords[units](index=line), label=line, **kwargs)
