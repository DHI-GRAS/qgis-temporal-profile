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

from osgeo import osr
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *


import resources
from ui.ptdockwidget import PTDockWidget
from tools.doprofile import DoProfile
from tools.ptmaptool import ProfiletoolMapTool
from tools.tableviewtool import TableViewTool
from tools.plottingtool import PlottingTool
from tools.utils import isProfilable

class TemporalSpectralProfilePlugin:

    POINT_SELECTION = 0
    SELECTED_POLYGON = 1
    TEMPORARY_PLOYGON = 2

    def __init__(self, iface):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.wdg = None
        self.pointTool = None
        self.lastFreeHandPoints = []


    def initGui(self):
        # create action 
        self.action = QAction(QIcon(":/plugins/temporalprofiletool/icons/temporalProfileIcon.png"), "Temporal/Spectral Profile", self.iface.mainWindow())
        self.action.setWhatsThis("Plots temporal/spectral profiles")
        QObject.connect(self.action, SIGNAL("triggered()"), self.run)
        self.aboutAction = QAction("About", self.iface.mainWindow())
        QObject.connect(self.aboutAction, SIGNAL("triggered()"), self.about)

        # add toolbar button and menu item
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&Profile Tool", self.action)
        self.iface.addPluginToMenu("&Profile Tool", self.aboutAction)
        
        #Init classe variables
        self.pointTool = ProfiletoolMapTool(self.iface.mapCanvas(),self.action)        #the mouselistener
        self.dockOpened = False        #remember for not reopening dock if there's already one opened
        self.pointstoDraw = None    #Polyline in mapcanvas CRS analysed
        self.dblclktemp = None        #enable disctinction between leftclick and doubleclick
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
            QObject.connect(self.wdg, SIGNAL( "closed(PyQt_PyObject)" ), self.cleaning2)
            QObject.connect(self.wdg.tableView,SIGNAL("clicked(QModelIndex)"), self._onClick) 
            QObject.connect(self.wdg.pushButton_2, SIGNAL("clicked()"), self.addLayer)
            QObject.connect(self.wdg.pushButton, SIGNAL("clicked()"), self.removeLayer)
            QObject.connect(self.wdg.comboBox, SIGNAL("currentIndexChanged(int)"), self.selectionMethod)
            QObject.connect(self.wdg.cboLibrary, SIGNAL("currentIndexChanged(int)"), self.changePlotLibrary)
            QObject.connect(self.wdg.cboXAxis, SIGNAL("currentIndexChanged(int)"), self.changeXAxisLabeling)
            QObject.connect(self.wdg.leXAxisSteps, SIGNAL("editingFinished()"), self.changeXAxisLabeling)
            QObject.connect(self.wdg.dateTimeEditCurrentTime, SIGNAL("editingFinished()"), self.changeXAxisLabeling) 
            QObject.connect(self.wdg.spinBoxTimeExtent, SIGNAL("editingFinished()"), self.changeXAxisLabeling) 
            QObject.connect(self.wdg.cboTimeExtent, SIGNAL("currentIndexChanged(int)"), self.changeXAxisLabeling)
            QObject.connect(self.wdg.cbTimeDimension, SIGNAL("stateChanged(int)"), self.changeXAxisLabeling)            
            self.tableViewTool.layerAddedOrRemoved.connect(self.refreshPlot)
            self.wdg.addOptionComboboxItems()
            self.addLayer()    
            self.dockOpened = True
        #Listeners of mouse
        self.connectPointMapTool()
        #init the mouse listener comportement and save the classic to restore it on quit
        self.canvas.setMapTool(self.pointTool)
        #init the temp layer where the polyline is draw
        self.polygon = False
        self.rubberband = QgsRubberBand(self.canvas, self.polygon)
        self.rubberband.setWidth(2)
        self.rubberband.setColor(QColor(Qt.red))
        #init the table where is saved the poyline
        self.pointstoDraw = []
        self.pointstoCal = []
        self.lastClicked = [[-9999999999.9,9999999999.9]]
        # The last valid line we drew to create a free-hand profile
        self.lastFreeHandPoints = []
        
        #Help about what doing
        if self.selectionmethod == TemporalSpectralProfilePlugin.POINT_SELECTION:
            self.iface.mainWindow().statusBar().showMessage(self.pointSelectionInstructions )
        elif self.selectionmethod == TemporalSpectralProfilePlugin.SELECTED_POLYGON:
            self.iface.mainWindow().statusBar().showMessage(self.selectedPolygonInstructions)
            
        QObject.connect(QgsMapLayerRegistry.instance(), SIGNAL("layersWillBeRemoved (QStringList)"), self.onLayersWillBeRemoved)

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
        if not layer.geometryType() == QGis.Polygon:
            return
        fullGeometry = QgsGeometry()
        for feature in layer.selectedFeatures():
            if fullGeometry.isEmpty():
                fullGeometry = QgsGeometry(feature.constGeometry())
            else:
                fullGeometry = fullGeometry.combine(feature.constGeometry())
        if not fullGeometry.isEmpty():
            crs = osr.SpatialReference()
            crs.ImportFromProj4(str(layer.crs().toProj4()))
            self.doprofile.calculatePolygonProfile(fullGeometry, crs, self.mdl, self.plotlibrary)


