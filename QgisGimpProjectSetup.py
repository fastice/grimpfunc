#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar 17 10:47:23 2021

@author: ian
"""
import glob

productFamilyTemplate = {'name': None, 'topDir': None,
                         'productFilePrefix': None,
                         'bands': [], 'type': 'tif', 'products': None,
                         'byYear': True, 'productPrefix': None,
                         'basePath': None, 'Category': None}


class QgisGimpProjectSetup:
    """ An object for the class is used to collect all of the data needed
    to build a QGIS project"""

    def __init__(self, defaultBasePath='.'):
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

    def addProductFamilies(self, *productFamilies,
                           defaultProperties=productFamilyTemplate):
        """ Add a product Family to the project (e.g., monthlyMosaics)
        Parameters
        ----------
        *args : str
            Arbitrary number of product types to add to project.
        """
        for productFamily in productFamilies:  # loop through
            self.productFamilies[productFamily] = \
                self._defaultProductFamily(productFamily, **defaultProperties)

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
        print(productFamily)
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
            for x in ['productFilePrefix', 'type']:
                # print(x, productFamily[x])
                if productFamily[x] not in urlFile:
                    continue
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
                                   f'*{band}*.{productFamily["type"]}'])
                productFamily['products'][band] += glob.glob(myPath)
            else:
                foundUrls = self.filterUrls(urls, band, productFamily)
                if len(foundUrls) > 0:
                    productFamily['products'][band] = foundUrls


    def _defaultProductFamily(self, productFamilyName, **kwargs):
        """ Create a default product dictionary """
        newProductFamily = productFamilyTemplate.copy()
        # Default to product name
        newProductFamily['topDir'] = productFamilyName
        newProductFamily['name'] = productFamilyName
        newProductFamily['basePath'] = self.defaultBasePath
        self.addProductFamilyProperties(newProductFamily, **kwargs)
        return newProductFamily
