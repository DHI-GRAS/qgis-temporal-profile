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
from qgis.core import *

import platform
from math import sqrt


class DataReaderTool:

	"""def __init__(self):
		self.profiles = None"""

	def dataReaderTool(self, iface1, tool1, profile1, pointtoDraw):
		"""
		Return a dictionnary : {"layer" : layer read,
								"z" : array of computed z
		"""
		#init
		self.tool = tool1						#needed to transform point coordinates
		self.profiles = profile1				#profile with layer and band to compute
		self.pointtoDraw = pointtoDraw		#the polyline to compute
		self.iface = iface1						#QGis interface to show messages in status bar
		z = None

		layer = self.profiles["layer"]
		
		# this code adapted from valuetool plugin
		pointstoCal = self.tool.toLayerCoordinates(self.profiles["layer"] , QgsPoint(self.pointtoDraw[0],self.pointtoDraw[1]))
		x = float(pointstoCal.x())
		y = float(pointstoCal.y())
		if layer:
			try:
				ident = layer.dataProvider().identify(QgsPoint(x,y), QgsRaster.IdentifyFormatValue )
			except:
				ident = None
		else:
			ident = None
		#if ident is not None and ident.has_key(choosenBand+1):
		if ident is not None:
			z = ident.results().values()
			l = ident.results().keys()

			
		self.profiles["z"] = z
		self.profiles["l"] = l
		return self.profiles	







