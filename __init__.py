"""
/***************************************************************************
 pgRouting Layer
                                 a QGIS plugin
                                 
 based on "Fast SQL Layer" plugin Copyright 2011 Pablo Torres Carreira 
                             -------------------
        begin                : 2011-11-25
        copyright            : (c) 2011 by Anita Graser
        email                : anita.graser.at@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""

def name():
    return "pgRouting Layer"
def description():
    return "Dockable widget that adds pgRouting layers"
def version():
    return "Version 0.1"
def icon():
    return "icon.png"
def qgisMinimumVersion():
    return "1.7"
def classFactory(iface):
    from pgRoutingLayer import PgRoutingLayer
    return PgRoutingLayer(iface)
