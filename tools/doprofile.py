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
from __future__ import absolute_import
from builtins import str
from builtins import range
import math
import re
from datetime import datetime, timedelta

from qgis.PyQt.QtCore import Qt, QModelIndex, QSize, QObject
from qgis.PyQt.QtWidgets import QWidget, QGroupBox, QApplication, QSizePolicy, QTableView, QVBoxLayout, QPushButton, QApplication, QHBoxLayout
from qgis.PyQt.QtGui import QFont, QStandardItemModel
from qgis.core import QgsPoint, QgsRectangle, QgsGeometry, QgsRaster, QgsProject, QgsCoordinateReferenceSystem, QgsCoordinateTransform
from qgis.gui import QgsMessageBar
from .plottingtool import PlottingTool

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

    def transform_geom(self, geom, src_epsg_code, dst_epsg_code):
        """
         Transforms the given QgsGeometry object with the given src and dest EPSG code parameters.

        :param geom: QgsGeometry object
        :param src_epsg_code: source EPSG Code
        :param dst_epsg_code: destination EPSG Code

        :return: transformed QgsGeometry object
        """

        if isinstance(src_epsg_code, type(1)) and isinstance(dst_epsg_code, type(1)):

            crsSrc = QgsCoordinateReferenceSystem.fromEpsgId(src_epsg_code)
            crsDest = QgsCoordinateReferenceSystem.fromEpsgId(dst_epsg_code)
            xform = QgsCoordinateTransform(crsSrc,
                                           crsDest,
                                           QgsProject.instance())

            geom.transform(xform)

            return geom

        else:
            return None

    def calculatePointProfile(self, point, model, library):
        self.model = model
        self.library = library

        statName = self.getPointProfileStatNames()[0]

        self.removeClosedLayers(model)
        if point == None:
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
                    # project to CRS of the current Raster if they don't match
                    prj_epsg = int(QgsProject.instance().crs().authid().split("EPSG:")[1])
                    lyr_epsg = int(layer.crs().authid().split("EPSG:")[1])
                except IndexError:
                    prj_epsg = lyr_epsg = None
                if prj_epsg != lyr_epsg:
                    geom = QgsGeometry.fromPointXY(point)
                    t_geom = self.transform_geom(geom, prj_epsg, lyr_epsg)
                    point = t_geom.asPoint()
                ident = layer.dataProvider().identify(point, QgsRaster.IdentifyFormatValue)

            else:
                ident = None
            if ident is not None:
                self.profiles[i][statName] = list(ident.results().values())
                self.profiles[i]["l"] = list(ident.results().keys())

        self.setXAxisSteps()
        PlottingTool().attachCurves(self.dockwidget, self.profiles, model, library)
        if self.dockwidget.cboAutoScale.isChecked():
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

        # creating the plots of profiles
        for i in range(0, model.rowCount()):
            layer = model.item(i, 3).data(Qt.EditRole)
            self.profiles.append({"layer": layer})
            self.profiles[i]["l"] = []
            for statistic in self.getPolygonProfileStatNames():
                self.profiles[i][statistic] = []

            # project to CRS of the current Raster if they don't match
            vector_ref_system = QgsCoordinateReferenceSystem()
            vector_ref_system.createFromProj(crs.ExportToProj4())
            try:
                vector_epsg = int(vector_ref_system.authid().split("EPSG:")[1])
                raster_epsg = int(layer.crs().authid().split("EPSG:")[1])
            except IndexError:
                vector_epsg = raster_epsg = None
            if vector_epsg != raster_epsg:
                t_geometry = self.transform_geom(geometry, vector_epsg, raster_epsg)
            else:
                t_geometry = geometry

            # Get intersection between polygon geometry and raster following ZonalStatistics code
            rasterDS = gdal.Open(layer.source(), gdal.GA_ReadOnly)
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

            intersectedGeom = rasterGeom.intersection(t_geometry)
            ogrGeom = ogr.CreateGeometryFromWkt(intersectedGeom.asWkt())

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
                if noData is None:
                    noData = np.nan
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
        if self.dockwidget.cboAutoScale.isChecked():
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
                                                        calendar = nc.variables["time"].calendar,
                                                        only_use_cftime_datetimes=False)
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
                for stat in list(profile.keys()):
                    if stat == "l" or stat == "layer":
                        continue
                    profile[stat] = profile[stat][:stepsNum]

                try:
                    # If any x-axis step is a NaN then remove the corresponding
                    # value from profile
                    nans = [i for i, x in enumerate(profile["l"]) if math.isnan(x)]
                    for stat in list(profile.keys()):
                        if stat == "layer":
                            continue
                        profile[stat] = [x for i, x in enumerate(profile[stat]) if i not in nans]
                    self.changeXAxisStepType("numeric")
                except TypeError:
                    # If above throws an exception then we are probably dealing with date
                    self.changeXAxisStepType("timedate")

    def changeXAxisStepType(self, newType):
        if self.xAxisStepType == newType:
            return
        else:
            self.xAxisStepType = newType
            PlottingTool().resetAxis(self.dockwidget, self.library)

    def mapToPixel(self, mX, mY, geoTransform):
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
            self.groupBox[i].setTitle(QApplication.translate("GroupBox" + str(i), self.profiles[i]["layer"].name(), None))
            self.groupBox[i].setObjectName("groupBox" + str(i))

            self.verticalLayout.append( QVBoxLayout(self.groupBox[i]) )
            self.verticalLayout[i].setObjectName("verticalLayout")
            #The table
            self.tableView.append( QTableView(self.groupBox[i]) )
            self.tableView[i].setObjectName("tableView" + str(i))
            font = QFont("Arial", 8)
            columns = len(self.profiles[i]["l"])
            rowNames = list(self.profiles[i].keys())
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
            self.profilePushButton[i].setText(QApplication.translate("GroupBox", "Copy to clipboard", None))
            self.profilePushButton[i].setObjectName(str(i))
            self.horizontalLayout.addWidget(self.profilePushButton[i])

            self.horizontalLayout.addStretch(0)
            self.verticalLayout[i].addLayout(self.horizontalLayout)

            self.VLayout.addWidget(self.groupBox[i])
            self.profilePushButton[i].clicked.connect(self.copyTable)

    def copyTable(self):                            #Writing the table to clipboard in excel form
        nr = int( self.sender().objectName() )
        self.clipboard = QApplication.clipboard()
        text = "band"
        rowNames = list(self.profiles[nr].keys())
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
