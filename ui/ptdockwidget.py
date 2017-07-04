# -*- coding: utf-8 -*-

"""
***************************************************************************
   temporalprofileplugin.py
-------------------------------------
    Copyright (C) 2014 TIGER-NET (www.tiger-net.org)
    
    Based on Profile tool plugin:
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

from PyQt4 import uic
from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *
from qgis.gui import *

from ..tools.plottingtool import *
#from ..profileplugin import ProfilePlugin

try:
    from PyQt4.Qwt5 import *
    Qwt5_loaded = True
except ImportError:
    Qwt5_loaded = False
try:
    #from matplotlib import *
    import matplotlib
    matplotlib_loaded = True
except ImportError:
    matplotlib_loaded = False

import platform
import os


from ComboBoxDelegate import ComboBoxDelegate
uiFilePath = os.path.abspath(os.path.join(os.path.dirname(__file__), 'profiletool.ui'))
FormClass = uic.loadUiType(uiFilePath)[0]

class PTDockWidget(QDockWidget, FormClass):

    TITLE = "ProfileTool"

    def __init__(self, parent, iface1, mdl1):
        QDockWidget.__init__(self, parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.parent = parent
        self.location = Qt.RightDockWidgetArea
        self.iface = iface1

        self.setupUi(self)
        #self.connect(self, SIGNAL("dockLocationChanged(Qt::DockWidgetArea)"), self.setLocation)
        self.mdl = mdl1
        #self.showed = False
        
        QObject.connect(self.mdl, SIGNAL("rowsInserted(QModelIndex, int, int)"), self.addPersistentEditorForRows)
        QObject.connect(self.cboXAxis, SIGNAL("currentIndexChanged(int)"), self.changeXAxisLabeling)
        QObject.connect(self.butLoadXAxisSteps, SIGNAL("clicked()"), self.loadXAxisStepsFromFile)
        QObject.connect(self.butSaveAs, SIGNAL("clicked()"), self.saveAs)

    def showIt(self):
        self.location = Qt.BottomDockWidgetArea
        minsize = self.minimumSize()
        maxsize = self.maximumSize()
        self.setMinimumSize(minsize)
        self.setMaximumSize(maxsize)
        self.iface.mapCanvas().setRenderFlag(False)

        #TableWiew thing
        self.tableView.setModel(self.mdl)
        self.tableView.setColumnWidth(0, 20)
        self.tableView.setColumnWidth(1, 20)
        self.tableView.setColumnWidth(2, 150)
        self.tableView.setColumnHidden(3 , True)
        self.tableView.setColumnWidth(4, 30)
        self.tableView.setItemDelegateForColumn(4,ComboBoxDelegate(self.tableView, ["value"]))
        hh = self.tableView.horizontalHeader()
        hh.setStretchLastSection(True)
        self.mdl.setHorizontalHeaderLabels(["","","Layer","", "Stat"])
        self.tableView.verticalHeader().hide()

        #The ploting area
        self.plotWdg = None
        #Draw the widget
        self.iface.addDockWidget(self.location, self)
        self.iface.mapCanvas().setRenderFlag(True)

    def addPersistentEditorForRows(self, parent, startRow, endRow):
        for row in range(startRow, endRow+1):
            self.tableView.openPersistentEditor(self.mdl.index(row, 4))
        
    def changeStatComboBoxItems(self, itemList, defaultStat = ""):
        for row in range(self.mdl.rowCount()):
            self.tableView.closePersistentEditor(self.mdl.index(row, 4))
        statComboBoxDelegate = ComboBoxDelegate(self.tableView, itemList, defaultStat)
        self.tableView.setItemDelegateForColumn(4,statComboBoxDelegate)
        for row in range(self.mdl.rowCount()):
            self.tableView.openPersistentEditor(self.mdl.index(row, 4))

    def addOptionComboboxItems(self):
        if Qwt5_loaded:
            self.cboLibrary.addItem("Qwt5")
        if matplotlib_loaded:
            self.cboLibrary.addItem("Matplotlib")
            
        self.cboXAxis.addItem("Band numbers")
        self.cboXAxis.addItem("From string")
        self.cboXAxis.addItem("Time")
        
    def changeXAxisLabeling(self):
        if self.cboXAxis.currentIndex() == 0:
            self.leXAxisSteps.setEnabled(False)
            self.butLoadXAxisSteps.setEnabled(False)
            self.dateTimeEditCurrentTime.setEnabled(False)
            self.spinBoxTimeExtent.setEnabled(False)
            self.cboTimeExtent.setEnabled(False)
            self.cbTimeDimension.setEnabled(False)
        elif self.cboXAxis.currentIndex() == 1:
            self.leXAxisSteps.setEnabled(True)
            self.butLoadXAxisSteps.setEnabled(True)
            self.dateTimeEditCurrentTime.setEnabled(False)
            self.spinBoxTimeExtent.setEnabled(False)
            self.cboTimeExtent.setEnabled(False)
            self.cbTimeDimension.setEnabled(False)
        elif self.cboXAxis.currentIndex() == 2:
            self.leXAxisSteps.setEnabled(False)
            self.butLoadXAxisSteps.setEnabled(False)
            self.dateTimeEditCurrentTime.setEnabled(True)
            self.spinBoxTimeExtent.setEnabled(True)
            self.cboTimeExtent.setEnabled(True)
            self.cbTimeDimension.setEnabled(True)
            
    def loadXAxisStepsFromFile(self):
        fileName = QFileDialog.getOpenFileName(self, "Load X axis steps","","Text file (*.txt)")
        if fileName:
            with open(fileName) as fp:
                self.leXAxisSteps.setText(fp.readline())
                self.leXAxisSteps.editingFinished.emit()

    def closeEvent(self, event):
        self.emit( SIGNAL( "closed(PyQt_PyObject)" ), self )
        QObject.disconnect(self.butSaveAs, SIGNAL("clicked()"), self.saveAs)
        return QDockWidget.closeEvent(self, event)

    def addPlotWidget(self, library):
        layout = self.frame_for_plot.layout()
        while layout.count():
                        child = layout.takeAt(0)
                        child.widget().deleteLater()

        if library == "Qwt5":
            self.stackedWidget.setCurrentIndex(0)
            widget1 = self.stackedWidget.widget(1)
            if widget1:
                    self.stackedWidget.removeWidget( widget1 )
                    widget1 = None
            #self.widget_save_buttons.setVisible( True )
            self.plotWdg = PlottingTool().changePlotWidget("Qwt5", self.frame_for_plot)
            layout.addWidget(self.plotWdg)

            if QT_VERSION < 0X040100:
                                idx = self.cbxSaveAs.model().index(0, 0)
                                self.cbxSaveAs.model().setData(idx, QVariant(0), Qt.UserRole - 1)
                                self.cbxSaveAs.setCurrentIndex(1)
            if QT_VERSION < 0X040300:
                                idx = self.cbxSaveAs.model().index(1, 0)
                                self.cbxSaveAs.model().setData(idx, QVariant(0), Qt.UserRole - 1)
                                self.cbxSaveAs.setCurrentIndex(2)

        elif library == "Matplotlib":
            self.stackedWidget.setCurrentIndex(0)
            #self.widget_save_buttons.setVisible( False )
            self.plotWdg = PlottingTool().changePlotWidget("Matplotlib", self.frame_for_plot)
            layout.addWidget(self.plotWdg)
            try:
                mpltoolbar = matplotlib.backends.backend_qt4agg.NavigationToolbar2QTAgg(self.plotWdg, self.frame_for_plot)
            except AttributeError:
                mpltoolbar = matplotlib.backends.backend_qt4agg.NavigationToolbar2QT(self.plotWdg, self.frame_for_plot)
            #layout.addWidget( mpltoolbar )
            self.stackedWidget.insertWidget(1, mpltoolbar)
            self.stackedWidget.setCurrentIndex(1)
            lstActions = mpltoolbar.actions()
            #mpltoolbar.removeAction( lstActions[ 7 ] )
            #mpltoolbar.removeAction( lstActions[ 8 ] )

    # generic save as button
    def saveAs(self):
            idx = self.cbxSaveAs.currentIndex()
            if idx == 0:
                    self.outPDF()
            elif idx == 1:
                    self.outPNG()
            elif idx == 2:
                    self.outSVG()
            elif idx == 3:
                    self.outPrint()
            else:
                    print('plottingtool: invalid index '+str(idx))

    def outPrint(self): # Postscript file rendering doesn't work properly yet.
        PlottingTool().outPrint(self.iface, self, self.mdl, self.cboLibrary.currentText ())

    def outPDF(self):
        PlottingTool().outPDF(self.iface, self, self.mdl, self.cboLibrary.currentText ())

    def outSVG(self):
        PlottingTool().outSVG(self.iface, self, self.mdl, self.cboLibrary.currentText ())

    def outPNG(self):
        PlottingTool().outPNG(self.iface, self, self.mdl, self.cboLibrary.currentText ())
