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

from math import log10, floor, ceil, sqrt, isnan

from qgis.core import *
from qgis.gui import *
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtSvg import *
import platform

has_qwt = False
has_mpl = False
try:
    from PyQt4.Qwt5 import *
    has_qwt = True
    import itertools # only needed for Qwt plot
except:
    pass
try:
    import matplotlib
    has_mpl = True
except:
    pass



class PlottingTool:


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
            from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg

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
            for i in range(0 , model1.rowCount()):
                tmp_name = ("%s#%d") % (profiles[i]["layer"].name(), i)
                profileName = model1.item(i,4).data(Qt.EditRole)

                # As QwtPlotCurve doesn't support nodata, split the data into single lines
                # with breaks wherever data is None.
                # Prepare two lists of coordinates (xx and yy). Make x=None whenever y==None.
                xx = profiles[i]["l"]
                yy = profiles[i][profileName]
                for j in range(len(yy)):
                    if yy[j] is None or isnan(yy[j]):
                        xx[j] = None
                        yy[j] = None

                # Split xx and yy into single lines at None values
                xx = [list(g) for k,g in itertools.groupby(xx, lambda x:x is None) if not k]
                yy = [list(g) for k,g in itertools.groupby(yy, lambda x:x is None) if not k]

                # Create & attach one QwtPlotCurve per one single line
                for j in range(len(xx)):
                    curve = QwtPlotCurve(tmp_name)
                    curve.setData(xx[j], yy[j])

                    curve.setPen(QPen(model1.item(i,1).data(Qt.BackgroundRole), 3))
                    curve.attach(wdg.plotWdg)
                    if model1.item(i,0).data(Qt.CheckStateRole):
                        curve.setVisible(True)
                    else:
                        curve.setVisible(False)

                #scaling this
                try:
                    wdg.setAxisScale(2,0,max(profiles[len(profiles) - 1]["l"]),0)
                    self.reScalePlot(wdg, profiles, profileName, library)
                except:
                    pass
            wdg.plotWdg.replot()
            
        elif library == "Matplotlib" and has_mpl:
            for i in range(0 , model1.rowCount()):
                tmp_name = ("%s#%d") % (profiles[i]["layer"].name(), i)
                profileName = model1.item(i,4).data(Qt.EditRole)
                
                xx = profiles[i]["l"]
                yy = profiles[i][profileName]
                
                # Don't plot if there are no valid values
                validValues = False
                for j in range(len(yy)):
                    if not (yy[j] is None or isnan(yy[j])):
                        validValues = True
                        break
                if not validValues:
                    continue        

                if model1.item(i,0).data(Qt.CheckStateRole):
                    wdg.plotWdg.figure.get_axes()[0].plot(xx, yy, gid = tmp_name, linewidth = 3, visible = True)
                else:
                    wdg.plotWdg.figure.get_axes()[0].plot(xx, yy, gid = tmp_name, linewidth = 3, visible = False)
                self.changeColor(wdg, "Matplotlib", model1.item(i,1).data(Qt.BackgroundRole), tmp_name)
                try:
                    self.reScalePlot(wdg, profiles, profileName, library)
                    wdg.plotWdg.figure.get_axes()[0].set_xbound( 1, max(profiles[len(profiles) - 1]["l"]) )
                except:
                    pass
            wdg.plotWdg.figure.get_axes()[0].redraw_in_frame()
            wdg.plotWdg.draw()


    def findMin(self,profiles, profileName, nr):
        minVal = min( z for z in profiles[nr][profileName] if z is not None )
        maxVal = max( profiles[nr][profileName] )
        d = ( maxVal - minVal ) or 1
        minVal =  minVal - d*0.05
        return floor(minVal) if abs(minVal) > 1 else minVal

    def findMax(self,profiles, profileName, nr):
        minVal = min( z for z in profiles[nr][profileName] if z is not None )
        maxVal = max( profiles[nr][profileName] )
        d = ( maxVal - minVal ) or 1
        maxVal =  maxVal + d*0.05
        return ceil(maxVal) if abs(maxVal) > 1 else maxVal

    def reScalePlot(self, wdg, profiles, model, library):                         # called when spinbox value changed
        if profiles == None:
            return
        minimumValue = wdg.sbMinVal.value()
        maximumValue = wdg.sbMaxVal.value()
        if minimumValue == maximumValue:
            # Automatic mode
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
                wdg.plotWdg.figure.get_axes()[0].redraw_in_frame()
                wdg.plotWdg.draw()

    def calculateSpinStep(self, minimum, maximum):
        valueRange = maximum - minimum
        if valueRange is None or valueRange <= 0:
            return 0
        step = valueRange / 10.0
        return round(step, -int(floor(log10(step))))

    def clearData(self, wdg, profiles, library):                             # erase one of profiles
        if not profiles:
            return
        if library == "Qwt5" and has_qwt:
            wdg.plotWdg.clear()
            for i in range(0,len(profiles)):
                profileNames = profiles[i].keys()
                for name in profileNames:
                    profiles[i][name] = []
            temp1 = wdg.plotWdg.itemList()
            for j in range(len(temp1)):
                if temp1[j].rtti() == QwtPlotItem.Rtti_PlotCurve:
                    temp1[j].detach()
            #wdg.plotWdg.replot()
        elif library == "Matplotlib" and has_mpl:
            wdg.plotWdg.figure.get_axes()[0].cla()
            self.manageMatplotlibAxe(wdg.plotWdg.figure.get_axes()[0])
            #wdg.plotWdg.figure.get_axes()[0].redraw_in_frame()
            #wdg.plotWdg.draw()
        wdg.sbMaxVal.setEnabled(False)
        wdg.sbMinVal.setEnabled(False)
        wdg.sbMaxVal.setValue(0)
        wdg.sbMinVal.setValue(0)


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
        axe1.grid()
        axe1.tick_params(axis = "both", which = "major", direction= "out", length=10, width=1, bottom = True, top = False, left = True, right = False)
        axe1.minorticks_on()
        axe1.tick_params(axis = "both", which = "minor", direction= "out", length=5, width=1, bottom = True, top = False, left = True, right = False)


    def outPrint(self, iface, wdg, mdl, library): # Postscript file rendering doesn't work properly yet.
        for i in range (0,mdl.rowCount()):
            if  mdl.item(i,0).data(Qt.CheckStateRole):
                name = str(mdl.item(i,2).data(Qt.EditRole))
                #return
        fileName = QFileDialog.getSaveFileName(iface.mainWindow(), "Save As","Profile of " + name + ".ps","PostScript Format (*.ps)")
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
        fileName = QFileDialog.getSaveFileName(iface.mainWindow(), "Save As","Profile of " + name + ".pdf","Portable Document Format (*.pdf)")
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
        fileName = QFileDialog.getSaveFileName(iface.mainWindow(), "Save As","Profile of " + name + ".svg","Scalable Vector Graphics (*.svg)")
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
        fileName = QFileDialog.getSaveFileName(iface.mainWindow(), "Save As","Profile of " + name + ".png","Portable Network Graphics (*.png)")
        if fileName:
            if library == "Qwt5" and has_qwt:
                QPixmap.grabWidget(wdg.plotWdg).save(fileName, "PNG")
            elif library == "Matplotlib" and has_mpl:
                wdg.plotWdg.figure.savefig(str(fileName))
