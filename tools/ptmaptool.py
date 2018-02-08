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

from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QCursor
from qgis.gui import QgsMapTool
from qgis.core import QgsPointXY


class ProfiletoolMapTool(QgsMapTool):

    moved = pyqtSignal(QgsPointXY)
    rightClicked = pyqtSignal(QgsPointXY)
    leftClicked = pyqtSignal(QgsPointXY)
    doubleClicked = pyqtSignal(QgsPointXY)

    def __init__(self, canvas, button):
        QgsMapTool.__init__(self,canvas)
        self.canvas = canvas
        self.cursor = QCursor(Qt.CrossCursor)

    def canvasMoveEvent(self,event):
        self.moved.emit(event.originalMapPoint())

    def canvasReleaseEvent(self,event):
        if event.button() == Qt.RightButton:
            self.rightClicked.emit(event.originalMapPoint())
        else:
            self.leftClicked.emit(event.originalMapPoint())

    def canvasDoubleClickEvent(self,event):
        self.doubleClicked.emit(event.originalMapPoint())

    def activate(self):
        QgsMapTool.activate(self)
        self.canvas.setCursor(self.cursor)

    def isZoomTool(self):
        return False

    def setCursor(self,cursor):
        self.cursor = QCursor(cursor)
