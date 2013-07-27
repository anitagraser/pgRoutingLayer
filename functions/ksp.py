from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
import psycopg2
from FunctionBase import FunctionBase

class Function(FunctionBase):
    
    @classmethod
    def getName(self):
        return 'ksp'
    
    @classmethod
    def getControlNames(self):
        # 'id' and 'target' are used for finding nearest node
        return [
            'labelId', 'lineEditId',
            'labelSource', 'lineEditSource',
            'labelTarget', 'lineEditTarget',
            'labelCost', 'lineEditCost',
            'labelReverseCost', 'lineEditReverseCost',
            'labelSourceId', 'lineEditSourceId', 'buttonSelectSourceId',
            'labelTargetId', 'lineEditTargetId', 'buttonSelectTargetId',
            'labelPaths', 'lineEditPaths',
            'checkBoxHasReverseCost'
        ]
    
    @classmethod
    def isEdgeBase(self):
        return False
    
    @classmethod
    def canExport(self):
        return True
    
    def prepare(self, con, args, geomType, canvasItemList):
        resultPathsRubberBands = canvasItemList['paths']
        for path in resultPathsRubberBands:
            path.reset(False)
        canvasItemList['paths'] = []
    
    def getQuery(self, args):
        return """
            SELECT seq, id1 AS route, id2 AS node, id3 AS edge, cost FROM pgr_ksp('
                SELECT %(id)s AS id,
                    %(source)s::int4 AS source,
                    %(target)s::int4 AS target,
                    %(cost)s::float8 AS cost%(reverse_cost)s
                    FROM %(edge_table)s',
                %(source_id)s, %(target_id)s, %(paths)s, %(has_reverse_cost)s)""" % args
    
    def draw(self, rows, con, args, geomType, canvasItemList, mapCanvas):
        resultPathsRubberBands = canvasItemList['paths']
        rubberBand = None
        cur_route_id = -1
        for row in rows:
            cur2 = con.cursor()
            args['result_route_id'] = row[1]
            args['result_node_id'] = row[2]
            args['result_edge_id'] = row[3]
            args['result_cost'] = row[4]
            if args['result_route_id'] <> cur_route_id:
                cur_route_id = args['result_route_id']
                if rubberBand:
                    resultPathsRubberBands.append(rubberBand)
                    rubberBand = None
                
                rubberBand = QgsRubberBand(mapCanvas, False)
                rubberBand.setColor(QColor(255, 0, 0, 128))
                rubberBand.setWidth(4)
            
            #if args['result_edge_id'] != -1:
            if args['result_edge_id'] != 0:
                query2 = """
                    SELECT ST_AsText(ST_Transform(%(geometry)s, %(canvas_srid)d)) FROM %(edge_table)s
                        WHERE %(source)s = %(result_node_id)d AND %(id)s = %(result_edge_id)d
                    UNION
                    SELECT ST_AsText(ST_Transform(ST_Reverse(%(geometry)s), %(canvas_srid)d)) FROM %(edge_table)s
                        WHERE %(target)s = %(result_node_id)d AND %(id)s = %(result_edge_id)d;
                """ % args
                ##QMessageBox.information(self.ui, self.ui.windowTitle(), query2)
                cur2.execute(query2)
                row2 = cur2.fetchone()
                ##QMessageBox.information(self.ui, self.ui.windowTitle(), str(row2[0]))
                assert row2, "Invalid result geometry. (route_id:%(result_route_id)d, node_id:%(result_node_id)d, edge_id:%(result_edge_id)d)" % args
                
                geom = QgsGeometry().fromWkt(str(row2[0]))
                if geom.wkbType() == QGis.WKBMultiLineString:
                    for line in geom.asMultiPolyline():
                        for pt in line:
                            rubberBand.addPoint(pt)
                elif geom.wkbType() == QGis.WKBLineString:
                    for pt in geom.asPolyline():
                        rubberBand.addPoint(pt)
        
        if rubberBand:
            resultPathsRubberBands.append(rubberBand)
            rubberBand = None
    
    def __init__(self, ui):
        FunctionBase.__init__(self, ui)
