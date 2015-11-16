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

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.Qt import *
from PyQt4.QtSvg import * # required in some distros
from qgis.core import *
from plottingtool import PlottingTool

from math import sqrt
from osgeo import gdal, ogr
import numpy as np
#from profilebase import Ui_ProfileBase
from dataReaderTool import DataReaderTool
import platform
import sys
from PyQt4.QtCore import SIGNAL,SLOT,pyqtSignature


class DoProfile(QWidget):

    def __init__(self, iface, dockwidget1 , tool1 , plugin, parent = None):
        QWidget.__init__(self, parent)
        self.profiles = None        #dictionary where is saved the plotting data {"l":[l],"z":[z], "layer":layer1, "curve":curve1}
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

    def calculatePointProfile(self, points1, model1, library, vertline = True):
        self.pointstoDraw = points1

        self.removeClosedLayers(model1)
        if self.pointstoDraw == None:
            return
        PlottingTool().clearData(self.dockwidget, self.profiles, library)
        self.profiles = []
        #if vertline:                        #Plotting vertical lines at the node of polyline draw
        #    PlottingTool().drawVertLine(self.dockwidget, self.pointstoDraw, library)

        #creating the plots of profiles
        for i in range(0 , model1.rowCount()):
            self.profiles.append( {"layer": model1.item(i,3).data(Qt.EditRole) } )
            #self.profiles[i]["band"] = model1.item(i,3).data(Qt.EditRole) - 1
            self.profiles[i] = DataReaderTool().dataReaderTool(self.iface, self.tool, self.profiles[i], self.pointstoDraw[0])
        PlottingTool().attachCurves(self.dockwidget, self.profiles, model1, library)
        PlottingTool().reScalePlot(self.dockwidget, self.profiles, library)
        self.setupTableTab(model1)

    # The code is based on the approach of ZonalStatistics from Processing toolbox 
    def calculatePolygonProfile(self, geometry, crs, model, library):
        self.removeClosedLayers(model)
        if geometry is None or geometry.isEmpty():
            return
        
        PlottingTool().clearData(self.dockwidget, self.profiles, library)
        self.profiles = []

        #creating the plots of profiles
        for i in range(0 , model.rowCount()):
            self.profiles.append( {"layer": model.item(i,3).data(Qt.EditRole) } )
            self.profiles[i]["z"] = []
            self.profiles[i]["l"] = []
            
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
                srcArray = rasterBand.ReadAsArray(*srcOffset)
                
                srcArray = np.nan_to_num(srcArray)
                masked = np.ma.MaskedArray(srcArray,
                         mask=np.logical_or(srcArray == noData,
                         np.logical_not(rasterizedArray)))
                
                self.profiles[i]["z"].append(float(masked.mean()))
                self.profiles[i]["l"].append(bandNumber)
                
            memVDS = None
            rasterizedDS = None
        
        rasterDS = None
        
        PlottingTool().attachCurves(self.dockwidget, self.profiles, model, library)
        PlottingTool().reScalePlot(self.dockwidget, self.profiles, library)
        self.setupTableTab(model)    

    def mapToPixel(self, mX, mY, geoTransform):
        (pX, pY) = gdal.ApplyGeoTransform(
            gdal.InvGeoTransform(geoTransform)[1], mX, mY)
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
            self.groupBox[i].setMaximumSize(QSize(16777215, 150))
            self.groupBox[i].setTitle(QApplication.translate("GroupBox" + str(i), self.profiles[i]["layer"].name(), None, QApplication.UnicodeUTF8))
            self.groupBox[i].setObjectName("groupBox" + str(i))

            self.verticalLayout.append( QVBoxLayout(self.groupBox[i]) )
            self.verticalLayout[i].setObjectName("verticalLayout")
            #The table
            self.tableView.append( QTableView(self.groupBox[i]) )
            self.tableView[i].setObjectName("tableView" + str(i))
            font = QFont("Arial", 8)
            column = len(self.profiles[i]["l"])
            self.mdl = QStandardItemModel(2, column)
            for j in range(len(self.profiles[i]["l"])):
                self.mdl.setData(self.mdl.index(0, j, QModelIndex())  ,self.profiles[i]["l"][j])
                self.mdl.setData(self.mdl.index(0, j, QModelIndex())  ,font ,Qt.FontRole)
                self.mdl.setData(self.mdl.index(1, j, QModelIndex())  ,self.profiles[i]["z"][j])
                self.mdl.setData(self.mdl.index(1, j, QModelIndex())  ,font ,Qt.FontRole)
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
        text = ""
        for i in range( len(self.profiles[nr]["l"]) ):
            text += str(self.profiles[nr]["l"][i]) + "\t" + str(self.profiles[nr]["z"][i]) + "\n"
        self.clipboard.setText(text)


    def reScalePlot(self, param):                         # called when a spinbox value changed
        if type(param) != int:
            # don't execute it twice, for both valueChanged(int) and valueChanged(str) signals
            return
        if self.dockwidget.sbMinVal.value() == self.dockwidget.sbMaxVal.value() == 0:
            # don't execute it on init
            return
        PlottingTool().reScalePlot(self.dockwidget, self.profiles, self.dockwidget.cboLibrary.currentText () )


    def getProfileCurve(self,nr):
        try:
            return self.profiles[nr]["curve"]
        except:
            return None

