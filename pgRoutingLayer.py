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
            
        self.dock.lineEditEdgeId.setText('gid')
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
        self.iface.removeDockWidget(self.dock)
        
    def run(self):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        
      	dados = str(self.dock.comboConnections.currentText())
      	self.db = self.actionsDb[dados].connect()
        
        routingMethod = self.dock.comboBoxRoutingMethod.currentText()
        (uri,layerName) = self.getUri(routingMethod)
        
        vl = self.iface.addVectorLayer(uri.uri(), layerName, self.db.getProviderName())
		
        QApplication.restoreOverrideCursor()
    
    def getUri(self,routingMethod):
        query=""


        tableName = self.dock.lineEditTable.text()
        uniqueFieldName = self.dock.lineEditEdgeId.text() #uniqueCombo.currentText()
        fromNodeName = self.dock.lineEditFromNode.text()
        toNodeName = self.dock.lineEditToNode.text()
        costName = self.dock.lineEditCost.text()
        isDirected = self.dock.checkBoxDirected.isChecked()
        hasReverseCost = self.dock.checkBoxReverse.isChecked()
        reverseCost = self.dock.lineEditReverseCost.text()
        fromNode = self.dock.lineEditFromNodeId.text()
        toNode = self.dock.lineEditToNodeId.text()
        geomFieldName = self.dock.lineEditGeometry.text()


        if routingMethod == "Shortest Path Dijkstra":
        
            """The shortest_path function has the following declaration:
            CREATE OR REPLACE FUNCTION shortest_path(
                sql text,
                source_id integer,
                target_id integer,
                directed boolean,
                has_reverse_cost boolean)
            RETURNS SETOF path_result
            
            Arguments:
    
            sql: a SQL query, which should return a set of rows with the following columns:
            SELECT id, source, target, cost FROM edge_table
            id: an int4 identifier of the edge
            source: an int4 identifier of the source vertex
            target: an int4 identifier of the target vertex
            cost: an float8 value, of the edge traversal cost. (a negative cost will prevent the edge from being inserted in the graph).
            reverse_cost (optional): the cost for the reverse traversal of the edge. This is only used when the directed and has_reverse_cost parameters are true (see the above remark about negative costs).
            
            source_id: int4 id of the start point
            
            directed: true if the graph is directed
            
            has_reverse_cost: if true, the reverse_cost column of the SQL generated set of rows will be used for the cost of the traversal of the edge in the opposite direction.
            """
    
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
            query += "::float8 AS cost "
            
            if hasReverseCost and reverseCost:
                query += ","
                query += reverseCost
                query += "::float8 AS reverse_cost "
                
            query += " FROM "
            query += tableName
            query += " ', "
            query += fromNode
            query += ","
            query += toNode
            query += ", "
            query += str(isDirected)
            query += ", "
            query += str(hasReverseCost)
            query += ")) AS route ON "
            query += tableName
            query += "."
            query += uniqueFieldName
            query += "= route.edge_id"


        layerName = "from "+fromNode+" to "+toNode
        
        uri = self.db.getURI()
        uri.setDataSource("", "(" + query + ")", geomFieldName, "", uniqueFieldName)
 
        return (uri,layerName)