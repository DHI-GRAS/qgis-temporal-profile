# -*- coding: utf-8 -*-

"""
***************************************************************************
   doprofile.py
-------------------------------------
    Copyright (C) 2014 TIGER-NET (www.tiger-net.org)
    
    Based on Profile tool plugin:
      Copyright (C) 2008  Borys Jurgiel
      Copyright (C) 2012  Patrice Verchere

***************************************************************************
* This plugin is part of the Water Observation Information System (WOIS)  *
* developed under the TIGER-NET project funded by the European Space      *
* Agency as part of the long-term TIGER initiative aiming at promoting    *
* the use of Earth Observation (EO) for improved Integrated Water         *
* Resources Management (IWRM) in Africa.                                  *
*                                                                         *
* WOIS is a free software i.e. you can redistribute it and/or modify      *
* it under the terms of the GNU General Public License as published       *
* by the Free Software Foundation, either version 3 of the License,       *
* or (at your option) any later version.                                  *
*                                                                         *
* WOIS is distributed in the hope that it will be useful, but WITHOUT ANY * 
* WARRANTY; without even the implied warranty of MERCHANTABILITY or       *
* FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License   *
* for more details.                                                       *
*                                                                         *
* You should have received a copy of the GNU General Public License along *
* with this program.  If not, see <http://www.gnu.org/licenses/>.         *
***************************************************************************
"""
import math
import re
from datetime import datetime, timedelta

from PyQt4.QtCore import Qt, QModelIndex, QSize, QObject, SIGNAL
from PyQt4.QtGui import QWidget, QGroupBox, QFont, QApplication, QSizePolicy, \
                        QTableView, QVBoxLayout, QStandardItemModel, QPushButton, \
                        QApplication, QHBoxLayout
from qgis.core import QgsPoint, QgsRectangle, QgsGeometry, QgsRaster
from qgis.gui import QgsMessageBar
from plottingtool import PlottingTool

from osgeo import gdal, ogr
import numpy as np