#************************************* Mouse listener actions ***********************************************
# Used for point selection option

    def moved(self,position):            #draw the polyline on the temp layer (rubberband)
        if self.selectionmethod == 0:
            if len(self.pointstoDraw) > 0:
                #Get mouse coords
                mapPos = self.canvas.getCoordinateTransform().toMapCoordinates(position["x"],position["y"])
                #Draw on temp layer
                if QGis.QGIS_VERSION_INT >= 10900:
                    self.rubberband.reset(QGis.Line)
                else:
                    self.rubberband.reset(self.polygon)
                for i in range(0,len(self.pointstoDraw)):
                     self.rubberband.addPoint(QgsPoint(self.pointstoDraw[i][0],self.pointstoDraw[i][1]))
                self.rubberband.addPoint(QgsPoint(mapPos.x(),mapPos.y()))
        if self.selectionmethod == 1:
            return



    def rightClicked(self,position):    #used to quit the current action
        if self.selectionmethod == 0:
            mapPos = self.canvas.getCoordinateTransform().toMapCoordinates(position["x"],position["y"])
            newPoints = [[mapPos.x(), mapPos.y()]]
            #if newPoints == self.lastClicked: return # sometimes a strange "double click" is given
            if len(self.pointstoDraw) > 0:
                self.pointstoDraw = []
                self.pointstoCal = []
                self.rubberband.reset(self.polygon)
            else:
                self.cleaning()
        if self.selectionmethod == 1:
            try:
                self.previousLayer.removeSelection( False )
            except:
                self.iface.mainWindow().statusBar().showMessage("error right click")
            self.cleaning()



    def leftClicked(self,position):
        self.doubleClicked(position)

    def doubleClicked(self,position):
        if self.selectionmethod == TemporalSpectralProfilePlugin.POINT_SELECTION:
            #Validation of line
            mapPos = self.canvas.getCoordinateTransform().toMapCoordinates(position["x"],position["y"])
            newPoints = [[mapPos.x(), mapPos.y()]]
            self.pointstoDraw += newPoints
            #launch analyses
            self.iface.mainWindow().statusBar().showMessage(str(self.pointstoDraw))
            self.doprofile.calculatePointProfile(self.pointstoDraw,self.mdl, self.plotlibrary)
            #Reset
            self.lastFreeHandPoints = self.pointstoDraw
            self.pointstoDraw = []
            #temp point to distinct leftclick and dbleclick
            self.dblclktemp = newPoints
            #self.iface.mainWindow().statusBar().showMessage(self.textquit0)
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
        QObject.connect(self.pointTool, SIGNAL("moved"), self.moved)
        QObject.connect(self.pointTool, SIGNAL("rightClicked"), self.rightClicked)
        QObject.connect(self.pointTool, SIGNAL("leftClicked"), self.leftClicked)
        QObject.connect(self.pointTool, SIGNAL("doubleClicked"), self.doubleClicked)
        QObject.connect(self.pointTool, SIGNAL("deactivate"), self.deactivatePointMapTool)
        

    def deactivatePointMapTool(self):        #enable clean exit of the plugin
        QObject.disconnect(self.pointTool, SIGNAL("moved"), self.moved)
        QObject.disconnect(self.pointTool, SIGNAL("leftClicked"), self.leftClicked)
        QObject.disconnect(self.pointTool, SIGNAL("rightClicked"), self.rightClicked)
        QObject.disconnect(self.pointTool, SIGNAL("doubleClicked"), self.doubleClicked)
        #QObject.disconnect(self.iface.mapCanvas(), SIGNAL("selectionChanged(QgsMapLayer *)"), self.selectionChanged)
        self.rubberband.reset(self.polygon)
        self.iface.mainWindow().statusBar().showMessage("")

    def connectSelectedPolygonsTool(self):
        QObject.connect(self.iface.mapCanvas(), SIGNAL("selectionChanged(QgsMapLayer *)"), self.selectionChanged)
        
    def deactivagteSelectedPolygonsTools(self):
        QObject.disconnect(self.iface.mapCanvas(), SIGNAL("selectionChanged(QgsMapLayer *)"), self.selectionChanged)

    def cleaning(self):            #used on right click
        try:
            self.previousLayer.removeSelection(False)
        except:
            pass
        self.canvas.unsetMapTool(self.pointTool)
        self.canvas.setMapTool(self.saveTool)
        self.iface.mainWindow().statusBar().showMessage( "" )

    def cleaning2(self):        #used when Dock dialog is closed
        QObject.disconnect(self.wdg.tableView,SIGNAL("clicked(QModelIndex)"), self._onClick)
        self.deactivagteSelectedPolygonsTools() 
        self.deactivatePointMapTool()
        QObject.disconnect(self.wdg.comboBox, SIGNAL("currentIndexChanged(int)"), self.selectionMethod)
        QObject.disconnect(QgsMapLayerRegistry.instance(), SIGNAL("layersWillBeRemoved (QStringList)"), self.onLayersWillBeRemoved)
        self.tableViewTool.layerAddedOrRemoved.disconnect(self.refreshPlot)
        self.mdl = None
        self.dockOpened = False
        self.cleaning()
        self.wdg = None

    #***************************** Options *******************************************

    def selectionMethod(self,item):
        if item == TemporalSpectralProfilePlugin.POINT_SELECTION:
            self.selectionmethod = TemporalSpectralProfilePlugin.POINT_SELECTION
            self.pointTool.setCursor(Qt.CrossCursor)
            self.deactivagteSelectedPolygonsTools()
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

    def addLayer(self, layer = None):
        if layer is None:
            layer = self.iface.activeLayer()
        if isProfilable(layer):
            self.tableViewTool.addLayer(self.iface, self.mdl, layer)
            layer.dataChanged.connect(self.refreshPlot)

    def _onClick(self,index1):                    #action when clicking the tableview
        self.tableViewTool.onClick(self.iface, self.wdg, self.mdl, self.plotlibrary, index1)

    def removeLayer(self, index = None):
        if index is None:
            index = self.tableViewTool.chooseLayerForRemoval(self.iface, self.mdl)
        
        if index is not None:
            layer = self.mdl.index(index, 3).data()
            try:
                layer.dataChanged.disconnect(self.refreshPlot)
            # In case the same layer is added multiple times to the tool 
            except TypeError:
                pass
            self.tableViewTool.removeLayer(self.mdl, index)

    def about(self):
        from ui.dlgabout import DlgAbout
        DlgAbout(self.iface.mainWindow()).exec_()

    def refreshPlot(self):
        """
            Refreshes/updates the plot without requiring the user to 
            redraw the plot line (rubberband)
        """
        if self.selectionmethod == 0:
            if len(self.lastFreeHandPoints) > 1:
                self.doprofile.calculateProfil(self.lastFreeHandPoints, self.mdl, self.plotlibrary)
