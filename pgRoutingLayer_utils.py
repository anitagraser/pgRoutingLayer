from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
import psycopg2
import sip

def setStartPoint(geomType, args):
    if geomType == 'ST_MultiLineString':
        args['startpoint'] = "ST_StartPoint(ST_GeometryN(%(geometry)s, 1))" % args
    elif geomType == 'ST_LineString':
        args['startpoint'] = "ST_StartPoint(%(geometry)s)" % args

def setEndPoint(geomType, args):
    if geomType == 'ST_MultiLineString':
        args['endpoint'] = "ST_EndPoint(ST_GeometryN(%(geometry)s, 1))" % args
    elif geomType == 'ST_LineString':
        args['endpoint'] = "ST_EndPoint(%(geometry)s)" % args

def setTransformQuotes(args):
    if args['srid'] > 0 and args['canvas_srid'] > 0:
        args['transform_s'] = "ST_Transform("
        args['transform_e'] = ", %(canvas_srid)d)" % args
    else:
        args['transform_s'] = ""
        args['transform_e'] = ""

def isSIPv2():
    return sip.getapi('QVariant') > 1

def getStringValue(settings, key, value):
    if isSIPv2():
        return settings.value(key, value, type=str)
    else:
        return settings.value(key, QVariant(value)).toString()

def getBoolValue(settings, key, value):
    if isSIPv2():
        return settings.value(key, value, type=bool)
    else:
        return settings.value(key, QVariant(value)).toBool()

def isQGISv1():
    return QGis.QGIS_VERSION_INT < 10900

def getDestinationCrs(mapRenderer):
    if isQGISv1():
        return mapRenderer.destinationSrs()
    else:
        return mapRenderer.destinationCrs()

def getCanvasSrid(crs):
    if isQGISv1():
        return crs.epsg()
    else:
        return crs.postgisSrid()

def createFromSrid(crs, srid):
    if isQGISv1():
        return crs.createFromEpsg(srid)
    else:
        return crs.createFromSrid(srid)

def getRubberBandType(isPolygon):
    if isQGISv1():
        return isPolygon
    else:
        if isPolygon:
            return QGis.Polygon
        else:
            return QGis.Line