class DoProfile(QWidget):

    def __init__(self, iface, dockwidget1 , tool1 , plugin, parent = None):
        QWidget.__init__(self, parent)
        self.profiles = None        #dictionary where is saved the plotting data {"l":[l],"z":[z], "layer":layer1, "curve":curve1}
        self.xAxisSteps = None
        self.xAxisStepType = "numeric"
        self.iface = iface
        self.tool = tool1
        self.dockwidget = dockwidget1
        self.pointstoDraw = None
        self.plugin = plugin
        #init scale widgets
        self.dockwidget.sbMaxVal.setValue(0)
        self.dockwidget.sbMinVal.setValue(0)
        self.dockwidget.sbMaxVal.setEnabled(False)
        self.dockwidget.sbMinVal.setEnabled(False)
        self.dockwidget.sbMinVal.valueChanged.connect(self.reScalePlot)
        self.dockwidget.sbMaxVal.valueChanged.connect(self.reScalePlot)


    #**************************** function part *************************************************

    # remove layers which were removed from QGIS
    def removeClosedLayers(self, model1):
        qgisLayerNames = []
        for i in range(0, self.iface.mapCanvas().layerCount()):
                qgisLayerNames.append(self.iface.mapCanvas().layer(i).name())

        for i in range(0 , model1.rowCount()):
            layerName = model1.item(i,2).data(Qt.EditRole)
            if not layerName in qgisLayerNames:
                self.plugin.removeLayer(i)
                self.removeClosedLayers(model1)
                break

    def calculatePointProfile(self, points, model, library):
        self.model = model
        self.library = library
        
        self.pointToProfile = points[0]
        statName = self.getPointProfileStatNames()[0]

        self.removeClosedLayers(model)
        if self.pointToProfile == None:
            return
        PlottingTool().clearData(self.dockwidget, model, library)
        self.profiles = []
        
        #creating the plots of profiles
        for i in range(0 , model.rowCount()):
            self.profiles.append( {"layer": model.item(i,3).data(Qt.EditRole) } )
            self.profiles[i][statName] = []
            self.profiles[i]["l"] = []
            layer = self.profiles[i]["layer"]

            if layer:
                try:
                    point = self.tool.toLayerCoordinates(layer , QgsPoint(self.pointToProfile[0],self.pointToProfile[1]))
                    ident = layer.dataProvider().identify(point, QgsRaster.IdentifyFormatValue )
                except:
                    ident = None
            else:
                ident = None
            #if ident is not None and ident.has_key(choosenBand+1):
            if ident is not None:
                self.profiles[i][statName] = ident.results().values()
                self.profiles[i]["l"] = ident.results().keys()
        
        self.setXAxisSteps()
        PlottingTool().attachCurves(self.dockwidget, self.profiles, model, library)
        PlottingTool().reScalePlot(self.dockwidget, self.profiles, model, library)
        self.setupTableTab(model)

    def getPointProfileStatNames(self):
        return ["value"]

    # The code is based on the approach of ZonalStatistics from Processing toolbox 
    def calculatePolygonProfile(self, geometry, crs, model, library):
        self.model = model
        self.library = library
        
        self.removeClosedLayers(model)
        if geometry is None or geometry.isEmpty():
            return
        
        PlottingTool().clearData(self.dockwidget, model, library)
        self.profiles = []

        #creating the plots of profiles
        for i in range(0 , model.rowCount()):
            self.profiles.append( {"layer": model.item(i,3).data(Qt.EditRole) } )
            self.profiles[i]["l"] = []
            for statistic in self.getPolygonProfileStatNames():
                self.profiles[i][statistic] = []
            
            # Get intersection between polygon geometry and raster following ZonalStatistics code
            rasterDS = gdal.Open(self.profiles[i]["layer"].source(), gdal.GA_ReadOnly)
            geoTransform = rasterDS.GetGeoTransform()
            
    
            cellXSize = abs(geoTransform[1])
            cellYSize = abs(geoTransform[5])
            rasterXSize = rasterDS.RasterXSize
            rasterYSize = rasterDS.RasterYSize
    
            rasterBBox = QgsRectangle(geoTransform[0], geoTransform[3] - cellYSize
                                      * rasterYSize, geoTransform[0] + cellXSize
                                      * rasterXSize, geoTransform[3])
            rasterGeom = QgsGeometry.fromRect(rasterBBox)
            
            memVectorDriver = ogr.GetDriverByName('Memory')
            memRasterDriver = gdal.GetDriverByName('MEM')
            
            intersectedGeom = rasterGeom.intersection(geometry)
            ogrGeom = ogr.CreateGeometryFromWkt(intersectedGeom.exportToWkt())
            
            bbox = intersectedGeom.boundingBox()

            xMin = bbox.xMinimum()
            xMax = bbox.xMaximum()
            yMin = bbox.yMinimum()
            yMax = bbox.yMaximum()

            (startColumn, startRow) = self.mapToPixel(xMin, yMax, geoTransform)
            (endColumn, endRow) = self.mapToPixel(xMax, yMin, geoTransform)

            width = endColumn - startColumn
            height = endRow - startRow

            if width == 0 or height == 0:
                return

            srcOffset = (startColumn, startRow, width, height)

            newGeoTransform = (
                geoTransform[0] + srcOffset[0] * geoTransform[1],
                geoTransform[1],
                0.0,
                geoTransform[3] + srcOffset[1] * geoTransform[5],
                0.0,
                geoTransform[5],
            )
            
            # Create a temporary vector layer in memory
            memVDS = memVectorDriver.CreateDataSource('out')
            memLayer = memVDS.CreateLayer('poly', crs, ogr.wkbPolygon)

            ft = ogr.Feature(memLayer.GetLayerDefn())
            ft.SetGeometry(ogrGeom)
            memLayer.CreateFeature(ft)
            ft.Destroy()
            
            # Rasterize it
            rasterizedDS = memRasterDriver.Create('', srcOffset[2],
                    srcOffset[3], 1, gdal.GDT_Byte)
            rasterizedDS.SetGeoTransform(newGeoTransform)
            gdal.RasterizeLayer(rasterizedDS, [1], memLayer, burn_values=[1])
            rasterizedArray = rasterizedDS.ReadAsArray()
            
            for bandNumber in range(1, rasterDS.RasterCount+1): 
                rasterBand = rasterDS.GetRasterBand(bandNumber)
                noData = rasterBand.GetNoDataValue()
                scale = rasterBand.GetScale()
                if scale is None:
                    scale = 1.0
                offset = rasterBand.GetOffset()
                if offset is None:
                    offset = 0.0
                srcArray = rasterBand.ReadAsArray(*srcOffset)
                srcArray = srcArray*scale+offset 
                masked = np.ma.MaskedArray(srcArray,
                            mask=np.logical_or.reduce((
                             srcArray == noData,
                             np.logical_not(rasterizedArray),
                             np.isnan(srcArray))))

                self.profiles[i]["l"].append(bandNumber)
                self.profiles[i]["count"].append(float(masked.count()))
                self.profiles[i]["max"].append(float(masked.max()))
                self.profiles[i]["mean"].append(float(masked.mean()))
                self.profiles[i]["median"].append(float(np.ma.median(masked)))
                self.profiles[i]["min"].append(float(masked.min()))
                self.profiles[i]["range"].append(float(masked.max()) - float(masked.min()))
                self.profiles[i]["std"].append(float(masked.std()))
                self.profiles[i]["sum"].append(float(masked.sum()))
                self.profiles[i]["unique"].append(np.unique(masked.compressed()).size)
                self.profiles[i]["var"].append(float(masked.var()))
                
            memVDS = None
            rasterizedDS = None
        
        rasterDS = None
        
        self.setXAxisSteps()
        PlottingTool().attachCurves(self.dockwidget, self.profiles, model, library)
        PlottingTool().reScalePlot(self.dockwidget, self.profiles, model, library)
        self.setupTableTab(model)

    def getPolygonProfileStatNames(self):
        return ["count", "max", "mean", "median", "min", "range", "std", "sum", "unique", "var"]

    def setXAxisSteps(self):
        if self.xAxisSteps == None:
            self.changeXAxisStepType("numeric")
            return
        
        elif self.xAxisSteps[0] == "Timesteps":
            for profile in self.profiles:
                stepsNum = len(profile["l"])
                startTime = self.xAxisSteps[1]
                step = self.xAxisSteps[2]
                stepType = self.xAxisSteps[3]
                useNetcdfTime = self.xAxisSteps[4]
                if stepType == "years":
                    stepType = "days"
                    step = step * 365
                elif stepType == "months":
                    stepType = "days"
                    step = step * 365/12

                profile["l"] = []
                if useNetcdfTime and (profile["layer"].source().startswith("NETCDF:") or
                                      profile["layer"].source().endswith(".nc")):
                    try:
                        import netCDF4
                        if profile["layer"].source().startswith("NETCDF:"):
                            filename = re.match('NETCDF:\"(.*)\":.*$', profile["layer"].source()).group(1)
                        else:
                            filename = profile["layer"].source()
                        nc = netCDF4.Dataset(filename, mode='r')
                        profile["l"] = netCDF4.num2date(nc.variables["time"][:],
                                                        units = nc.variables["time"].units,
                                                        calendar = nc.variables["time"].calendar)
                        nc.close()
                    except ImportError:
                        text = "Temporal/Spectral Profile Tool: netCDF4 module is required to read NetCDF " + \
                               "time dimension. Please use pip install netCDF4"
                        self.iface.messageBar().pushWidget(self.iface.messageBar().createMessage(text), 
                                                           QgsMessageBar.WARNING, 5)
                        profile["l"] = []
                    except KeyError:
                        text = "Temporal/Spectral Profile Tool: NetCDF file does not have " + \
                               "time dimension."
                        self.iface.messageBar().pushWidget(self.iface.messageBar().createMessage(text), 
                                                           QgsMessageBar.WARNING, 5)
                        nc.close()
                        profile["l"] = []
                if profile["l"] == []:
                    for i in range(stepsNum):
                        timedeltaParams = {stepType: step*i}
                        profile["l"].append(startTime + timedelta(**timedeltaParams))
                
                self.changeXAxisStepType("timedate")        
        else:
            for profile in self.profiles:
                # Truncate the profiles to the minimum of the length of each profile
                # or length of provided x-axis steps
                stepsNum = min(len(self.xAxisSteps), len(profile["l"]))
                profile["l"] = self.xAxisSteps[:stepsNum]
                for stat in profile.keys():
                    if stat == "l" or stat == "layer":
                        continue
                    profile[stat] = profile[stat][:stepsNum]
                    
                # If any x-axis step is a NaN then remove the corresponding
                # value from profile
                nans = [i for i, x in enumerate(profile["l"]) if math.isnan(x)]
                for stat in profile.keys():
                    if stat == "layer":
                        continue
                    profile[stat] = [x for i, x in enumerate(profile[stat]) if i not in nans]
            
            self.changeXAxisStepType("numeric")
            
    def changeXAxisStepType(self, newType):
        if self.xAxisStepType == newType:
            return
        else:
            self.xAxisStepType = newType
            PlottingTool().resetAxis(self.dockwidget, self.library)
    
    def mapToPixel(self, mX, mY, geoTransform):
        # GDAL 1.x
        try:
            (pX, pY) = gdal.ApplyGeoTransform(
                gdal.InvGeoTransform(geoTransform)[1], mX, mY)
        # GDAL 2.x
        except TypeError:
            (pX, pY) = gdal.ApplyGeoTransform(
                gdal.InvGeoTransform(geoTransform), mX, mY)
            
        return (int(pX), int(pY))            
    
    def setupTableTab(self, model1):
        #*********************** TAble tab *************************************************
        try:                                                                    #Reinitializing the table tab
            self.VLayout = self.dockwidget.scrollAreaWidgetContents.layout()
            while 1:
                child = self.VLayout.takeAt(0)
                if not child:
                    break
                child.widget().deleteLater()
        except:
            self.VLayout = QVBoxLayout(self.dockwidget.scrollAreaWidgetContents)
            self.VLayout.setContentsMargins(9, -1, -1, -1)
        #Setup the table tab
        self.groupBox = []
        self.profilePushButton = []
        self.tableView = []
        self.verticalLayout = []
        for i in range(0 , model1.rowCount()):
            self.groupBox.append( QGroupBox(self.dockwidget.scrollAreaWidgetContents) )
            sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            sizePolicy.setHorizontalStretch(0)
            sizePolicy.setVerticalStretch(0)
            sizePolicy.setHeightForWidth(self.groupBox[i].sizePolicy().hasHeightForWidth())
            self.groupBox[i].setSizePolicy(sizePolicy)
            self.groupBox[i].setMinimumSize(QSize(0, 150))
            self.groupBox[i].setMaximumSize(QSize(16777215, 350))
            self.groupBox[i].setTitle(QApplication.translate("GroupBox" + str(i), self.profiles[i]["layer"].name(), None, QApplication.UnicodeUTF8))
            self.groupBox[i].setObjectName("groupBox" + str(i))

            self.verticalLayout.append( QVBoxLayout(self.groupBox[i]) )
            self.verticalLayout[i].setObjectName("verticalLayout")
            #The table
            self.tableView.append( QTableView(self.groupBox[i]) )
            self.tableView[i].setObjectName("tableView" + str(i))
            font = QFont("Arial", 8)
            columns = len(self.profiles[i]["l"])
            rowNames = self.profiles[i].keys()
            rowNames.remove("layer") # holds the QgsMapLayer instance
            rowNames.remove("l") # holds the band number
            rows = len(rowNames)
            self.mdl = QStandardItemModel(rows+1, columns)
            self.mdl.setVerticalHeaderLabels(["band"] + rowNames)
            for j in range(columns):
                self.mdl.setData(self.mdl.index(0, j, QModelIndex()), str(self.profiles[i]["l"][j]))
                self.mdl.setData(self.mdl.index(0, j, QModelIndex()), font ,Qt.FontRole)
                for k in range(rows):
                    self.mdl.setData(self.mdl.index(k+1, j, QModelIndex()), str(self.profiles[i][rowNames[k]][j]))
                    self.mdl.setData(self.mdl.index(k+1, j, QModelIndex()), font ,Qt.FontRole)
            #self.tableView[i].setVerticalHeaderLabels(rowNames)
            self.tableView[i].verticalHeader().setDefaultSectionSize(18)
            self.tableView[i].horizontalHeader().setDefaultSectionSize(60)
            self.tableView[i].setModel(self.mdl)
            self.verticalLayout[i].addWidget(self.tableView[i])

            self.horizontalLayout = QHBoxLayout()

            #the copy to clipboard button
            self.profilePushButton.append( QPushButton(self.groupBox[i]) )
            sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            sizePolicy.setHorizontalStretch(0)
            sizePolicy.setVerticalStretch(0)
            sizePolicy.setHeightForWidth(self.profilePushButton[i].sizePolicy().hasHeightForWidth())
            self.profilePushButton[i].setSizePolicy(sizePolicy)
            self.profilePushButton[i].setText(QApplication.translate("GroupBox", "Copy to clipboard", None, QApplication.UnicodeUTF8))
            self.profilePushButton[i].setObjectName(str(i))
            self.horizontalLayout.addWidget(self.profilePushButton[i])

            self.horizontalLayout.addStretch(0)
            self.verticalLayout[i].addLayout(self.horizontalLayout)

            self.VLayout.addWidget(self.groupBox[i])
            QObject.connect(self.profilePushButton[i], SIGNAL("clicked()"), self.copyTable)

    def copyTable(self):                            #Writing the table to clipboard in excel form
        nr = int( self.sender().objectName() )
        self.clipboard = QApplication.clipboard()
        text = "band"
        rowNames = self.profiles[nr].keys()
        rowNames.remove("layer")
        rowNames.remove("l")
        for name in rowNames:
            text += "\t"+name
        text += "\n"
        for i in range( len(self.profiles[nr]["l"]) ):
            text += str(self.profiles[nr]["l"][i])
            for j in range(len(rowNames)):
                text += "\t" + str(self.profiles[nr][rowNames[j]][i])
            text += "\n"
        self.clipboard.setText(text)


    def reScalePlot(self, param):                         # called when a spinbox value changed
        if type(param) != float:    
            # don't execute it twice, for both valueChanged(int) and valueChanged(str) signals
            return
        if self.dockwidget.sbMinVal.value() == self.dockwidget.sbMaxVal.value() == 0:
            # don't execute it on init
            return
        PlottingTool().reScalePlot(self.dockwidget, self.profiles, self.model, self.library, autoMode = False)


    def getProfileCurve(self,nr):
        try:
            return self.profiles[nr]["curve"]
        except:
            return None

