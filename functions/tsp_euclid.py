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
            SELECT * FROM pgr_tsp('
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
        # return columns are 'vertex_id', 'edge_id', 'cost'
        i = 0
        for row in rows:
            cur2 = con.cursor()
            args['result_id1'] = row[1]
            args['result_id2'] = row[2]
            args['result_cost'] = row[3]
            query2 = """
                SELECT ST_AsText(ST_Transform(%(startpoint)s, %(canvas_srid)d)) FROM %(edge_table)s
                    WHERE %(source)s = %(result_id2)d
                UNION
                SELECT ST_AsText(ST_Transform(%(endpoint)s, %(canvas_srid)d)) FROM %(edge_table)s
                    WHERE %(target)s = %(result_id2)d
            """ % args
            cur2.execute(query2)
            row2 = cur2.fetchone()
            assert row2, "Invalid result geometry. (id1:%(result_id2)d)" % args
            
            geom = QgsGeometry().fromWkt(str(row2[0]))
            pt = geom.asPoint()
            i += 1
            textAnnotation = QgsTextAnnotationItem(mapCanvas)
            textAnnotation.setMapPosition(geom.asPoint())
            textAnnotation.setFrameSize(QSizeF(20,20))
            textAnnotation.setOffsetFromReferencePoint(QPointF(20, -40))
            textAnnotation.setDocument(QTextDocument(str(i)))
            textAnnotation.update()
            resultNodesTextAnnotations.append(textAnnotation)
    
    def __init__(self, ui):
        FunctionBase.__init__(self, ui)
