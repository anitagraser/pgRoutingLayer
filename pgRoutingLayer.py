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
import pgRoutingLayer_utils as Utils
#import highlighter as hl
import os
import psycopg2
import re

conn = dbConnection.ConnectionManager()

class PgRoutingLayer:

    SUPPORTED_FUNCTIONS = [
        'dijkstra',
        'astar',
        #'shootingStar',
        'drivingDistance',
        'alphashape',
        'tsp_euclid',
        'trsp_vertex',
        'trsp_edge',
        'kdijkstra_cost',
        'kdijkstra_path',
        'bdDijkstra',
        'bdAstar',
        'ksp'
    ]
    TOGGLE_CONTROL_NAMES = [
        'labelId', 'lineEditId',
        'labelSource', 'lineEditSource',
        'labelTarget', 'lineEditTarget',
        'labelCost', 'lineEditCost',
        'labelReverseCost', 'lineEditReverseCost',
        'labelX1', 'lineEditX1',
        'labelY1', 'lineEditY1',
        'labelX2', 'lineEditX2',
        'labelY2', 'lineEditY2',
        'labelRule', 'lineEditRule',
        'labelToCost', 'lineEditToCost',
        'labelIds', 'lineEditIds', 'buttonSelectIds',
        'labelSourceId', 'lineEditSourceId', 'buttonSelectSourceId',
        'labelSourcePos', 'lineEditSourcePos',
        'labelTargetId', 'lineEditTargetId', 'buttonSelectTargetId',
        'labelTargetIds', 'lineEditTargetIds', 'buttonSelectTargetIds',
        'labelTargetPos', 'lineEditTargetPos',
        'labelDistance', 'lineEditDistance',
        'labelPaths', 'lineEditPaths',
        'checkBoxDirected', 'checkBoxHasReverseCost',
        'labelTurnRestrictSql', 'plainTextEditTurnRestrictSql',
    ]
    FIND_RADIUS = 10
    
    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        
        self.idsVertexMarkers = []
        self.targetIdsVertexMarkers = []
        self.sourceIdVertexMarker = QgsVertexMarker(self.iface.mapCanvas())
        self.sourceIdVertexMarker.setColor(Qt.blue)
        self.sourceIdVertexMarker.setPenWidth(2)
        self.sourceIdVertexMarker.setVisible(False)
        self.targetIdVertexMarker = QgsVertexMarker(self.iface.mapCanvas())
        self.targetIdVertexMarker.setColor(Qt.green)
        self.targetIdVertexMarker.setPenWidth(2)
        self.targetIdVertexMarker.setVisible(False)
        self.sourceIdRubberBand = QgsRubberBand(self.iface.mapCanvas(), Utils.getRubberBandType(False))
        self.sourceIdRubberBand.setColor(Qt.cyan)
        self.sourceIdRubberBand.setWidth(4)
        self.targetIdRubberBand = QgsRubberBand(self.iface.mapCanvas(), Utils.getRubberBandType(False))
        self.targetIdRubberBand.setColor(Qt.yellow)
        self.targetIdRubberBand.setWidth(4)
        
        self.canvasItemList = {}
        self.canvasItemList['markers'] = []
        self.canvasItemList['annotations'] = []
        self.canvasItemList['paths'] = []
        resultPathRubberBand = QgsRubberBand(self.iface.mapCanvas(), Utils.getRubberBandType(False))
        resultPathRubberBand.setColor(QColor(255, 0, 0, 128))
        resultPathRubberBand.setWidth(4)
        self.canvasItemList['path'] = resultPathRubberBand
        resultAreaRubberBand = QgsRubberBand(self.iface.mapCanvas(), Utils.getRubberBandType(True))
        resultAreaRubberBand.setColor(Qt.magenta)
        resultAreaRubberBand.setWidth(2)
        if not Utils.isQGISv1():
            resultAreaRubberBand.setBrushStyle(Qt.Dense4Pattern)
        self.canvasItemList['area'] = resultAreaRubberBand
        
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
        self.targetIdsEmitPoint = QgsMapToolEmitPoint(self.iface.mapCanvas())
        #self.targetIdsEmitPoint.setButton(buttonSelectTargetId)
        
        #connect the action to each method
        QObject.connect(self.action, SIGNAL("triggered()"), self.show)
        QObject.connect(self.dock.comboBoxFunction, SIGNAL("currentIndexChanged(const QString&)"), self.updateFunctionEnabled)
        QObject.connect(self.dock.buttonSelectIds, SIGNAL("clicked(bool)"), self.selectIds)
        QObject.connect(self.idsEmitPoint, SIGNAL("canvasClicked(const QgsPoint&, Qt::MouseButton)"), self.setIds)
        QObject.connect(self.dock.buttonSelectSourceId, SIGNAL("clicked(bool)"), self.selectSourceId)
        QObject.connect(self.sourceIdEmitPoint, SIGNAL("canvasClicked(const QgsPoint&, Qt::MouseButton)"), self.setSourceId)
        QObject.connect(self.dock.buttonSelectTargetId, SIGNAL("clicked(bool)"), self.selectTargetId)
        QObject.connect(self.targetIdEmitPoint, SIGNAL("canvasClicked(const QgsPoint&, Qt::MouseButton)"), self.setTargetId)
        QObject.connect(self.dock.buttonSelectTargetIds, SIGNAL("clicked(bool)"), self.selectTargetIds)
        QObject.connect(self.targetIdsEmitPoint, SIGNAL("canvasClicked(const QgsPoint&, Qt::MouseButton)"), self.setTargetIds)
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
        
        self.prevType = None
        self.functions = {}
        for funcfname in self.SUPPORTED_FUNCTIONS:
            # import the function
            exec("from functions import %s as function" % funcfname)
            funcname = function.Function.getName()
            self.functions[funcname] = function.Function(self.dock)
            self.dock.comboBoxFunction.addItem(funcname)
        
        self.dock.lineEditIds.setValidator(QRegExpValidator(QRegExp("[0-9,]+"), self.dock))
        self.dock.lineEditSourceId.setValidator(QIntValidator())
        self.dock.lineEditSourcePos.setValidator(QDoubleValidator(0.0, 1.0, 10, self.dock))
        self.dock.lineEditTargetId.setValidator(QIntValidator())
        self.dock.lineEditTargetPos.setValidator(QDoubleValidator(0.0, 1.0, 10, self.dock))
        self.dock.lineEditTargetIds.setValidator(QRegExpValidator(QRegExp("[0-9,]+"), self.dock))
        self.dock.lineEditDistance.setValidator(QDoubleValidator())
        self.dock.lineEditPaths.setValidator(QIntValidator())
        
        self.loadSettings()
        
    def show(self):
        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dock)
        
    def unload(self):
        self.saveSettings()
        # Remove the plugin menu item and icon
        self.iface.removePluginDatabaseMenu("&pgRouting Layer", self.action)
        self.iface.removeDockWidget(self.dock)
        
    def updateFunctionEnabled(self, text):
        function = self.functions[str(text)]
        
        self.toggleSelectButton(None)
        
        for controlName in self.TOGGLE_CONTROL_NAMES:
            control = getattr(self.dock, controlName)
            control.setVisible(False)
        
        for controlName in function.getControlNames():
            control = getattr(self.dock, controlName)
            control.setVisible(True)
        
        # adjust sql scroll area max height (TODO:initial display)
        contents = self.dock.scrollAreaWidgetContents
        margins = contents.layout().contentsMargins()
        ##QMessageBox.information(self.dock, self.dock.windowTitle(), '%s - height:%d' % (text, contents.sizeHint().height()))
        self.dock.scrollAreaColumns.setMaximumHeight(contents.sizeHint().height() + margins.top() + margins.bottom())
        
        if (not self.dock.checkBoxHasReverseCost.isChecked()) or (not self.dock.checkBoxHasReverseCost.isEnabled()):
            self.dock.lineEditReverseCost.setEnabled(False)
        
        # if type(edge/node) changed, clear input
        if (self.prevType != None) and (self.prevType != function.isEdgeBase()):
            self.clear()
            
        self.prevType = function.isEdgeBase()
        
        self.dock.buttonExport.setEnabled(function.canExport())
   
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
            self.sourceIdRubberBand.reset(Utils.getRubberBandType(False))
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
            self.targetIdRubberBand.reset(Utils.getRubberBandType(False))
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
        
    def selectTargetIds(self, checked):
        if checked:
            self.toggleSelectButton(self.dock.buttonSelectTargetIds)
            self.dock.lineEditTargetIds.setText("")
            if len(self.targetIdsVertexMarkers) > 0:
                for marker in self.targetIdsVertexMarkers:
                    marker.setVisible(False)
                self.targetIdsVertexMarkers = []
            self.iface.mapCanvas().setMapTool(self.targetIdsEmitPoint)
        else:
            self.iface.mapCanvas().unsetMapTool(self.targetIdsEmitPoint)
        
    def setTargetIds(self, pt):
        args = self.getBaseArguments()
        result, id, wkt = self.findNearestNode(args, pt)
        if result:
            ids = self.dock.lineEditTargetIds.text()
            if not ids:
                self.dock.lineEditTargetIds.setText(str(id))
            else:
                self.dock.lineEditTargetIds.setText(ids + "," + str(id))
            geom = QgsGeometry().fromWkt(wkt)
            vertexMarker = QgsVertexMarker(self.iface.mapCanvas())
            vertexMarker.setColor(Qt.green)
            vertexMarker.setPenWidth(2)
            vertexMarker.setCenter(geom.asPoint())
            self.targetIdsVertexMarkers.append(vertexMarker)
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
            
            args['srid'] = srid
            args['canvas_srid'] = Utils.getCanvasSrid(Utils.getDestinationCrs(self.iface.mapCanvas().mapRenderer()))
            Utils.setTransformQuotes(args)
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
                result.seq AS result_seq,
                result.node AS result_node,
                result.cost AS result_cost
                FROM %(edge_table)s
                JOIN
                (%(path_query)s) AS result
                ON %(edge_table)s.%(id)s = result.edge""" % args
        
        query = query.replace('\n', ' ')
        query = re.sub(r'\s+', ' ', query)
        query = query.replace('( ', '(')
        query = query.replace(' )', ')')
        query = query.strip()
        ##QMessageBox.information(self.dock, self.dock.windowTitle(), query)
        
        try:
            dados = str(self.dock.comboConnections.currentText())
            db = self.actionsDb[dados].connect()
            
            uri = db.getURI()
            uri.setDataSource("", "(" + query + ")", args['geometry'], "", "result_seq")
            
            # add vector layer to map
            layerName = function.getName() + " - from " + args['source_id'] + " to "
            if 'target_id' in args:
                layerName += args['target_id']
            else:
                layerName += "many"
            
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
        self.dock.lineEditTargetIds.setText("")
        for marker in self.targetIdsVertexMarkers:
            marker.setVisible(False)
        self.targetIdsVertexMarkers = []
        self.dock.lineEditSourceId.setText("")
        self.sourceIdVertexMarker.setVisible(False)
        self.dock.lineEditTargetId.setText("")
        self.targetIdVertexMarker.setVisible(False)
        self.sourceIdRubberBand.reset(Utils.getRubberBandType(False))
        self.targetIdRubberBand.reset(Utils.getRubberBandType(False))
        for marker in self.canvasItemList['markers']:
            marker.setVisible(False)
        self.canvasItemList['markers'] = []
        for anno in self.canvasItemList['annotations']:
            anno.setVisible(False)
        self.canvasItemList['annotations'] = []
        for path in self.canvasItemList['paths']:
            path.reset(Utils.getRubberBandType(False))
        self.canvasItemList['paths'] = []
        self.canvasItemList['path'].reset(Utils.getRubberBandType(False))
        self.canvasItemList['area'].reset(Utils.getRubberBandType(True))
        
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
        
        if 'lineEditIds' in controls:
            args['ids'] = self.dock.lineEditIds.text()
        
        if 'lineEditSourceId' in controls:
            args['source_id'] = self.dock.lineEditSourceId.text()
        
        if 'lineEditSourcePos' in controls:
            args['source_pos'] = self.dock.lineEditSourcePos.text()
        
        if 'lineEditTargetId' in controls:
            args['target_id'] = self.dock.lineEditTargetId.text()
        
        if 'lineEditTargetPos' in controls:
            args['target_pos'] = self.dock.lineEditTargetPos.text()
        
        if 'lineEditTargetIds' in controls:
            args['target_ids'] = self.dock.lineEditTargetIds.text()
        
        if 'lineEditDistance' in controls:
            args['distance'] = self.dock.lineEditDistance.text()
        
        if 'lineEditPaths' in controls:
            args['paths'] = self.dock.lineEditPaths.text()
        
        if 'checkBoxDirected' in controls:
            args['directed'] = str(self.dock.checkBoxDirected.isChecked()).lower()
        
        if 'checkBoxHasReverseCost' in controls:
            args['has_reverse_cost'] = str(self.dock.checkBoxHasReverseCost.isChecked()).lower()
            if args['has_reverse_cost'] == 'false':
                args['reverse_cost'] = ' '
            else:
                args['reverse_cost'] = ', ' + args['reverse_cost'] + '::float8 AS reverse_cost'
        
        if 'plainTextEditTurnRestrictSql' in controls:
            args['turn_restrict_sql'] = self.dock.plainTextEditTurnRestrictSql.toPlainText();
        
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
        rect = QgsRectangle(pt.x() - distance, pt.y() - distance, pt.x() + distance, pt.y() + distance)
        canvasCrs = Utils.getDestinationCrs(self.iface.mapCanvas().mapRenderer())
        db = None
        try:
            dados = str(self.dock.comboConnections.currentText())
            db = self.actionsDb[dados].connect()
            
            con = db.con
            srid, geomType = self.getSridAndGeomType(con, args)
            if self.iface.mapCanvas().hasCrsTransformEnabled():
                layerCrs = QgsCoordinateReferenceSystem()
                Utils.createFromSrid(layerCrs, srid)
                trans = QgsCoordinateTransform(canvasCrs, layerCrs)
                pt = trans.transform(pt)
                rect = trans.transform(rect)
            
            args['canvas_srid'] = Utils.getCanvasSrid(canvasCrs)
            args['srid'] = srid
            args['x'] = pt.x()
            args['y'] = pt.y()
            args['minx'] = rect.xMinimum()
            args['miny'] = rect.yMinimum()
            args['maxx'] = rect.xMaximum()
            args['maxy'] = rect.yMaximum()
            
            Utils.setStartPoint(geomType, args)
            Utils.setEndPoint(geomType, args)
            Utils.setTransformQuotes(args)
            
            # Getting nearest source
            query1 = """
            SELECT %(source)s,
                ST_Distance(
                    %(startpoint)s,
                    ST_GeomFromText('POINT(%(x)f %(y)f)', %(srid)d)
                ) AS dist,
                ST_AsText(%(transform_s)s%(startpoint)s%(transform_e)s)
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
                ST_AsText(%(transform_s)s%(endpoint)s%(transform_e)s)
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
        rect = QgsRectangle(pt.x() - distance, pt.y() - distance, pt.x() + distance, pt.y() + distance)
        canvasCrs = Utils.getDestinationCrs(self.iface.mapCanvas().mapRenderer())
        try:
            dados = str(self.dock.comboConnections.currentText())
            db = self.actionsDb[dados].connect()
            
            con = db.con
            cur = con.cursor()
            srid, geomType = self.getSridAndGeomType(con, args)
            if self.iface.mapCanvas().hasCrsTransformEnabled():
                layerCrs = QgsCoordinateReferenceSystem()
                Utils.createFromSrid(layerCrs, srid)
                trans = QgsCoordinateTransform(canvasCrs, layerCrs)
                pt = trans.transform(pt)
                rect = trans.transform(rect)
            
            args['canvas_srid'] = Utils.getCanvasSrid(canvasCrs)
            args['srid'] = srid
            args['x'] = pt.x()
            args['y'] = pt.y()
            args['minx'] = rect.xMinimum()
            args['miny'] = rect.yMinimum()
            args['maxx'] = rect.xMaximum()
            args['maxy'] = rect.yMaximum()
            
            Utils.setTransformQuotes(args)
            
            # Searching for a link within the distance
            query = """
            SELECT %(id)s,
                ST_Distance(
                    %(geometry)s,
                    ST_GeomFromText('POINT(%(x)f %(y)f)', %(srid)d)
                ) AS dist,
                ST_AsText(%(transform_s)s%(geometry)s%(transform_e)s)
                FROM %(edge_table)s
                WHERE ST_SetSRID('BOX3D(%(minx)f %(miny)f, %(maxx)f %(maxy)f)'::BOX3D, %(srid)d)
                    && %(geometry)s ORDER BY dist ASC LIMIT 1""" % args
            
            ##QMessageBox.information(self.dock, self.dock.windowTitle(), query)
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
    
    def loadSettings(self):
        settings = QSettings()
        idx = self.dock.comboConnections.findText(Utils.getStringValue(settings, '/pgRoutingLayer/Database', ''))
        if idx >= 0:
            self.dock.comboConnections.setCurrentIndex(idx)
        idx = self.dock.comboBoxFunction.findText(Utils.getStringValue(settings, '/pgRoutingLayer/Function', 'dijkstra'))
        if idx >= 0:
            self.dock.comboBoxFunction.setCurrentIndex(idx)
        
        self.dock.lineEditTable.setText(Utils.getStringValue(settings, '/pgRoutingLayer/sql/edge_table', 'roads'))
        self.dock.lineEditGeometry.setText(Utils.getStringValue(settings, '/pgRoutingLayer/sql/geometry', 'the_geom'))
        self.dock.lineEditId.setText(Utils.getStringValue(settings, '/pgRoutingLayer/sql/id', 'id'))
        self.dock.lineEditSource.setText(Utils.getStringValue(settings, '/pgRoutingLayer/sql/source', 'source'))
        self.dock.lineEditTarget.setText(Utils.getStringValue(settings, '/pgRoutingLayer/sql/target', 'target'))
        self.dock.lineEditCost.setText(Utils.getStringValue(settings, '/pgRoutingLayer/sql/cost', 'cost'))
        self.dock.lineEditReverseCost.setText(Utils.getStringValue(settings, '/pgRoutingLayer/sql/reverse_cost', 'reverse_cost'))
        self.dock.lineEditX1.setText(Utils.getStringValue(settings, '/pgRoutingLayer/sql/x1', 'x1'))
        self.dock.lineEditY1.setText(Utils.getStringValue(settings, '/pgRoutingLayer/sql/y1', 'y1'))
        self.dock.lineEditX2.setText(Utils.getStringValue(settings, '/pgRoutingLayer/sql/x2', 'x2'))
        self.dock.lineEditY2.setText(Utils.getStringValue(settings, '/pgRoutingLayer/sql/y2', 'y2'))
        self.dock.lineEditRule.setText(Utils.getStringValue(settings, '/pgRoutingLayer/sql/rule', 'rule'))
        self.dock.lineEditToCost.setText(Utils.getStringValue(settings, '/pgRoutingLayer/sql/to_cost', 'to_cost'))
        
        self.dock.lineEditIds.setText(Utils.getStringValue(settings, '/pgRoutingLayer/ids', ''))
        self.dock.lineEditSourceId.setText(Utils.getStringValue(settings, '/pgRoutingLayer/source_id', ''))
        self.dock.lineEditSourcePos.setText(Utils.getStringValue(settings, '/pgRoutingLayer/source_pos', '0.5'))
        self.dock.lineEditTargetId.setText(Utils.getStringValue(settings, '/pgRoutingLayer/target_id', ''))
        self.dock.lineEditTargetPos.setText(Utils.getStringValue(settings, '/pgRoutingLayer/target_pos', '0.5'))
        self.dock.lineEditTargetIds.setText(Utils.getStringValue(settings, '/pgRoutingLayer/target_ids', ''))
        self.dock.lineEditDistance.setText(Utils.getStringValue(settings, '/pgRoutingLayer/distance', ''))
        self.dock.lineEditPaths.setText(Utils.getStringValue(settings, '/pgRoutingLayer/paths', '2'))
        self.dock.checkBoxDirected.setChecked(Utils.getBoolValue(settings, '/pgRoutingLayer/directed', False))
        self.dock.checkBoxHasReverseCost.setChecked(Utils.getBoolValue(settings, '/pgRoutingLayer/has_reverse_cost', False))
        self.dock.plainTextEditTurnRestrictSql.setPlainText(Utils.getStringValue(settings, '/pgRoutingLayer/turn_restrict_sql', 'null'))
        
    def saveSettings(self):
        settings = QSettings()
        settings.setValue('/pgRoutingLayer/Database', self.dock.comboConnections.currentText())
        settings.setValue('/pgRoutingLayer/Function', self.dock.comboBoxFunction.currentText())
        
        settings.setValue('/pgRoutingLayer/sql/edge_table', self.dock.lineEditTable.text())
        settings.setValue('/pgRoutingLayer/sql/geometry', self.dock.lineEditGeometry.text())
        settings.setValue('/pgRoutingLayer/sql/id', self.dock.lineEditId.text())
        settings.setValue('/pgRoutingLayer/sql/source', self.dock.lineEditSource.text())
        settings.setValue('/pgRoutingLayer/sql/target', self.dock.lineEditTarget.text())
        settings.setValue('/pgRoutingLayer/sql/cost', self.dock.lineEditCost.text())
        settings.setValue('/pgRoutingLayer/sql/reverse_cost', self.dock.lineEditReverseCost.text())
        settings.setValue('/pgRoutingLayer/sql/x1', self.dock.lineEditX1.text())
        settings.setValue('/pgRoutingLayer/sql/y1', self.dock.lineEditY1.text())
        settings.setValue('/pgRoutingLayer/sql/x2', self.dock.lineEditX2.text())
        settings.setValue('/pgRoutingLayer/sql/y2', self.dock.lineEditY2.text())
        settings.setValue('/pgRoutingLayer/sql/rule', self.dock.lineEditRule.text())
        settings.setValue('/pgRoutingLayer/sql/to_cost', self.dock.lineEditToCost.text())
        
        settings.setValue('/pgRoutingLayer/ids', self.dock.lineEditIds.text())
        settings.setValue('/pgRoutingLayer/source_id', self.dock.lineEditSourceId.text())
        settings.setValue('/pgRoutingLayer/source_pos', self.dock.lineEditSourcePos.text())
        settings.setValue('/pgRoutingLayer/target_id', self.dock.lineEditTargetId.text())
        settings.setValue('/pgRoutingLayer/target_pos', self.dock.lineEditTargetPos.text())
        settings.setValue('/pgRoutingLayer/target_ids', self.dock.lineEditTargetIds.text())
        settings.setValue('/pgRoutingLayer/distance', self.dock.lineEditDistance.text())
        settings.setValue('/pgRoutingLayer/paths', self.dock.lineEditPaths.text())
        settings.setValue('/pgRoutingLayer/directed', self.dock.checkBoxDirected.isChecked())
        settings.setValue('/pgRoutingLayer/has_reverse_cost', self.dock.checkBoxHasReverseCost.isChecked())
        settings.setValue('/pgRoutingLayer/turn_restrict_sql', self.dock.plainTextEditTurnRestrictSql.toPlainText())
