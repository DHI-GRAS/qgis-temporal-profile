Temporal/Spectral Profile Tool
=====================

A QGIS plugin for interactive plotting of temporal or spectral information stored in multi-band rasters. Based on Profile tool plugin.

After installation and activation the plugin can be accessed either from main menu (under Plugins > Profile Tool > Temporal/Spectral Profile) or from an icon on the taskbar:

![](https://github.com/TIGER-NET/screenshots/blob/master/Temporal_profile_tool/menu.png)

The tool can be used to compare spectral information contained in multiple multi-band rasters, for example to asses the accuracy of atmospheric correction or to interactively explore changes between the rasters:

![](https://github.com/TIGER-NET/screenshots/blob/master/Temporal_profile_tool/spectral_profile.png)

It can also be used to plot pixel time-series data from a list of rasters which have previously been stacked in, for example, a virtual raster (.VRT) file:

![](https://github.com/TIGER-NET/screenshots/blob/master/Temporal_profile_tool/temporal_profile.png)

The information can be presented either as a graph (profile) or in tabular form using the tabs at the top of the tool. It is also possible to save the graph as a pdf or an image using the buttons below the graph, as well as to change some graph properties if Matplotlib is used as the plotting library.

This plugin is part of the Water Observation Information System (WOIS) developed under the TIGER-NET project funded by the European Space Agency as part of the long-term TIGER initiative aiming at promoting the use of Earth Observation (EO) for improved Integrated Water Resources Management (IWRM) in Africa.

Copyright (C) 2014 TIGER-NET (www.tiger-net.org)

Based on Profile tool plugin:
  Copyright (C) 2008 Borys Jurgiel,
  Copyright (C) 2012 Patrice Verchere
