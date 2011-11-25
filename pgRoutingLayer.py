"""
/***************************************************************************
 pgRouting Layer
                                 a QGIS plugin
                                 
 based on "Fast SQL Layer" plugin. Copyright 2011 Pablo Torres Carreira 
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
"""
# Import the PyQt and QGIS libraries
from PyQt4 import uic
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
import dbConnection
#import highlighter as hl
import os
#import resources

# Initialize Qt resources from file resources.py

conn = dbConnection.ConnectionManager()

class PgRoutingLayer:
    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
    def initGui(self):
        # Create action that will start plugin configuration
        self.action = QAction(QIcon(":/plugins/pgRoutingLayer/icon.png"), "pgRouting Layer", self.iface.mainWindow())
        #Add toolbar button and menu item
        self.iface.addPluginToDatabaseMenu("&pgRouting Layer", self.action)
        #self.iface.addToolBarIcon(self.action)
        
        
        #load the form  
        path = os.path.dirname(os.path.abspath(__file__))
        self.dock = uic.loadUi(os.path.join(path, "ui_pgRoutingLayer.ui"))
        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dock)        
        
        
        #connect the action to the run method
        QObject.connect(self.action, SIGNAL("triggered()"), self.show)
        QObject.connect(self.dock.buttonRun, SIGNAL('clicked()'), self.run)
        
        #populate the combo with connections
        actions = conn.getAvailableConnections()
        self.actionsDb = {}
        for a in actions:
        	self.actionsDb[ unicode(a.text()) ] = a
        for i in self.actionsDb:
        	self.dock.comboConnections.addItem(i)
            
        self.dock.lineEditRoadId.setText('gid')
        self.dock.lineEditTable.setText('network')
        self.dock.lineEditGeometry.setText('the_geom')
        self.dock.lineEditCost.setText('shape_leng')
        self.dock.lineEditFromNode.setText('start_id')
        self.dock.lineEditToNode.setText('end_id')
        
        self.dock.lineEditFromNodeId.setText('100')
        self.dock.lineEditToNodeId.setText('500')     
        
    def show(self):
        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dock)
    
    def unload(self):
        # Remove the plugin menu item and icon
        self.iface.removePluginDatabaseMenu("&pgRouting Layer", self.action)
        

    
    def run(self):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        
      	dados = str(self.dock.comboConnections.currentText())
      	self.db = self.actionsDb[dados].connect()
        
        tableName = self.dock.lineEditTable.text()
        uniqueFieldName = self.dock.lineEditRoadId.text() #uniqueCombo.currentText()
        geomFieldName = self.dock.lineEditGeometry.text()
        fromNodeName = self.dock.lineEditFromNode.text()
        toNodeName = self.dock.lineEditToNode.text()
        costName = self.dock.lineEditCost.text()
        
        fromNode = self.dock.lineEditFromNodeId.text()
        toNode = self.dock.lineEditToNodeId.text()
        
        uri = self.db.getURI()
        
        query = "SELECT * FROM "
        query += tableName
        query += " JOIN (SELECT * FROM shortest_path('SELECT "
        query += uniqueFieldName 
        query += " AS id, "
        query += fromNodeName
        query += "::int4 AS source, "
        query += toNodeName
        query += "::int4 AS target, "
        query += costName
        query += "::float8 AS cost FROM "
        query += tableName
        query += " ', "
        query += fromNode
        query += ","
        query += toNode
        query += ", false, false)) AS route ON "
        query += tableName
        query += "."
        query += uniqueFieldName
        query += "= route.edge_id"
        
        #str(self.dock.textQuery.toPlainText())
        	
        layerName = "from "+fromNode+" to "+toNode
        
        uri.setDataSource("", "(" + query + ")", geomFieldName, "", uniqueFieldName)
        vl = self.iface.addVectorLayer(uri.uri(), layerName, self.db.getProviderName())
		
        QApplication.restoreOverrideCursor()
    
    