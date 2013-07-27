from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
import psycopg2
from FunctionBase import FunctionBase

class Function(FunctionBase):
    
    @classmethod
    def getName(self):
        return 'tsp(euclid)'
    
    @classmethod
    def getControlNames(self):
        # 'id' and 'target' are used for finding nearest node
        return [
            'labelId', 'lineEditId',
            'labelSource', 'lineEditSource',
            'labelTarget', 'lineEditTarget',
            'labelX1', 'lineEditX1',
            'labelY1', 'lineEditY1',
            'labelX2', 'lineEditX2',
            'labelY2', 'lineEditY2',
            'labelIds', 'lineEditIds', 'buttonSelectIds',
            'labelSourceId', 'lineEditSourceId', 'buttonSelectSourceId',
            'labelTargetId', 'lineEditTargetId', 'buttonSelectTargetId'
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
            SELECT seq, id1 AS internal, id2 AS node, cost FROM pgr_tsp('
                SELECT DISTINCT id, x, y FROM
                    (SELECT DISTINCT %(source)s AS id, %(x1)s::float8 AS x, %(y1)s::float8 AS y FROM %(edge_table)s
                    UNION
                    SELECT DISTINCT %(target)s AS id, %(x2)s::float8 AS x, %(y2)s::float8 AS y FROM %(edge_table)s)
                    AS node WHERE node.id IN (%(ids)s)',
                %(source_id)s, %(target_id)s)""" % args
    
    def draw(self, rows, con, args, geomType, canvasItemList, mapCanvas):
        resultNodesTextAnnotations = canvasItemList['annotations']
        if geomType == 'ST_MultiLineString':
            args['startpoint'] = "ST_StartPoint(ST_GeometryN(%(geometry)s, 1))" % args
            args['endpoint'] = "ST_EndPoint(ST_GeometryN(%(geometry)s, 1))" % args
        elif geomType == 'ST_LineString':
            args['startpoint'] = "ST_StartPoint(%(geometry)s)" % args
            args['endpoint'] = "ST_EndPoint(%(geometry)s)" % args
        # return columns are 'seq', 'id1(internal index)', 'id2(node id)', 'cost'
        for row in rows:
            cur2 = con.cursor()
            args['result_seq'] = row[0]
            args['result_internal_id'] = row[1]
            args['result_node_id'] = row[2]
            args['result_cost'] = row[3]
            query2 = """
                SELECT ST_AsText(ST_Transform(%(startpoint)s, %(canvas_srid)d)) FROM %(edge_table)s
                    WHERE %(source)s = %(result_node_id)d
                UNION
                SELECT ST_AsText(ST_Transform(%(endpoint)s, %(canvas_srid)d)) FROM %(edge_table)s
                    WHERE %(target)s = %(result_node_id)d
            """ % args
            cur2.execute(query2)
            row2 = cur2.fetchone()
            assert row2, "Invalid result geometry. (node_id:%(result_node_id)d)" % args
            
            geom = QgsGeometry().fromWkt(str(row2[0]))
            pt = geom.asPoint()
            textDocument = QTextDocument("%(result_seq)d:%(result_node_id)d" % args)
            textAnnotation = QgsTextAnnotationItem(mapCanvas)
            textAnnotation.setMapPosition(geom.asPoint())
            textAnnotation.setFrameSize(QSizeF(textDocument.idealWidth(), 20))
            textAnnotation.setOffsetFromReferencePoint(QPointF(20, -40))
            textAnnotation.setDocument(textDocument)
            textAnnotation.update()
            resultNodesTextAnnotations.append(textAnnotation)
    
    def __init__(self, ui):
        FunctionBase.__init__(self, ui)
