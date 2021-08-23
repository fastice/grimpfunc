#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar 17 14:22:13 2021

@author: ian
"""
import sys
import os
from datetime import datetime
import progressbar

try:
    import qgis.core as qc
    import qgis.gui as qg
    from qgis.PyQt.QtGui import QColor
except Exception:
    # Try anaconda path if not in the default path
    try:
        envName = os.environ["CONDA_DEFAULT_ENV"]
        qgisPath = os.path.expanduser(
            f'~/anaconda3/envs/{envName}/share/qgis/python')
        # qgisPath = '/'.join(sys.executable.split('/')[0:-2]) + \
        #    '/share/qgis/python'
        print(f'Adding {qgisPath} to sys.path')
        sys.path.append(qgisPath)
        import qgis.core as qc
        import qgis.gui as qg
    # unsucessful, print some instructions on how to fix
    except Exception:
        print('\nCould not find path for \033[1mqgis.core\033[0m')
        print(
            '\nFrom QGIS, one can find necessary path information by opening\n'
            'a Python Console (under the Plugins menu) and then doing a\n'
            '\033[1m\timport sys\033[0m \n followed by a \n'
            '\033[1m\tprint(sys.path)\033[0m\n to find the path with:\n'
            '\t\033[1m\033[3m/../qgis/python\033[0m\033[0m\n'
            'Either modify the sys.path.append line with this path in'
            'QgisGimpProject.py\nor update your python path')
        sys.exit()


class QgisGimpProject:
    """ An object for the class is used to collect all of the data needed
    to build a QGIS project using the QGIS python API"""

    def __init__(self, gimpSetup, crs=3413, relative=False, **kwargs):
        '''
        Init
        Parameters
        ----------
        gimpSetup : QgisGimpProjectSetup
            Setup object with all of the nfo.
        crs : int, optional
           epsg code. The default is 3413.
        relative : Bool, optional
            If true paths in QGIS project will be relative rather than
            absolute. The default is False.
        **kwargs : float
            xmin, xmax, ymin, ymax.
        Returns
        -------
        None.

        '''
        self.maxArea = 0
        self.nAdded = 0
        self.extent = None
        self.gimpSetup = gimpSetup
        self.project = qc.QgsProject.instance()
        # Default to absolute paths
        self.project.writeEntry('Paths', 'Absolute', not relative)
        self.project.setCrs(qc.QgsCoordinateReferenceSystem(crs))
        self.root = self.project.layerTreeRoot()
        self.canvas = qg.QgsMapCanvas()
        self._buildProductTree()
        self._checkFirstLayerOfLastGroup(self.root)
        self._setExtent(**kwargs)

    def _setExtent(self, **kwargs):
        ''' Set extent based on default or keyword input.'''
        # Default (Greenland)
        extent = {'xmin': -626000, 'ymin': -3356000,
                  'xmax': 850000, 'ymax': -695000}
        # Overwrite with keywords if specified
        for key in kwargs.keys():
            if key in list(extent.keys):
                extent[key] = kwargs[key]
        # Set extent
        self.canvas.setExtent(qc.QgsRectangle(extent['xmin'], extent['ymin'],
                                              extent['xmax'], extent['ymax']))

    def _checkFirstLayerOfLastGroup(self, group):
        ''' Recursively check move down tree unil layers are found'''
        first = True
        for child in group.children():
            if isinstance(child, qc.QgsLayerTreeGroup):
                child.setItemVisibilityChecked(first)
                first = False
                self._checkFirstLayerOfLastGroup(child)
            else:
                myLayer = self.root.findLayer(child.layer().id())
                # Set first no vector layer
                if myLayer.layer().type() != qc.QgsMapLayerType.VectorLayer:
                    print(myLayer.layer().type())
                    myLayer.setItemVisibilityChecked(True)
                    return

    def _productCount(self):
        ''' Get total number of products included in project '''
        count = 0
        for key in self.gimpSetup.productFamilies:
            productFamily = self.gimpSetup.productFamilies[key]
            for band in productFamily['products']:
                count += len(productFamily['products'][band])
        return count

    def _buildProductTree(self):
        """ Build a tree with root->topDir>products->optionalYear->name or
        Build a tree with root->topDir>products->optionalYear->name->bands
        """
        totalProducts = self._productCount()
        self.nAdded = 0
        # loop through product Families (e.g., annualMosaics, quarterlyMosaics)
        with progressbar.ProgressBar(max_value=totalProducts) as myBar:
            for productFamily in self.gimpSetup.productFamilies:
                # Add the product type to the tree and return the group
                productFamilyGroup = self._addproductFamilyToTree(
                    self.gimpSetup.productFamilies[productFamily])
                # get the list of product sets (e.g., {'vx': [files], 'vy'...)
                productSets = \
                    self.gimpSetup.productFamilies[productFamily]['products']
                for band in productSets:  # Add each list of product in to tree
                    self._addProductBand(band, productFamily,
                                         productSets[band], productFamilyGroup,
                                         myBar)

    def saveProject(self, rootName, append=False):
        if append is False:
            if os.path.exists(f'{rootName}.qgs'):
                os.remove(f'{rootName}.qgs')
        self.project.write(f'{rootName}.qgs')

    def saveLayerDefinitions(self, prefix, saveCategories=False):
        ''' Save layers by productFamily '''
        # Create list of layers to save (productFamilies or Categories)
        if saveCategories:
            toSave = self.gimpSetup.productCategories()
        else:
            toSave = list(self.gimpSetup.productFamilies.keys())
        # Go to layers deep in the and save items in toSave
        for level1 in self.root.children():
            # Process level1
            if level1.name() in toSave:
                fileName = f'{prefix}.{level1.name()}'
                qc.QgsLayerDefinition().exportLayerDefinition(
                    fileName, [level1])
                continue
            # Not found in level1, so try level2
            for level2 in level1.children():
                if level2.name() in toSave:
                    fileName = f'{prefix}.{level2.name()}'
                    qc.QgsLayerDefinition().exportLayerDefinition(
                        fileName, [level2])

    def _getNumberOfBandsWithData(self, productFamily):
        ''' Compute the number of bands that actually have data associated'''
        nBands = 0
        for band in self.gimpSetup.productFamilies[productFamily]['bands']:
            products = \
                self.gimpSetup.productFamilies[productFamily]['products'][band]
            if len(products) > 0:
                nBands += 1
        return nBands

    def _addProductBand(self, band, productFamily, products,
                        productFamilyGroup, myBar):
        '''
        for each band (vx), process list of products (e.g.,[x.vx.tif,
        y.vx.tif....]

        Parameters
        ----------
        band : str
            band indicate (e.g., vx, vy, browse).
        productFamily : qgis group
            Group for a family of products (.
        products : TYPE
            DESCRIPTION.
        productFamily : TYPE
            DESCRIPTION.
      '''
        # file name by product prefix
        baseName = \
            self.gimpSetup.productFamilies[productFamily]["productPrefix"]
        nBands = self._getNumberOfBandsWithData(productFamily)
        for product in products:
            date1, date2 = self._getDates(product)
            dateStr = f'{date1.strftime("%Y-%m-%d")}'
            if date2 is not None:
                dateStr += f'.{date2.strftime("%Y-%m-%d")}'
            # get the group
            if nBands == 1:
                productName = f'{baseName}_{band}_{dateStr}'
                productGroupName = ''
            else:
                productName = f'{band}'
                productGroupName = f'{baseName}_{dateStr}'
            # get the group file product file under
            bandGroup = self._getProductGroup(productFamilyGroup,
                                              productGroupName, productName,
                                              date1, date2, productFamily)
            displayOptions = \
                self.gimpSetup.productFamilies[productFamily]['displayOptions']
            self._addLayerToGroup(bandGroup, product, productName, band,
                                  displayOptions)
            self.nAdded += 1
            myBar.update(self.nAdded)

    def _updateMaxExtent(self, layer):
        ''' Track maximum extent to sent visible area to includ max area'''
        extent = layer.extent()
        area = (extent.xMaximum() - extent.xMinimum()) * \
            (extent.yMaximum() - extent.yMinimum())
        if area > self.maxArea:
            self.maxArea = area
            self.extent = extent

    def _addRasterLayer(self, product, name, band, displayOptions):
        ''' Create raster layer and set display options'''
        # print(name, band)
        # print(displayOptions[band])
        layer = qc.QgsRasterLayer(product, name, 'gdal')
        if displayOptions[band]['colorTable'] is not None:
            self._setLayerColorTable(layer, **displayOptions[band])
            layer.renderer().setOpacity(displayOptions[band]['opacity'])
        return layer

    def _addVectorLayer(self, product, name):
        ''' Create raster layer and set display options'''
        layer = qc.QgsVectorLayer(product, name, 'ogr')  # Vector layer
        symbol = layer.renderer().symbol()
        # Very basic styling - could be updated
        if symbol.type() == 1:  # Line
            symbol.setWidth(0.6)  # Just up line width
        elif symbol.type() == 2:  # Fill
            mySymbol = qc.QgsStyle.defaultStyle().symbol('outline red')
            layer.renderer().setSymbol(mySymbol)
        return layer

    def _addLayerToGroup(self, group, product, name, band, displayOptions):
        ''' Add a product file to the appropriate group '''
        # Handle shape and layer cases
        if product.endswith('tif'):  # Raster layer
            layer = self._addRasterLayer(product, name, band, displayOptions)
        elif product.endswith('shp'):
            layer = self._addVectorLayer(product, name)
        # General layer stuff
        self.project.addMapLayer(layer, False)  # Add it as a map layer
        self._updateMaxExtent(layer)  # track extent
        group.addLayer(layer)  # Added to the group
        # Unexpand color table
        # if product.endswith('tif'):
        self.root.findLayer(layer.id()).setExpanded(False)
        self.root.findLayer(layer.id()).setItemVisibilityChecked(False)

    def _getYearGroup(self, productGroup, year):
        ''' Called if "byYear" to resolve and return correct year group'''
        # loop through group to see if year group already exist, return if so
        for group in productGroup.children():
            if year == group.name():
                group.setItemVisibilityChecked(False)
                group.setExpanded(False)
                return group
        # doesn't already exist, so creat
        return productGroup.addGroup(year)

    def _getProductGroup(self, productFamilyGroup, productGroupName,
                         productName, date1, date2, productFamily):
        '''
        When passed the current product group, dates, and type, find group
        under product is filed
        Parameters
        ----------
        productFamilyGroup : QGIS group
            Group for this product family.
        productGroupName : str
            Name the product is filed under
            Blank for multiband datestr for single.
        productName : str
            Name for product filed under, datestr for single, band for multi.
        date1, date2 : datetime date
            Start and end dates.
        productFamily : dict
            dictionary with all info for this product family.
        Returns
        -------
        group: QGIS group
            The group to add the layer to.
        '''
        # Products aren't filed under year, so return the band group
        if not self.gimpSetup.productFamilies[productFamily]['byYear']:
            return self._getBandGroup(productName, productFamilyGroup,
                                      productFamily)
        # Filed by date, so find and return that group
        midDate = date1
        if date2 is not None:
            midDate += (date2 - date1) * 0.5
        year = str(midDate.year)
        # get the year group
        yearGroup = self._getYearGroup(productFamilyGroup, year)
        # no return the corresponding band group
        return self._getBandGroup(productGroupName, yearGroup, productFamily)

    def _getBandGroup(self, productName, productGroup, productFamily):
        ''' For single "band" products, dont group. But for multi band
        groupd of products (e.g., .vx, .vy) orginize in a group'''
        # if only 1 band, return the product group
        if self._getNumberOfBandsWithData(productFamily) == 1:
            return productGroup
        # For multi band, see if group exists and if not create
        for group in productGroup.children():
            if productName == group.name():
                return group
        return productGroup.addGroup(productName)

    def _getTopGroup(self, productFamily):
        ''' Handle category if needed, and return group above productFamily '''
        if productFamily['category'] is None:
            return self.root
        # Category present, so find or create
        for group in self.root.children():
            if group.name() == productFamily['category']:
                return group
        return self.root.addGroup(productFamily['category'])

    def _addproductFamilyToTree(self, productFamily):
        ''' If it does not already exist, add a product Family to '''
        # Add product name
        topGroup = self._getTopGroup(productFamily)
        for group in topGroup.children():
            if group.name() == productFamily['name']:
                return group
        return topGroup.addGroup(productFamily['name'])

    def _getDates(self, product):
        ''' Extract date from file name. dateLocs defines where to find date
        for a given prefix'''
        # setup table, add to as needed.
        dateLocs = {'GL_vel': (4, 5), 'GL_S1bks': (3, 4), 'TSX': (2, 3),
                    'termini': None}
        # Get dates
        if 'termini' in product:
            date1 = datetime.strptime(product.split('/')[-2], '%Y.%m.%d')
            date2 = None
        else:
            # split path
            pieces = product.split('/')[-1].split('_')
            if 'TSX' in pieces:
                prefix = 'TSX'
            else:
                prefix = '_'.join(pieces[0:2])
            date1 = datetime.strptime(pieces[dateLocs[prefix][0]], '%d%b%y')
            date2 = datetime.strptime(pieces[dateLocs[prefix][1]], '%d%b%y')
        return date1, date2

    def _setLayerColorTable(self, layer, colorTable='Greys', minV=None,
                            maxV=None, invert=False, opacity=1):
        '''
        Change layer to pseudocolor, set color table, and min/max values
        '''
        # Create style to grab a standard color table.
        myStyle = qc.QgsStyle().defaultStyle()
        # print(myStyle.colorRampNames())
        if colorTable not in myStyle.colorRampNames():
            print(f'Warning: colortable {colorTable} not in '
                  '{myStyle.colorRampNames()}.\n No color table Applied')
            return
        # Proceed with valid color table
        ramp = myStyle.colorRamp(colorTable)
        if invert:
            ramp.invert()
        # Combine bounding colors and stops
        colors = [ramp.color1()] + \
            [QColor(c.color.rgb()) for c in ramp.stops()] + [ramp.color2()]
        nColors = len(colors)
        # Setup shader function
        dv = (maxV - minV) / (nColors-1)
        itemList = [qc.QgsColorRampShader.ColorRampItem(minV + dv*n, c)
                    for n, c in zip(range(0, nColors), colors)]
        fcn = qc.QgsColorRampShader(colorRamp=ramp)
        fcn.setColorRampType(qc.QgsColorRampShader.Interpolated)
        fcn.setColorRampItemList(itemList)
        # setup shader and add to renderer
        shader = qc.QgsRasterShader()
        shader.setRasterShaderFunction(fcn)
        renderer = qc.QgsSingleBandPseudoColorRenderer(layer.dataProvider(), 1,
                                                       shader)
        # Set final layer properties
        layer.setRenderer(renderer)
        layer.renderer().setClassificationMin(minV)
        layer.renderer().setClassificationMax(maxV)
        layer.renderer().setOpacity(opacity)
