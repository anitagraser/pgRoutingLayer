from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
import psycopg2
from FunctionBase import FunctionBase

class Function(FunctionBase):
    
    @classmethod
    def getName(self):
        return 'kdijkstra(cost)'
    
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
        return False
    
    def prepare(self, con, args, geomType, canvasItemList):
        resultNodesTextAnnotations = canvasItemList['annotations']
        for anno in resultNodesTextAnnotations:
            anno.setVisible(False)
        canvasItemList['annotations'] = []
    
    def getQuery(self, args):
        return """
            SELECT seq, id1 AS source, id2 AS target, cost FROM pgr_kdijkstraCost('
                SELECT %(id)s AS id,
                    %(source)s::int4 AS source,
                    %(target)s::int4 AS target,
                    %(cost)s::float8 AS cost%(reverse_cost)s
                    FROM %(edge_table)s',
                %(source_id)s, array[%(target_ids)s], %(directed)s, %(has_reverse_cost)s)""" % args
    
    def draw(self, rows, con, args, geomType, canvasItemList, mapCanvas):
        resultNodesTextAnnotations = canvasItemList['annotations']
        if geomType == 'ST_MultiLineString':
            args['startpoint'] = "ST_StartPoint(ST_GeometryN(%(geometry)s, 1))" % args
            args['endpoint'] = "ST_EndPoint(ST_GeometryN(%(geometry)s, 1))" % args
        elif geomType == 'ST_LineString':
            args['startpoint'] = "ST_StartPoint(%(geometry)s)" % args
            args['endpoint'] = "ST_EndPoint(%(geometry)s)" % args
        # return columns are 'seq', 'id1(source id)', 'id2(target id)', 'cost'
        for row in rows:
            cur2 = con.cursor()
            args['result_seq'] = row[0]
            args['result_source_id'] = row[1]
            args['result_target_id'] = row[2]
            args['result_cost'] = row[3]
            query2 = """
                SELECT ST_AsText(ST_Transform(%(startpoint)s, %(canvas_srid)d)) FROM %(edge_table)s
                    WHERE %(source)s = %(result_target_id)d
                UNION
                SELECT ST_AsText(ST_Transform(%(endpoint)s, %(canvas_srid)d)) FROM %(edge_table)s
                    WHERE %(target)s = %(result_target_id)d
            """ % args
            cur2.execute(query2)
            row2 = cur2.fetchone()
            assert row2, "Invalid result geometry. (target_id:%(result_target_id)d)" % args
            
            geom = QgsGeometry().fromWkt(str(row2[0]))
            pt = geom.asPoint()
            textDocument = QTextDocument("%(result_target_id)d:%(result_cost)f" % args)
            textAnnotation = QgsTextAnnotationItem(mapCanvas)
            textAnnotation.setMapPosition(geom.asPoint())
            textAnnotation.setFrameSize(QSizeF(textDocument.idealWidth(), 20))
            textAnnotation.setOffsetFromReferencePoint(QPointF(20, -40))
            textAnnotation.setDocument(textDocument)
            
            textAnnotation.update()
            resultNodesTextAnnotations.append(textAnnotation)
    
    def __init__(self, ui):
        FunctionBase.__init__(self, ui)
