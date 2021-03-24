#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar 19 15:37:45 2021

@author: ian
"""
import param
import numpy as np
from datetime import datetime
import pandas as pd
import gimpfunc as gimp
import panel as pn


products = ['NSIDC-0642',
            'NSIDC-0723',
            'NSIDC-0725', 'NSIDC-0727', 'NSIDC-0731']

velocityOptions = ['browse', 'speed', 'velocity', 'velocity+errors', 'all']
productOptions = {'NSIDC-0642': ['termini'],
                  'NSIDC-0723': ['image', 'gamma0', 'sigma0'],
                  'NSIDC-0725': velocityOptions,
                  'NSIDC-0727': velocityOptions,
                  'NSIDC-0731': velocityOptions,

                  }
versions = {'NSIDC-0723': '3', 'NSIDC-0725': '2', 'NSIDC-0727': '2',
            'NSIDC-0731': '2', 'NSIDC-0642': '1'}
defaultProduct = 'NSIDC-0723'

productGroups = {'browse': ['browse'],
                 'speed': ['vv'],
                 'velocity': ['vv', 'vx', 'vy'],
                 'velocity+errors': ['vv', 'vx', 'vy', 'ex', 'ey', 'dT'],
                 'sigma0': ['sigma0'],
                 'gamma0': ['gamma0'],
                 'image':  ['image'],
                 'termini': ['termini']
                 }
fileTypes = dict.fromkeys(productGroups.keys(), ['.tif'])  # Set all to tif
fileTypes['termini'] = ['.shp', '.dbf', '.prj', '.sbx', '.shx']  # shp


class cmrUrls(param.Parameterized):
    '''Class to allow user to select product params and then search for
    matching data'''
    # product Information

    # Date range for search
    firstDate = param.CalendarDate(default=datetime(2000, 1, 1).date())
    lastDate = param.CalendarDate(default=datetime.today().date())
    # Select Product
    product = param.ObjectSelector(defaultProduct, objects=products)
    productFilter = param.ObjectSelector(
        productOptions[defaultProduct][0],
        objects=productOptions[defaultProduct])
    #
    getData = param.Boolean(False)
    clearSearch = param.Boolean(False)
    first = True
    cogs = []
    urls = []
    productList = []
    dates = []
    msg = 'Init'
    # initialize with empty list
    results = pd.DataFrame()

    def getCogs(self):
        return [x for x in self.urls if x.endswith('.tif')]

    def getShapes(self):
        return [x for x in self.urls if x.endswith('.shp')]

    @param.depends('clearSearch', watch=True)
    def clearData(self):
        self.products = []
        self.urls = []
        self.dates = []
        self.productList = []
        self.results = pd.DataFrame(zip(self.dates, self.productList),
                                    columns=['date', 'product'])
        self.clearSearch = False

    @param.depends('getData', watch=True)
    def findData(self):
        '''Search NASA/NSIDC Catalog for dashboard parameters'''
        # Return if not a button push (e.g., first)
        if not self.getData:
            return
        #
        newUrls = self.getURLS()
        self.msg = len(newUrls)

        self.newProducts(newUrls)
        # append list. Use unique to avoid selecting same data set
        self.urls = list(np.unique(newUrls + self.urls))
        self.results = pd.DataFrame(zip(self.dates, self.productList),
                                    columns=['date', 'product'])
        # reset get Data
        self.getData = False

    def newProducts(self, newUrls):
        ''' Generate a list of the unique products in the url list'''
        fileType = productGroups[self.productFilter][0]
        newProducts = []
        newDates = []
        for url in newUrls:
            if fileType in url:
                productName = url.split('/')[-1]
                newProducts.append(productName)
                newDates.append(url.split('/')[-2])
        self.productList = newProducts + self.productList
        self.dates = newDates + self.dates

    def getURLS(self):
        ''' Get list of URLs for the product '''
        dateFormat1, dateFormat2 = '%Y-%m-%dT00:00:01Z', '%Y-%m-%dT00:23:59'
        version = versions[self.product]  # Current Version for product
        bounding_box, polygon = None, None
        newUrls = []
        self.msg = f'{self.product} {version}'
        self.debug()
        allUrls = gimp.get_urls(self.product, version,
                                self.firstDate.strftime(dateFormat1),
                                self.lastDate.strftime(dateFormat2),
                                bounding_box, polygon, '*')
        # filter urls for ones to keep
        for url in allUrls:
            # get all urls for group (e.g., vx)
            self.msg = fileTypes[self.productFilter]
            self.debug()
            for productGroup in productGroups[self.productFilter]:
                for suffix in fileTypes[self.productFilter]:
                    if productGroup in url and url.endswith(suffix):
                        newUrls.append(url)
        # Return filtered list sorted.
        return sorted(newUrls)

    @param.depends('product', watch=True)
    def setProductOptions(self):
        self.param.productFilter.objects = productOptions[self.product]
        self.productFilter = productOptions[self.product][0]

    def result_view(self):
        return pn.widgets.DataFrame(self.results, height=400,
                                    autosize_mode='fit_columns')

    def displayProductCount(self):
        return pn.pane.Markdown(
            f'### Total Products retrieved {len(self.productList)} with '
            f'{len(self.urls)} Files')

    def debug(self):
        return pn.pane.Markdown(f'debug {self.msg}')

    def view(self):
        ''' Display panel for getting data '''
        # Directions
        directionsPanel = pn.pane.Markdown('''
        ### Instructions:
        Select a product, date, and filter options then press getData to
        retrieve. Repeat procedure to append additional products.
        ''')
        # Data legend
        infoPanel = pn.pane.Markdown('''
        #### Data Types:
        * NSIDC-0723: S1A/B Image mosaics
        * NSIDC-0725: Annual Velocity
        * NSIDC-0727: Quarterly Velocity
        * NSIDC-0731: Monthly Velocity
        ''')

        inputs = pn.Param(self.param,
                          widgets={
                              'product': pn.widgets.RadioButtonGroup,
                              'productFilter': pn.widgets.Select,
                              'firstDate': pn.widgets.DatePicker,
                              'lastDate': pn.widgets.DatePicker,
                              'getData': pn.widgets.Button,
                              'clearSearch': pn.widgets.Button
                              },
                          name='Select Data', width=500)
        return pn.Row(pn.Column(directionsPanel, infoPanel, inputs),
                      pn.Column(self.result_view, self.displayProductCount,
                                self.debug))

    def panel(self):
        return self.view()


#myUrls = cmrUrls()
#myUrls.panel() #add .servable() if deploying via a server