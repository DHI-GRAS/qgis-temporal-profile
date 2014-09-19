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


from qgis.core import *
from qgis.gui import *
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from plottingtool import *
from utils import isProfilable


class TableViewTool(QObject):
	
	layerAddedOrRemoved = pyqtSignal() # Emitted when a new layer is added

	def addLayer(self , iface, mdl, layer1 = None):
		if layer1 == None:
			templist=[]
			j=0
			# Ask the layer by a input dialog 
			for i in range(0, iface.mapCanvas().layerCount()):
				donothing = False
				layer = iface.mapCanvas().layer(i)
				if isProfilable(layer):
					for j in range(0, mdl.rowCount()):
						if str(mdl.item(j,2).data(Qt.EditRole)) == str(layer.name()):
							donothing = True
				else:
					donothing = True
					
				if donothing == False:
					templist +=  [[layer, layer.name()]]
						
			if len(templist) == 0:
				QMessageBox.warning(iface.mainWindow(), "Profile tool", "No raster to add")
				return
			else:	
				testqt, ok = QInputDialog.getItem(iface.mainWindow(), "Layer selector", "Choose layer", [templist[k][1] for k in range( len(templist) )], False)
				if ok:
					for i in range (0,len(templist)):
						if templist[i][1] == testqt:
							layer2 = templist[i][0]
				else:
					return
		else : 
			layer2 = layer1

		#Complete the tableview
		row = mdl.rowCount()
		mdl.insertRow(row)
		mdl.setData( mdl.index(row, 0, QModelIndex())  ,True, Qt.CheckStateRole)
		mdl.item(row,0).setFlags(Qt.ItemIsSelectable) 
		lineColour = Qt.red
		mdl.setData( mdl.index(row, 1, QModelIndex())  ,QColor(lineColour) , Qt.BackgroundRole)
		mdl.item(row,1).setFlags(Qt.NoItemFlags) 
		mdl.setData( mdl.index(row, 2, QModelIndex())  ,layer2.name())
		mdl.item(row,2).setFlags(Qt.NoItemFlags)  
		mdl.setData( mdl.index(row, 3, QModelIndex())  ,layer2)
		mdl.item(row,3).setFlags(Qt.NoItemFlags)
		self.layerAddedOrRemoved.emit()
		
		
	def removeLayer(self, iface, mdl, index = None):
		if not index == None :
			try:
				mdl.removeRow(index)
				self.layerAddedOrRemoved.emit()
				return
			except:
				return
			
		if mdl.rowCount() < 2:
			if mdl.rowCount() == 1:
				mdl.removeRow(0)
				return

		list1 = []
		for i in range(0,mdl.rowCount()):
			list1.append(str(i +1) + " : " + mdl.item(i,2).data(Qt.EditRole))
		testqt, ok = QInputDialog.getItem(iface.mainWindow(), "Layer selector", "Choose the Layer", list1, False)
		if ok:
			for i in range(0,mdl.rowCount()):
				if testqt == (str(i+1) + " : " + mdl.item(i,2).data(Qt.EditRole)):
					mdl.removeRow(i)
					break
		self.layerAddedOrRemoved.emit()
		
	def onClick(self, iface, wdg, mdl, plotlibrary, index1):					#action when clicking the tableview
		temp = mdl.itemFromIndex(index1)
		if index1.column() == 1:				#modifying color
			name = ("%s#") % (mdl.item(index1.row(),2).data(Qt.EditRole))
			color = QColorDialog().getColor(temp.data(Qt.BackgroundRole))
			mdl.setData( mdl.index(temp.row(), 1, QModelIndex())  ,color , Qt.BackgroundRole)
			PlottingTool().changeColor(wdg, plotlibrary, color, name)
		elif index1.column() == 0:				#modifying checkbox
			name = mdl.item(index1.row(),2).data(Qt.EditRole)			
			booltemp = temp.data(Qt.CheckStateRole)
			if booltemp == True:
				booltemp = False
			else:
				booltemp = True
			mdl.setData( mdl.index(temp.row(), 0, QModelIndex())  ,booltemp, Qt.CheckStateRole)
			PlottingTool().changeAttachCurve(wdg, plotlibrary, booltemp, name)
		else:
			return

		
