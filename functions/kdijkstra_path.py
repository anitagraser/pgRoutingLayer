from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
import psycopg2
from FunctionBase import FunctionBase

class Function(FunctionBase):
    
    @classmethod
    def getName(self):
        return 'kdijkstra(path)'
    
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
            'labelTargetIds', 'lineEditTargetIds', 'buttonSelectTargetIds',
            'checkBoxDirected', 'checkBoxHasReverseCost'
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
            SELECT * FROM pgr_kdijkstraPath('
                SELECT %(id)s AS id,
                    %(source)s::int4 AS source,
                    %(target)s::int4 AS target,
                    %(cost)s::float8 AS cost%(reverse_cost)s
                    FROM %(edge_table)s',
                %(source_id)s, array[%(target_ids)s], %(directed)s, %(has_reverse_cost)s)""" % args
    
    def draw(self, rows, con, args, geomType, canvasItemList, mapCanvas):
        resultPathsRubberBands = canvasItemList['paths']
        rubberBand = None
        cur_target_id = -1
        for row in rows:
            cur2 = con.cursor()
            args['result_target_id'] = row[1]
            args['result_edge_target_node_id'] = row[2]
            args['result_edge_id'] = row[3]
            args['result_cost'] = row[4]
            if args['result_target_id'] <> cur_target_id:
                cur_target_id = args['result_target_id']
                if rubberBand:
                    resultPathsRubberBands.append(rubberBand)
                    rubberBand = None
                
                rubberBand = QgsRubberBand(mapCanvas, False)
                rubberBand.setColor(Qt.red)
                rubberBand.setWidth(2)
            
            if args['result_edge_id'] != -1:
                #query2 = """
                #    SELECT ST_AsText(ST_Transform(%(geometry)s, %(canvas_srid)d)) FROM %(edge_table)s
                #        WHERE %(source)s = %(result_edge_target_node_id)d AND %(id)s = %(result_edge_id)d
                #    UNION
                #    SELECT ST_AsText(ST_Transform(ST_Reverse(%(geometry)s), %(canvas_srid)d)) FROM %(edge_table)s
                #        WHERE %(target)s = %(result_edge_target_node_id)d AND %(id)s = %(result_edge_id)d;
                #""" % args
                query2 = """
                    SELECT ST_AsText(ST_Transform(ST_Reverse(%(geometry)s), %(canvas_srid)d)) FROM %(edge_table)s
                        WHERE %(source)s = %(result_edge_target_node_id)d AND %(id)s = %(result_edge_id)d
                    UNION
                    SELECT ST_AsText(ST_Transform(%(geometry)s, %(canvas_srid)d)) FROM %(edge_table)s
                        WHERE %(target)s = %(result_edge_target_node_id)d AND %(id)s = %(result_edge_id)d;
                """ % args
                ##QMessageBox.information(self.ui, self.ui.windowTitle(), query2)
                cur2.execute(query2)
                row2 = cur2.fetchone()
                ##QMessageBox.information(self.ui, self.ui.windowTitle(), str(row2[0]))
                assert row2, "Invalid result geometry. (vertex_id:%(result_edge_target_node_id)d, edge_id:%(result_edge_id)d)" % args
                
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
