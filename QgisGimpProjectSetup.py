#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar 17 10:47:23 2021

@author: ian
"""
import glob
from copy import deepcopy
import numpy as np

productFamilyTemplate = {'topDir': None,
                         'productFilePrefix': None,
                         'bands': [], 'fileType': 'tif', 'products': None,
                         'byYear': True, 'productPrefix': None,
                         'basePath': None, 'category': None,
                         'displayOptions': None}

displayDefaults = {'image': {'colorTable': None, 'minV': None, 'maxV': None,
                             'opacity': 1., 'invert': False},
                   'sigma0': {'colorTable': 'Greys', 'minV': -20, 'maxV': 5,
                              'opacity': 1., 'invert': True},
                   'gamma0': {'colorTable': 'Greys', 'minV': -20, 'maxV': 5,
                              'opacity': 1, 'invert': True},
                   'browse': {'colorTable': None, 'opacity': 0.7,
                              'invert': False},
                   'vv': {'colorTable': 'Blues', 'minV': 0, 'maxV': 1500,
                          'opacity': 1, 'invert': False},
                   'vx': {'colorTable': 'RdBu', 'minV': -1000, 'maxV': 1000,
                          'opacity': 1, 'invert': False},
                   'vy': {'colorTable': 'RdBu', 'minV': -1000, 'maxV': 1000,
                          'opacity': 1, 'invert': False},
                   'ex': {'colorTable': 'YlGn', 'minV': 0, 'maxV': 20,
                          'opacity': 1, 'invert': False},
                   'ey': {'colorTable': 'YlGn', 'minV': 0, 'maxV': 20,
                          'opacity': 1, 'invert': False},
                   }


class QgisGimpProjectSetup:
    """ An object for the class is used to collect all of the data needed
    to build a QGIS project"""

    def __init__(self, defaultBasePath=None):
        '''
        Init

        Parameters
        ----------
        defaultBasePath : str, optional
            If given, path to where produce files are located. If not urls
            are used. The default is None.
        Returns
        -------
        None.
        '''
        self.productFamilies = {}
        self.setDefaultBasePath(defaultBasePath)

    def setDefaultBasePath(self, defaultBasePath):
        """ Set the base path for the files.
        Parameters
        ----------
        basePath : str
            Path to GIMP product directory.
        """
        self.defaultBasePath = defaultBasePath

    def addProductFamilies(self, *productFamilies, **kwargs):
        """ Add a product Family to the project (e.g., monthlyMosaics)
        Parameters
        ----------
        *args : str
            Arbitrary number of product types to add to project.
        **kwargs: optional arguments
        """
        for productFamily in productFamilies:  # loop through
            self.productFamilies[productFamily] = \
                self._defaultProductFamily(productFamily,
                                           **kwargs)

    def productCategories(self):
        ''' Return list of product categories'''
        categories = [x['category'] for x in self.productFamilies.values()
                      if x['category'] is not None]
        return list(np.unique(categories))

    def updateProductFamily(self, productFamilyKey, **kwargs):
        ''' Changed the properties for an existing product type as
        indicated by the keywords.
         Parameters
        ----------
        productFamilyKey : str
            key in the the productFamilies dict (e.g., "annualMosaics")
         **kwargs : dict of keywords, or explicit keywords
            Keywords used to populate product specs.
        '''
        self.addProductFamilyProperties(self.productFamilies[productFamilyKey],
                                        **kwargs)

    def addProductFamilyProperties(self, productFamily, **kwargs):
        """ Update dictionary for 'product' with keyword specified values
        defined by productTemplate
        Parameters
        ----------
        productFamily : str
            productFamily key.
        **kwargs : dict of keywords, or explicit keywords
            Keywords used to populate product specs.
        """
        # print(productFamily)
        for kwarg in kwargs:
            if kwarg in productFamilyTemplate.keys():
                productFamily[kwarg] = kwargs[kwarg]
            else:
                print(f'{kwarg} is not a valid keyword\nValid keywords are:')
                for kw in productFamilyTemplate:
                    print(f'{kw} [{productFamilyTemplate[kw]}]')
        if productFamily['products'] is None:
            productFamily['products'] = {}
            for band in productFamily['bands']:
                productFamily['products'][band] = []

    def getProductFamilies(self, urls=None):
        """ Get the files for the each of the productFamilies
        """
        for productFamily in self.productFamilies:
            self.getProducts(self.productFamilies[productFamily], urls=urls)

    def fileFound(self, urlFile, productFamily):
        ''' See if a url belongs to a product Family '''
        for x in ['productFilePrefix', 'fileType']:
            if productFamily[x] not in urlFile:
                return False
        return True

    def filterUrls(self, urls, band, productFamily):
        ''' Given a list of urls, return all for requested band and
        productFamily '''
        foundUrls = []
        for url in urls:
            urlFile = url.split('/')[-1]
            # the band not found so skip this file
            if band not in urlFile:
                continue
            # Skip if prefix (e.g., S1_bks) or type (tif) not correct
            if not self.fileFound(urlFile, productFamily):
                continue  # Skip this url if no match
            # Passed all tests, so add to list
            option = ''
            if urlFile.endswith('tif'):
                option = '?list_dir=no'
            # print(url)
            foundUrls.append(f'/vsicurl/{option}&url={url}')
        return foundUrls

    def getProducts(self, productFamily, urls=None):
        """ Get the files for a specific productFamily
        Parameters
        ----------
        productFamily : dict
            Product type parameter dictionary.
        """
        for band in productFamily['bands']:
            if urls is None:
                myPath = '/'.join([productFamily['basePath'],
                                   productFamily['topDir'],
                                   productFamily['productFilePrefix'],
                                   f'*{band}*.{productFamily["fileType"]}'])
                productFamily['products'][band] += sorted(glob.glob(myPath))
                # print(myPath,'\n',productFamily)
            else:
                foundUrls = self.filterUrls(urls, band, productFamily)
                if len(foundUrls) > 0:
                    productFamily['products'][band] = foundUrls

    def defaultDisplayOptions(self):
        ''' Return a copy of the default display options '''
        return deepcopy(displayDefaults)

    def _defaultProductFamily(self, productFamilyName, **kwargs):
        """ Create a default product dictionary """
        newProductFamily = deepcopy(productFamilyTemplate)
        # Default to product name
        newProductFamily['topDir'] = productFamilyName
        newProductFamily['name'] = productFamilyName
        newProductFamily['basePath'] = self.defaultBasePath
        newProductFamily['displayOptions'] = deepcopy(displayDefaults)
        self.addProductFamilyProperties(newProductFamily, **kwargs)
        return newProductFamily
