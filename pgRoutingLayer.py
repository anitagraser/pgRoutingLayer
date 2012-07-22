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
from qgis.gui import *
import dbConnection
#import highlighter as hl
import os
import psycopg2
import re

conn = dbConnection.ConnectionManager()

class PgRoutingLayer:

    SUPPORTED_FUNCTIONS = [
        'shortest_path',
        'shortest_path_astar',
        'shortest_path_shooting_star',
        'driving_distance',
        'alphashape',
        'tsp'
    ]
    TOGGLE_CONTROL_NAMES = [
        'lineEditId', 'lineEditSource', 'lineEditTarget',
        'lineEditCost', 'lineEditReverseCost',
        'lineEditX1', 'lineEditY1', 'lineEditX2', 'lineEditY2',
        'lineEditRule', 'lineEditToCost',
        'lineEditIds', 'buttonSelectIds',
        'lineEditSourceId', 'buttonSelectSourceId',
        'lineEditTargetId', 'buttonSelectTargetId',
        'lineEditDistance',
        'checkBoxDirected', 'checkBoxHasReverseCost',
        'buttonExport'
    ]
    FIND_RADIUS = 10
    
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
        
        self.idsEmitPoint = QgsMapToolEmitPoint(self.iface.mapCanvas())
        #self.idsEmitPoint.setButton(buttonSelectIds)
        self.sourceIdEmitPoint = QgsMapToolEmitPoint(self.iface.mapCanvas())
        #self.sourceIdEmitPoint.setButton(buttonSelectSourceId)
        self.targetIdEmitPoint = QgsMapToolEmitPoint(self.iface.mapCanvas())
        #self.targetIdEmitPoint.setButton(buttonSelectTargetId)
        
        #connect the action to each method
        QObject.connect(self.action, SIGNAL("triggered()"), self.show)
        QObject.connect(self.dock.comboBoxFunction, SIGNAL("currentIndexChanged(const QString&)"), self.updateFunctionEnabled)
        QObject.connect(self.dock.buttonSelectIds, SIGNAL("clicked(bool)"), self.selectIds)
        QObject.connect(self.idsEmitPoint, SIGNAL("canvasClicked(const QgsPoint&, Qt::MouseButton)"), self.setIds)
        QObject.connect(self.dock.buttonSelectSourceId, SIGNAL("clicked(bool)"), self.selectSourceId)
        QObject.connect(self.sourceIdEmitPoint, SIGNAL("canvasClicked(const QgsPoint&, Qt::MouseButton)"), self.setSourceId)
        QObject.connect(self.dock.buttonSelectTargetId, SIGNAL("clicked(bool)"), self.selectTargetId)
        QObject.connect(self.targetIdEmitPoint, SIGNAL("canvasClicked(const QgsPoint&, Qt::MouseButton)"), self.setTargetId)
        QObject.connect(self.dock.checkBoxHasReverseCost, SIGNAL("stateChanged(int)"), self.updateReverseCostEnabled)
        QObject.connect(self.dock.buttonRun, SIGNAL("clicked()"), self.run)
        QObject.connect(self.dock.buttonExport, SIGNAL("clicked()"), self.export)
        QObject.connect(self.dock.buttonClear, SIGNAL("clicked()"), self.clear)
        
        #populate the combo with connections
        actions = conn.getAvailableConnections()
        self.actionsDb = {}
        for a in actions:
            self.actionsDb[ unicode(a.text()) ] = a
        for i in self.actionsDb:
            self.dock.comboConnections.addItem(i)
        
        self.functions = {}
        for funcname in self.SUPPORTED_FUNCTIONS:
            # import the function
            exec("from functions import %s as function" % funcname)
            self.functions[funcname] = function.Function(self.dock)
            self.dock.comboBoxFunction.addItem(funcname)
        
        #self.dock.lineEditTable.setText('at_2po_4pgr')
        #self.dock.lineEditGeometry.setText('geom_way')
        self.dock.lineEditTable.setText('roads')
        self.dock.lineEditGeometry.setText('the_geom')
        
        self.dock.lineEditId.setText('id')
        self.dock.lineEditSource.setText('source')
        self.dock.lineEditTarget.setText('target')
        self.dock.lineEditCost.setText('cost')
        self.dock.lineEditReverseCost.setText('reverse_cost')
        self.dock.lineEditX1.setText('x1')
        self.dock.lineEditY1.setText('y1')
        self.dock.lineEditX2.setText('x2')
        self.dock.lineEditY2.setText('y2')
        self.dock.lineEditRule.setText('rule')
        self.dock.lineEditToCost.setText('to_cost')
        
        #self.dock.lineEditSourceId.setText('191266')
        #self.dock.lineEditTargetId.setText('190866')
        
        self.dock.lineEditIds.setValidator(QRegExpValidator(QRegExp("[0-9,]+"), self.dock))
        self.dock.lineEditSourceId.setValidator(QIntValidator())
        self.dock.lineEditTargetId.setValidator(QIntValidator())
        
        self.idsVertexMarkers = []
        self.sourceIdVertexMarker = QgsVertexMarker(self.iface.mapCanvas())
        self.sourceIdVertexMarker.setColor(Qt.blue)
        self.sourceIdVertexMarker.setPenWidth(2)
        self.sourceIdVertexMarker.setVisible(False)
        self.targetIdVertexMarker = QgsVertexMarker(self.iface.mapCanvas())
        self.targetIdVertexMarker.setColor(Qt.green)
        self.targetIdVertexMarker.setPenWidth(2)
        self.targetIdVertexMarker.setVisible(False)
        self.sourceIdRubberBand = QgsRubberBand(self.iface.mapCanvas(), False)
        self.sourceIdRubberBand.setColor(Qt.cyan)
        self.sourceIdRubberBand.setWidth(4)
        self.targetIdRubberBand = QgsRubberBand(self.iface.mapCanvas(), False)
        self.targetIdRubberBand.setColor(Qt.yellow)
        self.targetIdRubberBand.setWidth(4)
        
        self.canvasItemList = {}
        self.canvasItemList['markers'] = []
        self.canvasItemList['annotations'] = []
        resultPathRubberBand = QgsRubberBand(self.iface.mapCanvas(), False)
        resultPathRubberBand.setColor(Qt.red)
        resultPathRubberBand.setWidth(2)
        self.canvasItemList['path'] = resultPathRubberBand
        resultAreaRubberBand = QgsRubberBand(self.iface.mapCanvas(), True)
        resultAreaRubberBand.setColor(Qt.magenta)
        resultAreaRubberBand.setWidth(2)
        self.canvasItemList['area'] = resultAreaRubberBand
        
        self.dock.comboBoxFunction.setCurrentIndex(0)
        
    def show(self):
        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dock)
        
    def unload(self):
        # Remove the plugin menu item and icon
        self.iface.removePluginDatabaseMenu("&pgRouting Layer", self.action)
        self.iface.removeDockWidget(self.dock)
        
    def updateFunctionEnabled(self, text):
        function = self.functions[str(text)]
        
        self.toggleSelectButton(None)
        
        for controlName in self.TOGGLE_CONTROL_NAMES:
            control = getattr(self.dock, controlName)
            control.setEnabled(False)
        
        for controlName in function.getControlNames():
            control = getattr(self.dock, controlName)
            control.setEnabled(True)
        
        if (not self.dock.checkBoxHasReverseCost.isChecked()) or (not self.dock.checkBoxHasReverseCost.isEnabled()):
            self.dock.lineEditReverseCost.setEnabled(False)
        
        # currently edge base function is "shortest_path_shooting_star" only
        if function.isEdgeBase():
            self.clear()
            
    def selectIds(self, checked):
        if checked:
            self.toggleSelectButton(self.dock.buttonSelectIds)
            self.dock.lineEditIds.setText("")
            if len(self.idsVertexMarkers) > 0:
                for marker in self.idsVertexMarkers:
                    marker.setVisible(False)
                self.idsVertexMarkers = []
            self.iface.mapCanvas().setMapTool(self.idsEmitPoint)
        else:
            self.iface.mapCanvas().unsetMapTool(self.idsEmitPoint)
        
    def setIds(self, pt):
        args = self.getBaseArguments()
        result, id, wkt = self.findNearestNode(args, pt)
        if result:
            ids = self.dock.lineEditIds.text()
            if not ids:
                self.dock.lineEditIds.setText(str(id))
            else:
                self.dock.lineEditIds.setText(ids + "," + str(id))
            geom = QgsGeometry().fromWkt(wkt)
            vertexMarker = QgsVertexMarker(self.iface.mapCanvas())
            vertexMarker.setColor(Qt.green)
            vertexMarker.setPenWidth(2)
            vertexMarker.setCenter(geom.asPoint())
            self.idsVertexMarkers.append(vertexMarker)
            self.iface.mapCanvas().clear() # TODO:
        
    def selectSourceId(self, checked):
        if checked:
            self.toggleSelectButton(self.dock.buttonSelectSourceId)
            self.dock.lineEditSourceId.setText("")
            self.sourceIdVertexMarker.setVisible(False)
            self.sourceIdRubberBand.reset(False)
            self.iface.mapCanvas().setMapTool(self.sourceIdEmitPoint)
        else:
            self.iface.mapCanvas().unsetMapTool(self.sourceIdEmitPoint)
        
    def setSourceId(self, pt):
        function = self.functions[str(self.dock.comboBoxFunction.currentText())]
        args = self.getBaseArguments()
        if not function.isEdgeBase():
            result, id, wkt = self.findNearestNode(args, pt)
            if result:
                self.dock.lineEditSourceId.setText(str(id))
                geom = QgsGeometry().fromWkt(wkt)
                self.sourceIdVertexMarker.setCenter(geom.asPoint())
                self.sourceIdVertexMarker.setVisible(True)
                self.dock.buttonSelectSourceId.click()
        else:
            result, id, wkt = self.findNearestLink(args, pt)
            if result:
                self.dock.lineEditSourceId.setText(str(id))
                geom = QgsGeometry().fromWkt(wkt)
                if geom.wkbType() == QGis.WKBMultiLineString:
                    for line in geom.asMultiPolyline():
                        for pt in line:
                            self.sourceIdRubberBand.addPoint(pt)
                elif geom.wkbType() == QGis.WKBLineString:
                    for pt in geom.asPolyline():
                        self.sourceIdRubberBand.addPoint(pt)
                self.dock.buttonSelectSourceId.click()
        self.iface.mapCanvas().clear() # TODO:
        
    def selectTargetId(self, checked):
        if checked:
            self.toggleSelectButton(self.dock.buttonSelectTargetId)
            self.dock.lineEditTargetId.setText("")
            self.targetIdVertexMarker.setVisible(False)
            self.targetIdRubberBand.reset(False)
            self.iface.mapCanvas().setMapTool(self.targetIdEmitPoint)
        else:
            self.iface.mapCanvas().unsetMapTool(self.targetIdEmitPoint)
        
    def setTargetId(self, pt):
        function = self.functions[str(self.dock.comboBoxFunction.currentText())]
        args = self.getBaseArguments()
        if not function.isEdgeBase():
            result, id, wkt = self.findNearestNode(args, pt)
            if result:
                self.dock.lineEditTargetId.setText(str(id))
                geom = QgsGeometry().fromWkt(wkt)
                self.targetIdVertexMarker.setCenter(geom.asPoint())
                self.targetIdVertexMarker.setVisible(True)
                self.dock.buttonSelectTargetId.click()
        else:
            result, id, wkt = self.findNearestLink(args, pt)
            if result:
                self.dock.lineEditTargetId.setText(str(id))
                geom = QgsGeometry().fromWkt(wkt)
                if geom.wkbType() == QGis.WKBMultiLineString:
                    for line in geom.asMultiPolyline():
                        for pt in line:
                            self.targetIdRubberBand.addPoint(pt)
                elif geom.wkbType() == QGis.WKBLineString:
                    for pt in geom.asPolyline():
                        self.targetIdRubberBand.addPoint(pt)
                self.dock.buttonSelectTargetId.click()
        self.iface.mapCanvas().clear() # TODO:
        
    def updateReverseCostEnabled(self, state):
        if state == Qt.Checked:
            self.dock.lineEditReverseCost.setEnabled(True)
        else:
            self.dock.lineEditReverseCost.setEnabled(False)
        
    def run(self):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        
        function = self.functions[str(self.dock.comboBoxFunction.currentText())]
        args = self.getArguments(function.getControlNames())
        
        empties = []
        for key in args.keys():
            if not args[key]:
                empties.append(key)
        
        if len(empties) > 0:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self.dock, self.dock.windowTitle(),
                'Following argument is not specified.\n' + ','.join(empties))
            return
        
        try:
            dados = str(self.dock.comboConnections.currentText())
            db = self.actionsDb[dados].connect()
            
            con = db.con
            
            srid, geomType = self.getSridAndGeomType(con, args)
            function.prepare(con, args, geomType, self.canvasItemList)
            
            query = function.getQuery(args)
            ##QMessageBox.information(self.dock, self.dock.windowTitle(), query)
            
            cur = con.cursor()
            cur.execute(query)
            rows = cur.fetchall()
            
            function.draw(rows, con, args, geomType, self.canvasItemList, self.iface.mapCanvas())
            
        except psycopg2.DatabaseError, e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self.dock, self.dock.windowTitle(), '%s' % e)
            
        except SystemError, e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self.dock, self.dock.windowTitle(), '%s' % e)
            
        except AssertionError, e:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self.dock, self.dock.windowTitle(), '%s' % e)
            
        finally:
            QApplication.restoreOverrideCursor()
            if db and db.con:
                try:
                    db.con.close()
                except:
                    QMessageBox.critical(self.dock, self.dock.windowTitle(),
                        'server closed the connection unexpectedly')
        
    def export(self):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        
        function = self.functions[str(self.dock.comboBoxFunction.currentText())]
        args = self.getArguments(function.getControlNames())
        
        empties = []
        for key in args.keys():
            if not args[key]:
                empties.append(key)
        
        if len(empties) > 0:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self.dock, self.dock.windowTitle(),
                'Following argument is not specified.\n' + ','.join(empties))
            return
        
        args['path_query'] = function.getQuery(args)
        
        query = """
            SELECT %(edge_table)s.*,
                route.cost AS route_cost,
                route.vertex_id AS route_vertex_id
                FROM %(edge_table)s
                JOIN
                (%(path_query)s) AS route
                ON %(edge_table)s.%(id)s = route.edge_id""" % args
        
        query = query.replace('\n', ' ')
        query = re.sub(r'\s+', ' ', query)
        query = query.strip()
        ##QMessageBox.information(self.dock, self.dock.windowTitle(), query)
        
        try:
            dados = str(self.dock.comboConnections.currentText())
            db = self.actionsDb[dados].connect()
            
            uri = db.getURI()
            uri.setDataSource("", "(" + query + ")", args['geometry'], "", args['id'])
            
            # add vector layer to map
            layerName = "from "+args['source_id']+" to "+args['target_id']
            vl = self.iface.addVectorLayer(uri.uri(), layerName, db.getProviderName())
            
        except psycopg2.DatabaseError, e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self.dock, self.dock.windowTitle(), '%s' % e)
            
        except SystemError, e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self.dock, self.dock.windowTitle(), '%s' % e)
            
        finally:
            QApplication.restoreOverrideCursor()
            if db and db.con:
                try:
                    db.con.close()
                except:
                    QMessageBox.critical(self.dock, self.dock.windowTitle(),
                        'server closed the connection unexpectedly')
        
    def clear(self):
        self.dock.lineEditIds.setText("")
        for marker in self.idsVertexMarkers:
            marker.setVisible(False)
        self.idsVertexMarkers = []
        self.dock.lineEditSourceId.setText("")
        self.sourceIdVertexMarker.setVisible(False)
        self.dock.lineEditTargetId.setText("")
        self.targetIdVertexMarker.setVisible(False)
        self.sourceIdRubberBand.reset(False)
        self.targetIdRubberBand.reset(False)
        for marker in self.canvasItemList['markers']:
            marker.setVisible(False)
        self.canvasItemList['markers'] = []
        for anno in self.canvasItemList['annotations']:
            anno.setVisible(False)
        self.canvasItemList['annotations'] = []
        self.canvasItemList['path'].reset(False)
        self.canvasItemList['area'].reset(True)
        
    def toggleSelectButton(self, button):
        selectButtons = [
            self.dock.buttonSelectIds,
            self.dock.buttonSelectSourceId,
            self.dock.buttonSelectTargetId
        ]
        for selectButton in selectButtons:
            if selectButton != button:
                if selectButton.isChecked():
                    selectButton.click()
        
    def getArguments(self, controls):
        args = {}
        args['edge_table'] = self.dock.lineEditTable.text()
        args['geometry'] = self.dock.lineEditGeometry.text()
        if 'lineEditId' in controls:
            args['id'] = self.dock.lineEditId.text()
        if 'lineEditSource' in controls:
            args['source'] = self.dock.lineEditSource.text()
        
        if 'lineEditTarget' in controls:
            args['target'] = self.dock.lineEditTarget.text()
        
        if 'lineEditCost' in controls:
            args['cost'] = self.dock.lineEditCost.text()
        
        if 'lineEditReverseCost' in controls:
            args['reverse_cost'] = self.dock.lineEditReverseCost.text()
        
        if 'lineEditX1' in controls:
            args['x1'] = self.dock.lineEditX1.text()
        
        if 'lineEditY1' in controls:
            args['y1'] = self.dock.lineEditY1.text()
        
        if 'lineEditX2' in controls:
            args['x2'] = self.dock.lineEditX2.text()
        
        if 'lineEditY2' in controls:
            args['y2'] = self.dock.lineEditY2.text()
        
        if 'lineEditRule' in controls:
            args['rule'] = self.dock.lineEditRule.text()
        
        if 'lineEditToCost' in controls:
            args['to_cost'] = self.dock.lineEditToCost.text()
        
        if 'lineEditSourceId' in controls:
            args['source_id'] = self.dock.lineEditSourceId.text()
        
        if 'lineEditTargetId' in controls:
            args['target_id'] = self.dock.lineEditTargetId.text()
        
        if 'lineEditIds' in controls:
            args['ids'] = self.dock.lineEditIds.text()
        
        if 'lineEditDistance' in controls:
            args['distance'] = self.dock.lineEditDistance.text()
        
        if 'checkBoxDirected' in controls:
            args['directed'] = str(self.dock.checkBoxDirected.isChecked()).lower()
        
        if 'checkBoxHasReverseCost' in controls:
            args['has_reverse_cost'] = str(self.dock.checkBoxHasReverseCost.isChecked()).lower()
            if args['has_reverse_cost'] == 'false':
                args['reverse_cost'] = ' '
            else:
                args['reverse_cost'] = ', ' + args['reverse_cost'] + '::float8 AS reverse_cost'
        
        return args
        
    def getBaseArguments(self):
        args = {}
        args['edge_table'] = self.dock.lineEditTable.text()
        args['geometry'] = self.dock.lineEditGeometry.text()
        args['id'] = self.dock.lineEditId.text()
        args['source'] = self.dock.lineEditSource.text()
        args['target'] = self.dock.lineEditTarget.text()
        
        empties = []
        for key in args.keys():
            if not args[key]:
                empties.append(key)
        
        if len(empties) > 0:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self.dock, self.dock.windowTitle(),
                'Following argument is not specified.\n' + ','.join(empties))
            return None
        
        return args
        
    def getSridAndGeomType(self, con, args):
        cur = con.cursor()
        cur.execute("""
            SELECT ST_SRID(%(geometry)s), ST_GeometryType(%(geometry)s)
                FROM %(edge_table)s
                WHERE %(id)s = (SELECT MIN(%(id)s) FROM %(edge_table)s)""" % args)
        row = cur.fetchone()
        srid = row[0]
        geomType = row[1]
        return srid, geomType
        
    # emulate "matching.sql" - "find_nearest_node_within_distance"
    def findNearestNode(self, args, pt):
        distance = self.iface.mapCanvas().getCoordinateTransform().mapUnitsPerPixel() * self.FIND_RADIUS
        try:
            dados = str(self.dock.comboConnections.currentText())
            db = self.actionsDb[dados].connect()
            
            con = db.con
            srid, geomType = self.getSridAndGeomType(con, args)
            args['srid'] = srid
            args['x'] = pt.x()
            args['y'] = pt.y()
            args['minx'] = pt.x() - distance
            args['miny'] = pt.y() - distance
            args['maxx'] = pt.x() + distance
            args['maxy'] = pt.y() + distance
            
            if geomType == 'ST_MultiLineString':
                args['startpoint'] = "ST_StartPoint(ST_GeometryN(%(geometry)s, 1))" % args
                args['endpoint'] = "ST_EndPoint(ST_GeometryN(%(geometry)s, 1))" % args
            elif geomType == 'ST_LineString':
                args['startpoint'] = "ST_StartPoint(%(geometry)s)" % args
                args['endpoint'] = "ST_EndPoint(%(geometry)s)" % args
            
            # Getting nearest source
            query1 = """
            SELECT %(source)s,
                ST_Distance(
                    %(startpoint)s,
                    ST_GeomFromText('POINT(%(x)f %(y)f)', %(srid)d)
                ) AS dist,
                ST_AsText(%(startpoint)s)
                FROM %(edge_table)s
                WHERE ST_SetSRID('BOX3D(%(minx)f %(miny)f, %(maxx)f %(maxy)f)'::BOX3D, %(srid)d)
                    && %(geometry)s ORDER BY dist ASC LIMIT 1""" % args
            
            ##QMessageBox.information(self.dock, self.dock.windowTitle(), query1)
            cur1 = con.cursor()
            cur1.execute(query1)
            row1 = cur1.fetchone()
            d1 = None
            source = None
            wkt1 = None
            if row1:
                d1 = row1[1]
                source = row1[0]
                wkt1 = row1[2]
            
            # Getting nearest target
            query2 = """
            SELECT %(target)s,
                ST_Distance(
                    %(endpoint)s,
                    ST_GeomFromText('POINT(%(x)f %(y)f)', %(srid)d)
                ) AS dist,
                ST_AsText(%(endpoint)s)
                FROM %(edge_table)s
                WHERE ST_SetSRID('BOX3D(%(minx)f %(miny)f, %(maxx)f %(maxy)f)'::BOX3D, %(srid)d)
                    && %(geometry)s ORDER BY dist ASC LIMIT 1""" % args
            
            ##QMessageBox.information(self.dock, self.dock.windowTitle(), query2)
            cur2 = con.cursor()
            cur2.execute(query2)
            row2 = cur2.fetchone()
            d2 = None
            target = None
            wkt2 = None
            if row2:
                d2 = row2[1]
                target = row2[0]
                wkt2 = row2[2]
            
            # Checking what is nearer - source or target
            d = None
            node = None
            wkt = None
            if d1 and (not d2):
                node = source
                d = d1
                wkt = wkt1
            elif (not d1) and d2:
                node = target
                d = d2
                wkt = wkt2
            elif d1 and d2:
                if d1 < d2:
                    node = source
                    d = d1
                    wkt = wkt1
                else:
                    node = target
                    d = d2
                    wkt = wkt2
            
            ##QMessageBox.information(self.dock, self.dock.windowTitle(), str(d))
            if (d == None) or (d > distance):
                node = None
                wkt = None
                return False, None, None
            
            return True, node, wkt
            
        except psycopg2.DatabaseError, e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self.dock, self.dock.windowTitle(), '%s' % e)
            return False, None, None
            
        finally:
            if db and db.con:
                db.con.close()
        
    # emulate "matching.sql" - "find_nearest_link_within_distance"
    def findNearestLink(self, args, pt):
        distance = self.iface.mapCanvas().getCoordinateTransform().mapUnitsPerPixel() * self.FIND_RADIUS
        try:
            dados = str(self.dock.comboConnections.currentText())
            db = self.actionsDb[dados].connect()
            
            con = db.con
            cur = con.cursor()
            cur.execute("""
                SELECT ST_SRID(%(geometry)s)
                    FROM %(edge_table)s
                    WHERE %(id)s = (SELECT MIN(%(id)s) FROM %(edge_table)s)""" % args)
            row = cur.fetchone()
            args['srid'] = row[0]
            args['x'] = pt.x()
            args['y'] = pt.y()
            args['minx'] = pt.x() - distance
            args['miny'] = pt.y() - distance
            args['maxx'] = pt.x() + distance
            args['maxy'] = pt.y() + distance
            
            # Searching for a link within the distance
            query = """
            SELECT %(id)s,
                ST_Distance(
                    %(geometry)s,
                    ST_GeomFromText('POINT(%(x)f %(y)f)', %(srid)d)
                ) AS dist,
                ST_AsText(%(geometry)s)
                FROM %(edge_table)s
                WHERE ST_SetSRID('BOX3D(%(minx)f %(miny)f, %(maxx)f %(maxy)f)'::BOX3D, %(srid)d)
                    && %(geometry)s ORDER BY dist ASC LIMIT 1""" % args
            
            ##QMessageBox.information(self.dock, self.dock.windowTitle(), query1)
            cur = con.cursor()
            cur.execute(query)
            row = cur.fetchone()
            if not row:
                return False, None, None
            link = row[0]
            wkt = row[2]
            
            return True, link, wkt
            
        except psycopg2.DatabaseError, e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self.dock, self.dock.windowTitle(), '%s' % e)
            return False, None, None
            
        finally:
            if db and db.con:
                db.con.close()
