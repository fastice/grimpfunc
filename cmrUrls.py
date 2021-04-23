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
            'NSIDC-0725', 'NSIDC-0727', 'NSIDC-0731',
            'NSIDC-0481']

velocityOptions = ['browse', 'speed', 'velocity', 'velocity+errors', 'all']
productOptions = {'NSIDC-0642': ['termini'],
                  'NSIDC-0723': ['image', 'gamma0', 'sigma0'],
                  'NSIDC-0725': velocityOptions,
                  'NSIDC-0727': velocityOptions,
                  'NSIDC-0731': velocityOptions,
                  'NSIDC-0481': velocityOptions[1:]}
# Current versions, if versions updated at DAAC, will try later version
versions = {'NSIDC-0723': '3', 'NSIDC-0725': '2', 'NSIDC-0727': '2',
            'NSIDC-0731': '2', 'NSIDC-0642': '1', 'NSIDC-0481': '3'}
defaultProduct = 'NSIDC-0723'

productGroups = {'browse': ['browse'],
                 'speed': ['vv'], '-': ['vv'],
                 'velocity': ['vv', 'vx', 'vy'],
                 'velocity+errors': ['vv', 'vx', 'vy', 'ex', 'ey'],
                 'all': ['vv', 'vx', 'vy', 'ex', 'ey', 'browse', 'dT'],
                 'sigma0': ['sigma0'],
                 'gamma0': ['gamma0'],
                 'image':  ['image'],
                 'termini': ['termini']
                 }
fileTypes = dict.fromkeys(productGroups.keys(), ['.tif'])  # Set all to tif
fileTypes['termini'] = ['.shp']  # shp

defaultBounds = {'LatMin': 60, 'LatMax': 82, 'LonMin': -75, 'LonMax': -5}


