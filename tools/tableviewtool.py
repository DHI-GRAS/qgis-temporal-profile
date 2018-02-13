# -*- coding: utf-8 -*-

"""
***************************************************************************
   tableviewtool.py
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
from __future__ import absolute_import
from builtins import str
from builtins import range
import uuid

from qgis.PyQt.QtCore import Qt, QObject, QModelIndex, pyqtSignal
from qgis.PyQt.QtWidgets import QMessageBox, QInputDialog, QColorDialog, QInputDialog
from qgis.PyQt.QtGui import QColor
from .plottingtool import PlottingTool


class TableViewTool(QObject):
    
    layerAddedOrRemoved = pyqtSignal() # Emitted when a new layer is added
    
    # Colour Brewer Set 1: http://colorbrewer2.org/#type=qualitative&scheme=Set1&n=9
    colourSet = [(228,26,28), (55,126,184), (77,175,74), (152,78,163), (255,127,0),
                 (255,255,51), (166,86,40), (247,129,191), (153,153,153)]
    colourIndex = 0

    def pickColour(self):
        colour = self.colourSet[self.colourIndex]
        colour = QColor(colour[0], colour[1], colour[2])
        
        self.colourIndex = self.colourIndex + 1
        if self.colourIndex == len(self.colourSet):
            self.colourIndex = 0
        return colour

    def addLayer(self , iface, mdl, layer):
        row = mdl.rowCount()
        mdl.insertRow(row)
        mdl.setData( mdl.index(row, 0, QModelIndex()), True, Qt.CheckStateRole)
        mdl.item(row,0).setFlags(Qt.ItemIsSelectable) 
        lineColour = self.pickColour()
        mdl.setData( mdl.index(row, 1, QModelIndex()), QColor(lineColour) , Qt.BackgroundRole)
        mdl.item(row,1).setFlags(Qt.NoItemFlags) 
        mdl.setData( mdl.index(row, 2, QModelIndex()), layer.name())
        mdl.item(row,2).setFlags(Qt.NoItemFlags)  
        mdl.setData( mdl.index(row, 3, QModelIndex()), layer)
        mdl.item(row,3).setFlags(Qt.NoItemFlags)
        mdl.setData(mdl.index(row, 4, QModelIndex()), "")
        mdl.item(row,4).setFlags(Qt.NoItemFlags)
        mdl.setData(mdl.index(row, 5, QModelIndex()), layer.name()+str(uuid.uuid4()))
        mdl.item(row,5).setFlags(Qt.NoItemFlags)
        self.layerAddedOrRemoved.emit()
        
    def removeLayer(self, mdl, index):
            try:
                mdl.removeRow(index)
                self.layerAddedOrRemoved.emit()
            except:
                return

    def chooseLayerForRemoval(self, iface, mdl):
        if mdl.rowCount() < 2:
            if mdl.rowCount() == 1:
                return 0
            return None

        list1 = []
        for i in range(0,mdl.rowCount()):
            list1.append(str(i +1) + " : " + mdl.item(i,2).data(Qt.EditRole))
        testqt, ok = QInputDialog.getItem(iface.mainWindow(), "Layer selector", "Choose the Layer", list1, False)
        if ok:
            for i in range(0,mdl.rowCount()):
                if testqt == (str(i+1) + " : " + mdl.item(i,2).data(Qt.EditRole)):
                    return i
        return None

    def onClick(self, iface, wdg, mdl, plotlibrary, index):                    #action when clicking the tableview
        item = mdl.itemFromIndex(index)
        name = mdl.item(index.row(),5).data(Qt.EditRole)
        if index.column() == 1:                #modifying color
            color = QColorDialog().getColor(item.data(Qt.BackgroundRole))
            mdl.setData( mdl.index(item.row(), 1, QModelIndex())  ,color , Qt.BackgroundRole)
            PlottingTool().changeColor(wdg, plotlibrary, color, name)
        elif index.column() == 0:                #modifying checkbox
            isVisible = not(item.data(Qt.CheckStateRole))
            mdl.setData( mdl.index(item.row(), 0, QModelIndex()), isVisible, Qt.CheckStateRole)
            PlottingTool().changeAttachCurve(wdg, plotlibrary, isVisible, name)
        else:
            return
