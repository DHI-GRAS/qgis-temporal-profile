"""
***************************************************************************
   ptmaptool.py
-------------------------------------
    
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

from PyQt4.QtCore import Qt, SIGNAL
from PyQt4.QtGui import QCursor
from qgis.gui import QgsMapTool


class ProfiletoolMapTool(QgsMapTool):

    def __init__(self, canvas,button):
        QgsMapTool.__init__(self,canvas)
        self.canvas = canvas
        self.cursor = QCursor(Qt.CrossCursor)

    def canvasMoveEvent(self, event):
        self.emit( SIGNAL("moved"), event.originalMapPoint())

    def canvasReleaseEvent(self,event):
        if event.button() == Qt.RightButton:
            self.emit( SIGNAL("rightClicked"), event.originalMapPoint())
        else:
            self.emit( SIGNAL("leftClicked"), event.originalMapPoint())

    def canvasDoubleClickEvent(self,event):
        self.emit( SIGNAL("doubleClicked"), event.originalMapPoint())

    def activate(self):
        QgsMapTool.activate(self)
        self.canvas.setCursor(self.cursor)

    def isZoomTool(self):
        return False

    def setCursor(self,cursor):
        self.cursor = QCursor(cursor)