class cmrUrls(param.Parameterized):
    '''Class to allow user to select product params and then search for
    matching data'''

    # product Information
    # Select Product
    product = param.ObjectSelector(defaultProduct, objects=products)
    productFilter = param.ObjectSelector(
        productOptions[defaultProduct][0],
        objects=productOptions[defaultProduct])
    # Date range for search
    firstDate = param.CalendarDate(default=datetime(2000, 1, 1).date())
    lastDate = param.CalendarDate(default=datetime.today().date())

    LatMin = pn.widgets.FloatSlider(name='Lat min', disabled=True,
                                    value=defaultBounds['LatMin'],
                                    start=defaultBounds['LatMin'],
                                    end=defaultBounds['LatMax'])
    LatMax = pn.widgets.FloatSlider(name='Lat max', disabled=True,
                                    value=defaultBounds['LatMax'],
                                    start=defaultBounds['LatMin'] + 1,
                                    end=defaultBounds['LatMax'])
    LonMin = pn.widgets.FloatSlider(name='Lon min', disabled=True,
                                    value=defaultBounds['LonMin'],
                                    start=defaultBounds['LonMin'],
                                    end=defaultBounds['LonMax'])
    LonMax = pn.widgets.FloatSlider(name='Lon max', disabled=True,
                                    value=defaultBounds['LonMax'],
                                    start=defaultBounds['LonMin'] + 1,
                                    end=defaultBounds['LonMax'])
    #
    Search = param.Boolean(False)
    Clear = param.Boolean(False)
    results = pd.DataFrame()

    def __init__(self, mode='none'):
        super().__init__()
        # Adjust options if subsetter mode
        self.mode = mode.lower()
        if self.mode == 'subsetter':
            self.param.Clear.precedence = -1
            for prod in ['NSIDC-0725', 'NSIDC-0727', 'NSIDC-0731']:
                productOptions[prod] = ['-']
            productOptions['NSIDC-0481'] = self.TSXBoxNames()
            for x in productOptions['NSIDC-0481']:
                productGroups[x] = ['vv']
                fileTypes[x] = ['.tif']
            self.param.product.objects = self.param.product.objects[1:]
        #self.productGroups = productGroups
        self.first = True
        self.cogs = []
        self.urls = []
        self.nUrls = 0
        self.productList = []
        self.nProducts = 0
        self.newProductCount = 0
        self.dates = []
        self.msg = 'Init'
    # initialize with empty list


    def getCogs(self):
        return [x for x in self.urls if x.endswith('.tif')]

    def getShapes(self):
        return [x for x in self.urls if x.endswith('.shp')]

    @param.depends('Clear', watch=True)
    def clearData(self):
        self.resetData()
        self.Clear = False

    def resetData(self):
        self.products = []
        self.urls = []
        self.nUrls = 0
        self.nProducts = 0
        self.newProductCount = 0
        self.dates = []
        self.productList = []
        self.results = pd.DataFrame(zip(self.dates, self.productList),
                                    columns=['date', 'product'])

    @param.depends('Search', watch=True)
    def findData(self):
        '''Search NASA/NSIDC Catalog for dashboard parameters'''
        # Return if not a button push (e.g., first)
        if not self.Search:
            return
        #
        if self.mode == 'subsetter':  # Start fresh for each search
            self.resetData()
        #
        newUrls = self.getURLS()
        self.msg = len(newUrls)
        # append list. Use unique to avoid selecting same data set
        self.urls = list(np.unique(newUrls + self.urls))
        self.nUrls = len(self.urls)
        self.updateProducts(newUrls)
        self.results = pd.DataFrame(zip(self.dates, self.productList),
                                    columns=['date', 'product'])
        # reset get Data
        self.Search = False

    def updateProducts(self, newUrls):
        ''' Generate a list of the products in the url list'''
        fileType = productGroups[self.productFilter][0]
        oldCount = self.nProducts
        # update list
        for url in newUrls:
            for fileType in productGroups[self.productFilter]:
                if fileType in url:
                    productName = url.split('/')[-1]
                    self.productList.append(productName)
                    self.dates.append(url.split('/')[-2])
        self.productList, uIndex = np.unique(self.productList,
                                             return_index=True)
        self.productList = list(self.productList)
        self.nProducts = len(self.productList)
        self.dates = [self.dates[i] for i in uIndex]
        self.newProductCount = self.nProducts - oldCount

    def boundingBox(self):
        ''' Create bounding box string for search'''
        return f'{self.LonMin.value:.2f},{self.LatMin.value:.2f},' \
            f'{self.LonMax.value:.2f},{self.LatMax.value:.2f}'

    def getURLS(self):
        ''' Get list of URLs for the product '''
        dateFormat1, dateFormat2 = '%Y-%m-%dT00:00:01Z', '%Y-%m-%dT00:23:59'
        version = versions[self.product]  # Current Version for product
        polygon = None
        bounding_box = self.boundingBox()
        pattern = '*'
        if self.mode == 'subsetter' and self.product == 'NSIDC-0481':
            pattern = f'*{self.productFilter}*'  # Include TSX box for subset
        newUrls = []
        # Future proof by increasing version if nothing found
        for i in range(0, 5):
            allUrls = gimp.get_urls(self.product, str(int(version) + i),
                                    self.firstDate.strftime(dateFormat1),
                                    self.lastDate.strftime(dateFormat2),
                                    bounding_box, polygon, pattern)
            if len(allUrls) > 0:  # Some found so assume version current
                break
        for url in allUrls:
            # get all urls for group (e.g., vx)
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
        # Reset lat/lon bounds
        for coord in ['LatMin', 'LatMax', 'LonMin', 'LonMax']:
            if self.product not in ['NSIDC-0481']:
                getattr(self, coord).value = defaultBounds[coord]
                getattr(self, coord).disabled = True
            else:
                getattr(self, coord).disabled = False

    @param.depends('LatMin.value', watch=True)
    def _latMinUpdate(self):
        ''' Ensure LatMin < LatMax '''
        self.LatMax.value = max(self.LatMax.value, self.LatMin.value + 1.)

    @param.depends('LonMin.value', watch=True)
    def _lonMinUpdate(self):
        ''' Ensure LonMin < LonMax'''
        self.LonMax.value = max(self.LonMax.value, self.LonMin.value + 1.)

    @param.depends('LatMax.value', watch=True)
    def _latMaxUpdate(self):
        ''' Ensure LatMin < LatMax '''
        self.LatMin.value = min(self.LatMin.value, self.LatMax.value - 1.)

    @param.depends('LonMax.value', watch=True)
    def _lonMaxUpdate(self):
        ''' Ensure LonMin < LonMax'''
        self.LonMin.value = min(self.LonMin.value, self.LonMax.value - 1.)

    def result_view(self):
        return pn.widgets.DataFrame(self.results, height=600,
                                    autosize_mode='fit_columns')

    def TSXBoxNames(self):
        ''' Get list of all TSX boxes'''
        date1, date2 = '2009-01-01T00:00:01Z', '2029-01-01T00:00:01Z'
        for i in range(0, 5):
            TSXurls = gimp.get_urls('NSIDC-0481',
                                    str(int(versions['NSIDC-0481']) + i),
                                    date1, date2,
                                    self.boundingBox(), None, '*')
            if len(TSXurls) > 0:
                return self.findTSXBoxes(urls=TSXurls)

    def findTSXBoxes(self, urls=None):
        ''' Return list of unique boxes for the cogs '''
        if urls is None:
            urls = self.getCogs()
        return list(np.unique([x.split('/')[-1].split('_')[1]
                              for x in urls if 'TSX' in x]))

    def displayProductCount(self):
        return pn.pane.Markdown(
            f'### {self.newProductCount} New Products\n'
            f'### {self.nUrls} Total Products')

    def debug(self):
        return pn.pane.Markdown(f'debug {self.msg}')

    def view(self):
        ''' Display panel for getting data '''
        # Directions
        directionsPanel = pn.pane.Markdown('''
        ### Instructions:
        * Select a product, filter (e.g., speed), and date, and bounds
        * Press Search to find products,
        * Repeat procedure to append additional products.
        * Press Clear to remove all results and start over
        ''')
        # Data legend
        names = ['- **NSIDC-0642:** Terminus Locations<br/>',
                 '- **NSIDC-0723:** S1A/B Image Mosaics<br/>',
                 '- **NSIDC-0725:** Annual Velocity<br/>',
                 '- **NSIDC-0727:** Quarterly Velocity<br/>',
                 '- **NSIDC-0731:** Monthly Velocity<br/>',
                 '- **NSIDC-0481:** TSX Individual Glacier Velocity']
        searchWidgets = {'product': pn.widgets.RadioButtonGroup,
                         'productFilter': pn.widgets.Select,
                         'firstDate': pn.widgets.DatePicker,
                         'lastDate': pn.widgets.DatePicker,
                         'Search': pn.widgets.Button}
        if self.mode == 'subsetter':
            names = names[1:]
        #else:  # Non subsetter so include clear
        searchWidgets['Clear'] = pn.widgets.Button
        #
        infoPanel = pn.Row(
            pn.pane.Markdown(
                f'''**Product Key: **<br/>{''.join(names[0:3])}'''),
            pn.pane.Markdown(f'''<br/>{''.join(names[3:])}'''))
        leftWidth = 600
        self.inputs = pn.Param(self.param,
                               widgets=searchWidgets,
                               name='Select Product & Parameters',
                               width=leftWidth)

        panels = [directionsPanel, self.inputs]
        if self.mode != 'subsetter':
            boundsPanel = pn.Column(pn.Row(self.LatMin, self.LatMax),
                                    pn.Row(self.LonMin, self.LonMax))
            boundsLabel = pn.pane.Markdown('###Search Area (NSIDC-481 only)')
            panels += [boundsPanel, boundsLabel]
        panels += [infoPanel]
        return pn.Row(pn.Column(*panels, min_width=leftWidth),
                      pn.Column(self.result_view, self.displayProductCount,
                                self.debug))

    def panel(self):
        return self.view()


# myUrls = cmrUrls()
# myUrls.panel() #add .servable() if deploying via a server