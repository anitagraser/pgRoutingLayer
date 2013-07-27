from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
import psycopg2
from FunctionBase import FunctionBase

class Function(FunctionBase):
    
    @classmethod
    def getName(self):
        return 'shootingStar'
    
    @classmethod
    def getControlNames(self):
        return [
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
            'labelSourceId', 'lineEditSourceId', 'buttonSelectSourceId',
            'labelTargetId', 'lineEditTargetId', 'buttonSelectTargetId',
            'checkBoxDirected', 'checkBoxHasReverseCost'
        ]
    
    @classmethod
    def isEdgeBase(self):
        return True
    
    @classmethod
    def canExport(self):
        return True
    
    def prepare(self, con, args, geomType, canvasItemList):
        resultPathRubberBand = canvasItemList['path']
        resultPathRubberBand.reset(False)
    
    def getQuery(self, args):
        return """
            SELECT seq, id1 AS node, id2 AS edge, cost FROM pgr_shootingStar('
                SELECT %(id)s AS id,
                    %(source)s::int4 AS source,
                    %(target)s::int4 AS target,
                    %(cost)s::float8 AS cost%(reverse_cost)s,
                    %(x1)s::float8 AS x1,
                    %(y1)s::float8 AS y1,
                    %(x2)s::float8 AS x2,
                    %(y2)s::float8 AS y2,
                    %(rule)s::text AS rule,
                    %(to_cost)s::float8
                    FROM %(edge_table)s',
                %(source_id)s, %(target_id)s, %(directed)s, %(has_reverse_cost)s)""" % args
    
    def draw(self, rows, con, args, geomType, canvasItemList, mapCanvas):
        resultPathRubberBand = canvasItemList['path']
        for row in rows:
            cur2 = con.cursor()
            args['result_vertex_id'] = row[1]
            args['result_edge_id'] = row[2]
            args['result_cost'] = row[3]
            query2 = """
                SELECT ST_AsText(%(transform_s)s%(geometry)s%(transform_e)s) FROM %(edge_table)s
                    WHERE %(source)s = %(result_vertex_id)d AND %(id)s = %(result_edge_id)d
                UNION
                SELECT ST_AsText(%(transform_s)sST_Reverse(%(geometry)s)%(transform_e)s) FROM %(edge_table)s
                    WHERE %(target)s = %(result_vertex_id)d AND %(id)s = %(result_edge_id)d;
            """ % args
            ##QMessageBox.information(self.ui, self.ui.windowTitle(), query2)
            cur2.execute(query2)
            row2 = cur2.fetchone()
            ##QMessageBox.information(self.ui, self.ui.windowTitle(), str(row2[0]))
            # TODO: shooting_star always returns invalid vertex_id!
            assert row2, "Invalid result geometry. (vertex_id:%(result_vertex_id)d, edge_id:%(result_edge_id)d)" % args
            
            geom = QgsGeometry().fromWkt(str(row2[0]))
            if geom.wkbType() == QGis.WKBMultiLineString:
                for line in geom.asMultiPolyline():
                    for pt in line:
                        resultPathRubberBand.addPoint(pt)
            elif geom.wkbType() == QGis.WKBLineString:
                for pt in geom.asPolyline():
                    resultPathRubberBand.addPoint(pt)
    
    def __init__(self, ui):
        FunctionBase.__init__(self, ui)
