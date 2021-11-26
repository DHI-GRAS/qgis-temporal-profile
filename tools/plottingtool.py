# -*- coding: utf-8 -*-

"""
***************************************************************************
   plottingtool.py
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
from builtins import str
from builtins import range
from builtins import object

from math import log10, floor, ceil, isnan
import platform

from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtWidgets import QSizePolicy, QFileDialog
from qgis.PyQt.QtGui import QPen, QPixmap, QColor
from qgis.PyQt.QtPrintSupport import QPrintDialog, QPrinter
from qgis.PyQt.QtSvg import QSvgGenerator

has_qwt = False
has_mpl = False
try:
    from PyQt4.Qwt5 import QwtPlot, QwtPlotZoomer, QwtPicker, QwtPlotPicker, \
                           QwtPlotGrid, QwtPlotCurve, QwtPlotItem, Qwt
    has_qwt = True
    import itertools # only needed for Qwt plot
except:
    pass
try:
    import matplotlib
    has_mpl = True
    from temporalprofiletool import nc_time_axis
except:
    pass


class PlottingTool(object):

    def changePlotWidget(self, library, frame_for_plot):
        if library == "Qwt5" and has_qwt:
            plotWdg = QwtPlot(frame_for_plot)
            sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            sizePolicy.setHorizontalStretch(0)
            sizePolicy.setVerticalStretch(0)
            sizePolicy.setHeightForWidth(plotWdg.sizePolicy().hasHeightForWidth())
            plotWdg.setSizePolicy(sizePolicy)
            plotWdg.setMinimumSize(QSize(0,0))
            plotWdg.setAutoFillBackground(False)
            #Decoration
            plotWdg.setCanvasBackground(Qt.white)
            plotWdg.plotLayout().setAlignCanvasToScales(True)
            zoomer = QwtPlotZoomer(QwtPlot.xBottom, QwtPlot.yLeft, QwtPicker.DragSelection, QwtPicker.AlwaysOff, plotWdg.canvas())
            zoomer.setRubberBandPen(QPen(Qt.blue))
            if platform.system() != "Windows":
                # disable picker in Windows due to crashes
                picker = QwtPlotPicker(QwtPlot.xBottom, QwtPlot.yLeft, QwtPicker.NoSelection, QwtPlotPicker.CrossRubberBand, QwtPicker.AlwaysOn, plotWdg.canvas())
                picker.setTrackerPen(QPen(Qt.green))
            #self.dockwidget.qwtPlot.insertLegend(QwtLegend(), QwtPlot.BottomLegend);
            grid = Qwt.QwtPlotGrid()
            grid.setPen(QPen(QColor('grey'), 0, Qt.DotLine))
            grid.attach(plotWdg)
            return plotWdg
        elif library == "Matplotlib" and has_mpl:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg

            fig = Figure( (1.0, 1.0), linewidth=0.0, subplotpars = matplotlib.figure.SubplotParams(left=0, bottom=0, right=1, top=1, wspace=0, hspace=0)    )

            font = {'family' : 'arial', 'weight' : 'normal', 'size'   : 12}
            matplotlib.rc('font', **font)

            rect = fig.patch
            rect.set_facecolor((0.9,0.9,0.9))

            self.subplot = fig.add_axes((0.07, 0.15, 0.92,0.82))
            self.subplot.set_xbound(0,1000)
            self.subplot.set_ybound(0,1000)
            self.manageMatplotlibAxe(self.subplot)
            canvas = FigureCanvasQTAgg(fig)
            sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            sizePolicy.setHorizontalStretch(0)
            sizePolicy.setVerticalStretch(0)
            canvas.setSizePolicy(sizePolicy)
            return canvas

    def attachCurves(self, wdg, profiles, model1, library):
        if library == "Qwt5" and has_qwt:
                wdg.plotWdg.clear()
        for i in range(0 , model1.rowCount()):
            profileName = model1.item(i,4).data(Qt.EditRole)
            profileId = model1.item(i,5).data(Qt.EditRole)
            isVisible = model1.item(i,0).data(Qt.CheckStateRole)

            xx = profiles[i]["l"]
            yy = profiles[i][profileName]

            if library == "Qwt5" and has_qwt:
                # As QwtPlotCurve doesn't support nodata, split the data into single lines
                # with breaks wherever data is None.
                # Prepare two lists of coordinates (xx and yy). Make x=None whenever y==None.
                for j in range(len(yy)):
                    if yy[j] is None or isnan(yy[j]):
                        xx[j] = None
                        yy[j] = None

                # Split xx and yy into single lines at None values
                xx = [list(g) for k,g in itertools.groupby(xx, lambda x:x is None) if not k]
                yy = [list(g) for k,g in itertools.groupby(yy, lambda x:x is None) if not k]

                # Create & attach one QwtPlotCurve per one single line
                for j in range(len(xx)):
                    curve = QwtPlotCurve(profileId)
                    curve.setData(xx[j], yy[j])

                    curve.setPen(QPen(model1.item(i,1).data(Qt.BackgroundRole), 3))
                    curve.attach(wdg.plotWdg)
                    curve.setVisible(isVisible)

            elif library == "Matplotlib" and has_mpl:
                lines = wdg.plotWdg.figure.get_axes()[0].get_lines()
                lineIds = [line.get_gid() for line in lines]
                # X-axis have to be set before wdg is redrawn in changeColor, otherwise and
                # exception is sometimes thrown when time-based axis is used.
                minimumValueX = min( z for z in profiles[i]["l"])
                maximumValueX = max( z for z in profiles[i]["l"])
                wdg.plotWdg.figure.get_axes()[0].set_xlim([minimumValueX, maximumValueX])
                if profileId in lineIds:
                    # Update existing line
                    line = lines[lineIds.index(profileId)]
                    line.set_data([xx, yy])
                else:
                    # Create new line
                    line = wdg.plotWdg.figure.get_axes()[0].plot(xx, yy, gid = profileId)[0]
                line.set_visible(isVisible)
                self.changeColor(wdg, "Matplotlib", model1.item(i,1).data(Qt.BackgroundRole), profileId)

    def findMin(self,profiles, profileName, nr):
        minVal = min( z for z in profiles[nr][profileName] if z is not None )
        maxVal = max( z for z in profiles[nr][profileName] if z is not None )
        d = ( maxVal - minVal ) or 1
        minVal =  minVal - d*0.05
        return floor(minVal) if abs(minVal) > 1 else minVal

    def findMax(self,profiles, profileName, nr):
        minVal = min( z for z in profiles[nr][profileName] if z is not None )
        maxVal = max( z for z in profiles[nr][profileName] if z is not None )
        d = ( maxVal - minVal ) or 1
        maxVal =  maxVal + d*0.05
        return ceil(maxVal) if abs(maxVal) > 1 else maxVal

    def reScalePlot(self, wdg, profiles, model, library, autoMode = True):                         # called when spinbox value changed
        if profiles == None:
            return

        # Rescale Y-axis
        minimumValue = wdg.sbMinVal.value()
        maximumValue = wdg.sbMaxVal.value()
        if autoMode:
            minimumValue = 1000000000
            maximumValue = -1000000000
            for i in range(0,len(profiles)):
                profileName = model.item(i,4).data(Qt.EditRole)
                if profiles[i]["layer"] != None and len([z for z in profiles[i][profileName] if z is not None]) > 0:
                    if self.findMin(profiles, profileName, i) < minimumValue:
                        minimumValue = self.findMin(profiles, profileName, i)
                    if self.findMax(profiles, profileName, i) > maximumValue:
                        maximumValue = self.findMax(profiles, profileName, i)
            wdg.sbMaxVal.setValue(maximumValue)
            wdg.sbMinVal.setValue(minimumValue)
            wdg.sbMaxVal.setSingleStep(self.calculateSpinStep(minimumValue, maximumValue))
            wdg.sbMinVal.setSingleStep(self.calculateSpinStep(minimumValue, maximumValue))
            wdg.sbMaxVal.setEnabled(True)
            wdg.sbMinVal.setEnabled(True)

        if minimumValue < maximumValue:
            if library == "Qwt5" and has_qwt:
                wdg.plotWdg.setAxisScale(0,minimumValue,maximumValue,0)
                wdg.plotWdg.replot()
            elif library == "Matplotlib" and has_mpl:
                wdg.plotWdg.figure.get_axes()[0].set_ybound(minimumValue,maximumValue)
                wdg.plotWdg.draw()

        # Rescale X-axis
        minimumValueX = None
        maximumValueX = None
        for i in range(0,len(profiles)):
            minimumValueX = min( z for z in profiles[i]["l"])
            maximumValueX = max( z for z in profiles[i]["l"])
        if minimumValueX is None:
            minimumValueX = 0.0
        if maximumValueX is None:
            maximumValueX = 1.0
        if library == "Matplotlib" and has_mpl:
            margin = (maximumValueX - minimumValueX)/50
            wdg.plotWdg.figure.get_axes()[0].set_xlim([minimumValueX-margin, maximumValueX+margin])

    def calculateSpinStep(self, minimum, maximum):
        valueRange = maximum - minimum
        if valueRange is None or valueRange <= 0:
            return 0
        step = valueRange / 10.0
        return round(step, -int(floor(log10(step))))

    def clearData(self, wdg, model, library):
        # Remove only profiles which were removed from the model. This way
        # line styling of existing profiles does not change.
        ids = [model.item(i,5).data(Qt.EditRole) for i in range(model.rowCount())]
        if library == "Qwt5" and has_qwt:
            lines = wdg.plotWdg.itemList()
            linesToRemove = []
            for i, line in enumerate(lines):
                if line.rtti() == QwtPlotItem.Rtti_PlotCurve and \
                   str(line.title().text()) not in ids:
                    linesToRemove.append(line)
            for line in linesToRemove:
                line.detach()
            wdg.plotWdg.replot()
        elif library == "Matplotlib" and has_mpl:
            lines = wdg.plotWdg.figure.get_axes()[0].get_lines()
            for i, line in enumerate(lines):
                if line.get_gid() not in ids:
                    lines.pop(i).remove()
            self.manageMatplotlibAxe(wdg.plotWdg.figure.get_axes()[0])
            wdg.plotWdg.draw()

    def resetAxis(self, wdg, library):
        if library == "Qwt5" and has_qwt:
            wdg.plotWdg.clear()
        elif library == "Matplotlib" and has_mpl:
            wdg.plotWdg.figure.get_axes()[0].cla()
            self.manageMatplotlibAxe(wdg.plotWdg.figure.get_axes()[0])

    def changeColor(self,wdg, library, color1, name):                    #Action when clicking the tableview - color
        if library == "Qwt5":
            temp1 = wdg.plotWdg.itemList()
            for i in range(len(temp1)):
                if name == str(temp1[i].title().text()):
                    curve = temp1[i]
                    curve.setPen(QPen(color1, 3))
                    wdg.plotWdg.replot()
                    # break  # Don't break as there may be multiple curves with a common name (segments separated with None values)
        if library == "Matplotlib":
            temp1 = wdg.plotWdg.figure.get_axes()[0].get_lines()
            for i in range(len(temp1)):
                if name == str(temp1[i].get_gid()):
                    # avoid this issue https://github.com/matplotlib/matplotlib/issues/1690/
                    temp1[i].set_color('#%02x%02x%02x' % (color1.red(), color1.green(), color1.blue()))
                    wdg.plotWdg.draw()
                    break

    def changeAttachCurve(self, wdg, library, isVisible, name):                #Action when clicking the tableview - checkstate
        if library == "Qwt5":
            for curve in wdg.plotWdg.itemList():
                if name == str(curve.title().text()):
                    curve.setVisible(isVisible)
                    wdg.plotWdg.replot()
                    # break  # Don't break as there may be multiple curves with a common name (segments separated with None values)
        if library == "Matplotlib":
            for curve in wdg.plotWdg.figure.get_axes()[0].get_lines():
                if name == str(curve.get_gid()):
                    curve.set_visible(isVisible)
                    wdg.plotWdg.figure.get_axes()[0].redraw_in_frame()
                    wdg.plotWdg.draw()
                    break

    def manageMatplotlibAxe(self, axe1):
        axe1.grid(True)
        axe1.tick_params(axis = "both", which = "major", direction= "out", length=10, width=1, bottom = True, top = False, left = True, right = False)
        axe1.minorticks_on()
        axe1.tick_params(axis = "both", which = "minor", direction= "out", length=5, width=1, bottom = True, top = False, left = True, right = False)

    def outPrint(self, iface, wdg, mdl, library): # Postscript file rendering doesn't work properly yet.
        for i in range (0,mdl.rowCount()):
            if  mdl.item(i,0).data(Qt.CheckStateRole):
                name = str(mdl.item(i,2).data(Qt.EditRole))
                #return
        fileName, __, __ = QFileDialog.getSaveFileName(iface.mainWindow(), "Save As","Profile of " + name + ".ps","PostScript Format (*.ps)")
        if fileName:
            if library == "Qwt5" and has_qwt:
                printer = QPrinter()
                printer.setCreator("QGIS Profile Plugin")
                printer.setDocName("QGIS Profile")
                printer.setOutputFileName(fileName)
                printer.setColorMode(QPrinter.Color)
                printer.setOrientation(QPrinter.Portrait)
                dialog = QPrintDialog(printer)
                if dialog.exec_():
                    wdg.plotWdg.print_(printer)
            elif library == "Matplotlib" and has_mpl:
                wdg.plotWdg.figure.savefig(str(fileName))

    def outPDF(self, iface, wdg, mdl, library):
        for i in range (0,mdl.rowCount()):
            if  mdl.item(i,0).data(Qt.CheckStateRole):
                name = str(mdl.item(i,2).data(Qt.EditRole))
                break
        fileName, _ = QFileDialog.getSaveFileName(iface.mainWindow(), "Save As","Profile of " + name + ".pdf","Portable Document Format (*.pdf)")
        if fileName:
            if library == "Qwt5" and has_qwt:
                printer = QPrinter()
                printer.setCreator('QGIS Profile Plugin')
                printer.setOutputFileName(fileName)
                printer.setOutputFormat(QPrinter.PdfFormat)
                printer.setOrientation(QPrinter.Landscape)
                wdg.plotWdg.print_(printer)
            elif library == "Matplotlib" and has_mpl:
                wdg.plotWdg.figure.savefig(str(fileName))

    def outSVG(self, iface, wdg, mdl, library):
        for i in range (0,mdl.rowCount()):
            if  mdl.item(i,0).data(Qt.CheckStateRole):
                name = str(mdl.item(i,2).data(Qt.EditRole))
                #return
        fileName, _ = QFileDialog.getSaveFileName(iface.mainWindow(), "Save As","Profile of " + name + ".svg","Scalable Vector Graphics (*.svg)")
        if fileName:
            if library == "Qwt5" and has_qwt:
                printer = QSvgGenerator()
                printer.setFileName(fileName)
                printer.setSize(QSize(800, 400))
                wdg.plotWdg.print_(printer)
            elif library == "Matplotlib" and has_mpl:
                wdg.plotWdg.figure.savefig(str(fileName))

    def outPNG(self, iface, wdg, mdl, library):
        for i in range (0,mdl.rowCount()):
            if  mdl.item(i,0).data(Qt.CheckStateRole):
                name = str(mdl.item(i,2).data(Qt.EditRole))
                #return
        fileName, _ = QFileDialog.getSaveFileName(iface.mainWindow(), "Save As","Profile of " + name + ".png","Portable Network Graphics (*.png)")
        if fileName:
            if library == "Qwt5" and has_qwt:
                QPixmap.grabWidget(wdg.plotWdg).save(fileName, "PNG")
            elif library == "Matplotlib" and has_mpl:
                wdg.plotWdg.figure.savefig(str(fileName))
