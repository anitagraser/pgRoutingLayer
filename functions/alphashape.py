from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
import psycopg2
from FunctionBase import FunctionBase

class Function(FunctionBase):
    
    @classmethod
    def getName(self):
        return 'alphashape'
    
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
        resultAreaRubberBand = canvasItemList['area']
        resultAreaRubberBand.reset(True)
        query = """
        CREATE TEMPORARY TABLE node AS
            SELECT id,
                ST_X(%(geometry)s) AS x,
                ST_Y(%(geometry)s) AS y,
                %(geometry)s
                FROM (
                    SELECT %(source)s AS id,
                        %(startpoint)s AS %(geometry)s
                        FROM %(edge_table)s
                    UNION
                    SELECT %(target)s AS id,
                        %(endpoint)s AS %(geometry)s
                        FROM %(edge_table)s
                ) AS node;"""
        if geomType == 'ST_MultiLineString':
            args['startpoint'] = "ST_StartPoint(ST_GeometryN(%(geometry)s, 1))" % args
            args['endpoint'] = "ST_EndPoint(ST_GeometryN(%(geometry)s, 1))" % args
        elif geomType == 'ST_LineString':
            args['startpoint'] = "ST_StartPoint(%(geometry)s)" % args
            args['endpoint'] = "ST_EndPoint(%(geometry)s)" % args
            
        cur = con.cursor()
        cur.execute(query % args)
    
    def getQuery(self, args):
        return """
            SELECT * FROM alphashape('
                SELECT *
                    FROM node
                    JOIN
                    (SELECT * FROM driving_distance(''
                        SELECT %(id)s AS id,
                            %(source)s::int4 AS source,
                            %(target)s::int4 AS target,
                            %(cost)s::float8 AS cost%(reverse_cost)s
                            FROM %(edge_table)s'',
                        %(source_id)s, %(distance)s, %(directed)s, %(has_reverse_cost)s))
                    AS dd ON node.id = dd.vertex_id'::text)""" % args
    
    def draw(self, rows, con, args, geomType, canvasItemList, mapCanvas):
        resultAreaRubberBand = canvasItemList['area']
        # return columns are 'x', 'y'
        for row in rows:
            x = row[0]
            y = row[1]
            resultAreaRubberBand.addPoint(QgsPoint(x, y))
    
    def __init__(self, ui):
        FunctionBase.__init__(self, ui)
