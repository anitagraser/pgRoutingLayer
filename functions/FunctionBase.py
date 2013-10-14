
class FunctionBase(object):

    @classmethod
    def getName(self):
        return ''
    
    @classmethod
    def getControlNames(self):
        return [ '' ]
    
    @classmethod
    def isEdgeBase(self):
        return False
    
    @classmethod
    def canExport(self):
        return False
    
    def prepare(self, con, args, geomType, canvasItemList):
        pass
    
    def getQuery(self, args):
        return ''
    
    def draw(self, rows, con, args, geomType, canvasItemList, mapCanvas):
        pass
    
    def __init__(self, ui):
        self.ui = ui
