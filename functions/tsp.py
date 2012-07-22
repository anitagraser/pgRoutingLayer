from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
import psycopg2
from FunctionBase import FunctionBase

class Function(FunctionBase):
    
    @classmethod
    def getName(self):
        return 'tsp'
    
    @classmethod
    def getControlNames(self):
        # 'id' and 'target' are used for finding nearest node
        return [
            'lineEditId', 'lineEditSource', 'lineEditTarget',
            'lineEditX1', 'lineEditY1',
            'lineEditIds', 'buttonSelectIds',
            'lineEditSourceId', 'buttonSelectSourceId'
        ]
    
    @classmethod
    def isEdgeBase(self):
        return False
    
    @classmethod
    def prepare(self, con, args, geomType, canvasItemList):
        resultNodesTextAnnotations = canvasItemList['annotations']
        for anno in resultNodesTextAnnotations:
            anno.setVisible(False)
        canvasItemList['annotations'] = []
    
    @classmethod
    def getQuery(self, args):
        return """
            SELECT * FROM tsp('
                SELECT DISTINCT %(source)s AS source_id,
                    %(x1)s::float8 AS x,
                    %(y1)s::float8 AS y
                    FROM %(edge_table)s
                    WHERE %(source)s IN (%(ids)s)',
                '%(ids)s', %(source_id)s)""" % args
    
    @classmethod
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
            args['result_vertex_id'] = row[0]
            args['result_edge_id'] = row[1]
            args['result_cost'] = row[2]
            query2 = """
                SELECT ST_AsText(%(startpoint)s) FROM %(edge_table)s
                    WHERE %(source)s = %(result_vertex_id)d
                UNION
                SELECT ST_AsText(%(endpoint)s) FROM %(edge_table)s
                    WHERE %(target)s = %(result_vertex_id)d
            """ % args
            cur2.execute(query2)
            row2 = cur2.fetchone()
            assert row2, "Invalid result geometry. (vertex_id:%(result_vertex_id)d)" % args
            
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
