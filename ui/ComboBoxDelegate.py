# -*- coding: utf-8 -*-

"""
***************************************************************************
   ComboBoxDelegate.py
-------------------------------------
    Copyright (C) 2015 TIGER-NET (www.tiger-net.org)
    


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

class ComboBoxDelegate(QItemDelegate):

    def __init__(self, parent, itemList):
        QItemDelegate.__init__(self, parent)
        self.itemList = itemList
    
    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        for item in self.itemList:
            editor.addItem(item)
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.EditRole)
        if editor.findText(value) >= 0:
            editor.setCurrentIndex(editor.findText(value))
        else:
            editor.setCurrentIndex(0)
            self.setModelData(editor, index.model(), index)

    def setModelData(self, editor, model, index):
        value = editor.currentText()
        model.setData(index, value, Qt.EditRole)
 
    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)
        