Temporal/Spectral Profile Tool
=====================

A QGIS plugin for interactive plotting of temporal or spectral information stored in multi-band rasters. Based on Profile tool plugin.

After installation and activation the plugin can be accessed either from main menu (under Plugins > Profile Tool > Temporal/Spectral Profile) or from an icon on the taskbar:

![](https://github.com/TIGER-NET/screenshots/blob/master/Temporal_profile_tool/menu.png)

The tool can be used to compare spectral information contained in multiple multi-band rasters, for example to asses the accuracy of atmospheric correction or to interactively explore changes between the rasters:

![](https://github.com/TIGER-NET/screenshots/blob/master/Temporal_profile_tool/spectral_profile.png)

It can also be used to plot pixel time-series data from a list of rasters which have previously been stacked in, for example, a virtual raster (.VRT) file:

![](https://github.com/TIGER-NET/screenshots/blob/master/Temporal_profile_tool/temporal_profile.png)

New functionality in version 1.1 allows the plotting of zonal statistics' time-series by using the "Selected Polygon" option and choosing the statistic to plot from a list next to the raster layer name:

![](https://github.com/TIGER-NET/screenshots/blob/master/Temporal_profile_tool/temporal_profile_polygon.png)

The information can be presented either as a graph (profile) or in tabular form using the tabs at the top of the tool. It is also possible to save the graph as a pdf or an image using the buttons below the graph, as well as to change some graph properties if Matplotlib is used as the plotting library.

New functionality in version 1.2 allows for changing the x-axis steps. They can either remain as band numbers (as was the case in previous versions), or be set based on string or based on regular time-steps. 

![](https://github.com/TIGER-NET/screenshots/blob/master/Temporal_profile_tool/temporal_profile_xaxis_steps.png)

The string for setting the x-axis steps must contain only numbers (including "nan") delimited by ";". The number of steps will be truncated to the minimum of the number of steps in the string and the number of bands in the raster. It is possible to skip a raster band during plotting by setting the corresponding step to "nan".

The time-step option only works if Matplotlib is chosen as the plotting library. A time step of "months" is approximated as 365/12 days and a time step of "years" is approximated as 365 days. If NetCDF with time dimension is used as the raster data source then the plugin can also use this dimension's dates during plotting.

In addition, when Matplotlib is used as the plotting library, the built-in "Figure options" can be used to customise the look of the axes and the curves.

![](https://github.com/TIGER-NET/screenshots/blob/master/Temporal_profile_tool/temporal_profile_figure_options.png)

This plugin was initially developed under the TIGER-NET project (www.tiger-net.org) funded by the European Space Agency (ESA) and currently is part of GlobWetland Africa Toolbox (http://globwetland-africa.org) also funded by ESA.

Copyright (C) 2020 DHI-GRAS A/S (http://www.dhi-gras.com).

Based on Profile tool plugin:
  Copyright (C) 2008 Borys Jurgiel,
  Copyright (C) 2012 Patrice Verchere
