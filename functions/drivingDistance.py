from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
import psycopg2
from pgRoutingLayer import pgRoutingLayer_utils as Utils
from FunctionBase import FunctionBase

class Function(FunctionBase):
    
    @classmethod
    def getName(self):
        return 'drivingDistance'
    
    @classmethod
    def getControlNames(self):
        return [
            'labelId', 'lineEditId',
            'labelSource', 'lineEditSource',
            'labelTarget', 'lineEditTarget',
            'labelCost', 'lineEditCost',
            'labelReverseCost', 'lineEditReverseCost',
            'labelSourceId', 'lineEditSourceId', 'buttonSelectSourceId',
            'labelDistance', 'lineEditDistance',
            'checkBoxDirected', 'checkBoxHasReverseCost'
        ]
    
    @classmethod
    def isEdgeBase(self):
        return False
    
    @classmethod
    def canExport(self):
        return False
    
    def prepare(self, con, args, geomType, canvasItemList):
        resultNodesVertexMarkers = canvasItemList['markers']
        for marker in resultNodesVertexMarkers:
            marker.setVisible(False)
        canvasItemList['markers'] = []
    
    def getQuery(self, args):
        return """
            SELECT seq, id1 AS node, id2 AS edge, cost FROM pgr_drivingDistance('
                SELECT %(id)s AS id,
                    %(source)s::int4 AS source,
                    %(target)s::int4 AS target,
                    %(cost)s::float8 AS cost%(reverse_cost)s
                    FROM %(edge_table)s',
                %(source_id)s, %(distance)s, %(directed)s, %(has_reverse_cost)s)""" % args
    
    def draw(self, rows, con, args, geomType, canvasItemList, mapCanvas):
        resultNodesVertexMarkers = canvasItemList['markers']
        Utils.setStartPoint(geomType, args)
        Utils.setEndPoint(geomType, args)
        for row in rows:
            cur2 = con.cursor()
            args['result_node_id'] = row[1]
            args['result_edge_id'] = row[2]
            args['result_cost'] = row[3]
            query2 = """
                SELECT ST_AsText(%(transform_s)s%(startpoint)s%(transform_e)s) FROM %(edge_table)s
                    WHERE %(source)s = %(result_node_id)d AND %(id)s = %(result_edge_id)d
                UNION
                SELECT ST_AsText(%(transform_s)s%(endpoint)s%(transform_e)s) FROM %(edge_table)s
                    WHERE %(target)s = %(result_node_id)d AND %(id)s = %(result_edge_id)d
            """ % args
            cur2.execute(query2)
            row2 = cur2.fetchone()
            assert row2, "Invalid result geometry. (node_id:%(result_node_id)d, edge_id:%(result_edge_id)d)" % args
            
            geom = QgsGeometry().fromWkt(str(row2[0]))
            pt = geom.asPoint()
            vertexMarker = QgsVertexMarker(mapCanvas)
            vertexMarker.setColor(Qt.red)
            vertexMarker.setPenWidth(2)
            vertexMarker.setIconSize(5)
            vertexMarker.setCenter(QgsPoint(pt))
            resultNodesVertexMarkers.append(vertexMarker)
    
    def __init__(self, ui):
        FunctionBase.__init__(self, ui)
