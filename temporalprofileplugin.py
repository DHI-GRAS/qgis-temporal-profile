# -*- coding: utf-8 -*-

"""
***************************************************************************
   temporalprofileplugin.py
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
from builtins import object

from osgeo import osr
from qgis.PyQt.QtCore import Qt, QObject
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.PyQt.QtGui import QIcon, QStandardItemModel, QColor
from qgis.core import QgsProject, QgsPointXY, QgsGeometry, QgsWkbTypes
from qgis.gui import QgsMapToolIdentifyFeature


from . import resources
from .ui.ptdockwidget import PTDockWidget
from .tools.doprofile import DoProfile
from .tools.ptmaptool import ProfiletoolMapTool
from .tools.tableviewtool import TableViewTool
from .tools.plottingtool import PlottingTool
from .tools.utils import isProfilable

class TemporalSpectralProfilePlugin(object):

    POINT_SELECTION = 0
    SELECTED_POLYGON = 1
    TEMPORARY_PLOYGON = 2

    def __init__(self, iface):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.wdg = None
        self.pointTool = None



    def initGui(self):
        # create action 
        self.action = QAction(QIcon(":/plugins/temporalprofiletool/icons/temporalProfileIcon.png"), "Temporal/Spectral Profile", self.iface.mainWindow())
        self.action.setWhatsThis("Plots temporal/spectral profiles")
        self.action.triggered.connect(self.run)
        self.aboutAction = QAction("About", self.iface.mainWindow())
        self.aboutAction.triggered.connect(self.about)

        # add toolbar button and menu item
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&Profile Tool", self.action)
        self.iface.addPluginToMenu("&Profile Tool", self.aboutAction)
        
        #Init classe variables
        self.pointTool = ProfiletoolMapTool(self.iface.mapCanvas(),self.action)        #the mouselistener
        self.dockOpened = False        #remember for not reopening dock if there's already one opened
        self.mdl = None                #the model whitch in are saved layers analysed caracteristics
        self.selectionmethod = 0                        #The selection method defined in option
        self.saveTool = self.canvas.mapTool()            #Save the standard mapttool for restoring it at the end
        self.layerindex = None                            #for selection mode
        self.previousLayer = None                        #for selection mode
        self.plotlibrary = None                            #The plotting library to use
        self.pointSelectionInstructions = "Click on a raster for temporal/spectral profile (right click to cancel then quit)"
        self.selectedPolygonInstructions = 'Use "Select Features" tool to select polygon(s) designating AOI for which temporal/spectral profile should be calculated'


    def unload(self):
        if not self.wdg is None:
            self.wdg.close()
        self.iface.removeToolBarIcon(self.action)
        self.iface.removePluginMenu("&Profile Tool", self.action)
        self.iface.removePluginMenu("&Profile Tool", self.aboutAction)


    def run(self):
        # first, check posibility
        if self.checkIfOpening() == False:
            return

        #if dock not already opened, open the dock and all the necessary thing (model,doProfile...)
        if self.dockOpened == False:
            self.mdl = QStandardItemModel(0, 6)
            self.wdg = PTDockWidget(self.iface.mainWindow(), self.iface, self.mdl)
            self.wdg.showIt()
            self.doprofile = DoProfile(self.iface,self.wdg,self.pointTool, self)
            self.tableViewTool = TableViewTool()
            self.wdg.closed.connect(self.cleaning2)
            self.wdg.tableView.clicked.connect(self._onClick) 
            self.wdg.pushButton_2.clicked.connect(self.addLayer)
            self.wdg.pushButton.clicked.connect(self.removeLayer)
            self.wdg.comboBox.currentIndexChanged.connect(self.selectionMethod)
            self.wdg.cboLibrary.currentIndexChanged.connect(self.changePlotLibrary)
            self.wdg.cboXAxis.currentIndexChanged.connect(self.changeXAxisLabeling)
            self.wdg.leXAxisSteps.editingFinished.connect(self.changeXAxisLabeling)
            self.wdg.dateTimeEditCurrentTime.editingFinished.connect(self.changeXAxisLabeling) 
            self.wdg.spinBoxTimeExtent.editingFinished.connect(self.changeXAxisLabeling) 
            self.wdg.cboTimeExtent.currentIndexChanged.connect(self.changeXAxisLabeling)
            self.wdg.cbTimeDimension.stateChanged.connect(self.changeXAxisLabeling)            
            self.wdg.addOptionComboboxItems()
            self.addLayer()    
            self.dockOpened = True
        #Listeners of mouse
        self.connectPointMapTool()
        #init the mouse listener comportement and save the classic to restore it on quit
        self.canvas.setMapTool(self.pointTool)
        
        #Help about what doing
        if self.selectionmethod == TemporalSpectralProfilePlugin.POINT_SELECTION:
            self.iface.mainWindow().statusBar().showMessage(self.pointSelectionInstructions )
        elif self.selectionmethod == TemporalSpectralProfilePlugin.SELECTED_POLYGON:
            self.iface.mainWindow().statusBar().showMessage(self.selectedPolygonInstructions)
            
        QgsProject.instance().layersWillBeRemoved .connect(self.onLayersWillBeRemoved)

#************************************* Canvas listener actions **********************************************
    
    # Used when layer is about to be removed from QGIS Map Layer Registry
    def onLayersWillBeRemoved(self, layersIds):
        if self.mdl is not None:
            for layerId in layersIds:
                for row in range(self.mdl.rowCount()):
                    if layerId == self.mdl.index(row, 3).data().id():
                        self.removeLayer(row)
                        self.onLayersWillBeRemoved(layersIds)
                        break
                    

    # Use for selected polygon option
    def selectionChanged(self, layer):
        if not layer.geometryType() == QgsWkbTypes.PolygonGeometry:
            return
        fullGeometry = QgsGeometry()
        for feature in layer.selectedFeatures():
            if fullGeometry.isEmpty():
                fullGeometry = QgsGeometry(feature.geometry())
            else:
                fullGeometry = fullGeometry.combine(feature.geometry())
        if not fullGeometry.isEmpty():
            crs = osr.SpatialReference()
            crs.ImportFromProj4(str(layer.crs().toProj4()))
            self.doprofile.calculatePolygonProfile(fullGeometry, crs, self.mdl, self.plotlibrary)


#************************************* Mouse listener actions ***********************************************
# Used for point selection option

    def moved(self, point):
        if self.selectionmethod == TemporalSpectralProfilePlugin.POINT_SELECTION:
            return
        if self.selectionmethod == TemporalSpectralProfilePlugin.SELECTED_POLYGON:
            return

    def rightClicked(self, point):    #used to quit the current action
            self.cleaning()

    def leftClicked(self, point):
        self.doubleClicked(point)

    def doubleClicked(self, point):
        if self.selectionmethod == TemporalSpectralProfilePlugin.POINT_SELECTION:
            self.iface.mainWindow().statusBar().showMessage(str(point.x())+", "+str(point.y()))
            self.doprofile.calculatePointProfile(point, self.mdl, self.plotlibrary)
        if self.selectionmethod == TemporalSpectralProfilePlugin.SELECTED_POLYGON:
            return

#***************************** open and quit options *******************************************
    
    def checkIfOpening(self):
        if self.iface.mapCanvas().layerCount() == 0:                    #Check a layer is opened
            QMessageBox.warning(self.iface.mainWindow(), "Profile", "First open any raster layer, please")
            return False

        layer = self.iface.activeLayer()
        
        if layer == None or not isProfilable(layer) :    #Check if a raster layer is opened and selectionned
            if self.mdl == None or self.mdl.rowCount() == 0:
                QMessageBox.warning(self.iface.mainWindow(), "Profile Tool", "Please select one raster layer")
                return False
                
        return True
    
    def connectPointMapTool(self):
        self.pointTool.moved.connect(self.moved)
        self.pointTool.rightClicked.connect(self.rightClicked)
        self.pointTool.leftClicked.connect(self.leftClicked)
        self.pointTool.doubleClicked.connect(self.doubleClicked)
        

    def deactivatePointMapTool(self):        #enable clean exit of the plugin
        self.pointTool.moved.disconnect(self.moved)
        self.pointTool.leftClicked.disconnect(self.leftClicked)
        self.pointTool.rightClicked.disconnect(self.rightClicked)
        self.pointTool.doubleClicked.disconnect(self.doubleClicked)
        self.iface.mainWindow().statusBar().showMessage("")

    def connectSelectedPolygonsTool(self):
        self.iface.mapCanvas().selectionChanged.connect(self.selectionChanged)
        
    def deactivateSelectedPolygonsTools(self):
        self.iface.mapCanvas().selectionChanged.disconnect(self.selectionChanged)

    def cleaning(self):            #used on right click
        try:
            self.previousLayer.removeSelection(False)
        except:
            pass
        self.canvas.unsetMapTool(self.pointTool)
        self.canvas.setMapTool(self.saveTool)
        self.iface.mainWindow().statusBar().showMessage( "" )

    def cleaning2(self):        #used when Dock dialog is closed
        self.wdg.tableView.clicked.disconnect(self._onClick)
        if self.selectionmethod == TemporalSpectralProfilePlugin.POINT_SELECTION:
            self.deactivatePointMapTool()
        else:
            self.deactivateSelectedPolygonsTools()
        self.selectionmethod = TemporalSpectralProfilePlugin.POINT_SELECTION
        self.wdg.comboBox.currentIndexChanged.disconnect(self.selectionMethod)
        QgsProject.instance().layersWillBeRemoved .disconnect(self.onLayersWillBeRemoved)
        self.mdl = None
        self.dockOpened = False
        self.cleaning()
        self.wdg = None

    #***************************** Options *******************************************

    def selectionMethod(self,item):
        if item == TemporalSpectralProfilePlugin.POINT_SELECTION:
            self.selectionmethod = TemporalSpectralProfilePlugin.POINT_SELECTION
            self.pointTool.setCursor(Qt.CrossCursor)
            self.deactivateSelectedPolygonsTools()
            self.connectPointMapTool()
            if not self.canvas.mapTool() == self.pointTool:
                self.canvas.setMapTool(self.pointTool)
            self.iface.mainWindow().statusBar().showMessage(self.pointSelectionInstructions)
            self.wdg.changeStatComboBoxItems(self.doprofile.getPointProfileStatNames())
            
        elif item == TemporalSpectralProfilePlugin.SELECTED_POLYGON:
            self.selectionmethod = TemporalSpectralProfilePlugin.SELECTED_POLYGON
            self.deactivatePointMapTool()
            self.connectSelectedPolygonsTool()
            self.iface.actionSelectRectangle().trigger()
            self.iface.mainWindow().statusBar().showMessage(self.selectedPolygonInstructions)
            self.wdg.changeStatComboBoxItems(self.doprofile.getPolygonProfileStatNames(), "mean")  
                
    def changePlotLibrary(self, item):
        self.plotlibrary = self.wdg.cboLibrary.itemText(item)
        self.wdg.addPlotWidget(self.plotlibrary)
        self.changeXAxisLabeling()
        
    def changeXAxisLabeling(self):
        self.xAxisSteps = {}
        # default band number labeling
        if self.wdg.cboXAxis.currentIndex() == 0:
            self.doprofile.xAxisSteps = None
        # Labels from string
        elif self.wdg.cboXAxis.currentIndex() == 1:
            self.doprofile.xAxisSteps = self.wdg.leXAxisSteps.text().split(';')
            try:
               self.doprofile.xAxisSteps = [ float(x) for x in self.doprofile.xAxisSteps ]
            except ValueError:
                self.doprofile.xAxisSteps = None
                text = "Temporal/Spectral Profile Tool: The X-axis steps' string " + \
                              "is invalid. Using band numbers instead."
                self.iface.messageBar().pushWidget(self.iface.messageBar().createMessage(text), 
                                                   QgsMessageBar.WARNING, 5)
        # Labels based on time
        elif self.wdg.cboXAxis.currentIndex() == 2: 
            self.doprofile.xAxisSteps = ["Timesteps", 
                                         self.wdg.dateTimeEditCurrentTime.dateTime().toPyDateTime(), 
                                         int(self.wdg.spinBoxTimeExtent.cleanText()),
                                         self.wdg.cboTimeExtent.currentText(),
                                         self.wdg.cbTimeDimension.isChecked()]
            if self.plotlibrary == "Qwt5":
                text = "Temporal/Spectral Profile Tool: There is currently no support using " + \
                              "Time steps while using the Qwt plotlibrary"
                self.iface.messageBar().pushWidget(self.iface.messageBar().createMessage(text), 
                                                   QgsMessageBar.WARNING, 5)
                self.doprofile.xAxisSteps = None
        

    #************************* tableview function ******************************************

    def addLayer(self):
        layer = self.iface.activeLayer()
        if isProfilable(layer):
            self.tableViewTool.addLayer(self.iface, self.mdl, layer)

    def _onClick(self,index1):                    #action when clicking the tableview
        self.tableViewTool.onClick(self.iface, self.wdg, self.mdl, self.plotlibrary, index1)

    def removeLayer(self, index = None):
        if index is None or index is False:
            index = self.tableViewTool.chooseLayerForRemoval(self.iface, self.mdl)
        
        if index is not None:
            self.tableViewTool.removeLayer(self.mdl, index)
            PlottingTool().clearData(self.wdg, self.mdl, self.plotlibrary)

    def about(self):
        from .ui.dlgabout import DlgAbout
        DlgAbout(self.iface.mainWindow()).exec_()
