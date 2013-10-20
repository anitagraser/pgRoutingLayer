# -*- coding: utf-8 -*-

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import qgis.core
import pgRoutingLayer_utils as Utils

class ConnectionManager:

	SUPPORTED_CONNECTORS = ['postgis']
	MISSED_CONNECTORS = []

	@classmethod
	def initConnectionSupport(self):
		conntypes = ConnectionManager.SUPPORTED_CONNECTORS
		for c in conntypes:
			try:
				connector = self.getConnection( c )
			except ImportError, e:
				module = e.args[0][ len("No module named "): ]
				ConnectionManager.SUPPORTED_CONNECTORS.remove( c )
				ConnectionManager.MISSED_CONNECTORS.append( (c, module) )

		return len(ConnectionManager.SUPPORTED_CONNECTORS) > 0

	@classmethod
	def getConnection(self, conntype, uri=None):
		if not self.isSupported(conntype):
			raise NotSupportedConnTypeException(conntype)

		# import the connector
		exec( "from connectors import %s as connector" % conntype)
		return connector.Connection(uri) if uri else connector.Connection

	@classmethod
	def isSupported(self, conntype):
		return conntype in ConnectionManager.SUPPORTED_CONNECTORS

	@classmethod
	def getAvailableConnections(self, conntypes=None):
		if conntypes == None:
			conntypes = ConnectionManager.SUPPORTED_CONNECTORS
		if not hasattr(conntypes, '__iter__'):
			conntypes = [conntypes]

		connections = []
		for c in conntypes:
			connection = self.getConnection( c )
			connections.extend( connection.getAvailableConnections() )
		return connections


class NotSupportedConnTypeException(Exception):
	def __init__(self, conntype):
		self.msg = u"%s is not supported yet" % conntype

	def __str__(self):
		return self.msg.encode('utf-8')


class DbError(Exception):
	def __init__(self, errormsg, query=None):
		self.msg = unicode( errormsg )
		self.query = unicode( query ) if query else None

	def __str__(self):
		msg = self.msg.encode('utf-8')
		if self.query != None:
			msg += "\nQuery:\n" + self.query.encode('utf-8')
		return msg


class Connection:

	def __init__(self, uri):
		self.uri = uri

	@classmethod
	def getTypeName(self):
		pass

	@classmethod
	def getTypeNameString(self):
		pass

	@classmethod
	def getProviderName(self):
		pass

	@classmethod
	def getSettingsKey(self):
		pass

	@classmethod
	def icon(self):
		pass

	@classmethod
	def getAvailableConnections(self):
		connections = []

		settings = QSettings()
		settings.beginGroup( "/%s/connections" % self.getSettingsKey() )
		keys = settings.childGroups()
		for name in keys:
			connections.append( Connection.ConnectionAction(name, self.getTypeName()) )
		settings.endGroup()

		return connections


	def getURI(self):
		# returns a new QgsDataSourceURI instance
		return qgis.core.QgsDataSourceURI( self.uri.connectionInfo() )

	def getAction(self, parent=None):
		return Connection.ConnectionAction(self.uri.database(), self.getTypeName(), parent)


	class ConnectionAction(QAction):
		def __init__(self, text, conntype, parent=None):
			self.type = conntype
			icon = ConnectionManager.getConnection(self.type).icon()
			QAction.__init__(self, icon, text, parent)

		def connect(self):
			selected = self.text()
			conn = ConnectionManager.getConnection( self.type ).connect( selected, self.parent() )

			# set as default in QSettings
			settings = QSettings()
			settings.setValue( "/%s/connections/selected" % conn.getSettingsKey(), selected )

			return conn


class TableAttribute:
	pass

class TableConstraint:
	""" class that represents a constraint of a table (relation) """
	
	TypeCheck, TypeForeignKey, TypePrimaryKey, TypeUnique = range(4)
	types = { "c" : TypeCheck, "f" : TypeForeignKey, "p" : TypePrimaryKey, "u" : TypeUnique }
	
	on_action = { "a" : "NO ACTION", "r" : "RESTRICT", "c" : "CASCADE", "n" : "SET NULL", "d" : "SET DEFAULT" }
	match_types = { "u" : "UNSPECIFIED", "f" : "FULL", "p" : "PARTIAL" }

	pass

class TableIndex:
	pass

class TableTrigger:
	# Bits within tgtype (pg_trigger.h)
	TypeRow      = (1 << 0) # row or statement
	TypeBefore   = (1 << 1) # before or after
	# events: one or more
	TypeInsert   = (1 << 2)
	TypeDelete   = (1 << 3)
	TypeUpdate   = (1 << 4)
	TypeTruncate = (1 << 5)

	pass

class TableRule:
	pass

class TableField:
	def is_null_txt(self):
		if self.is_null:
			return "NULL"
		else:
			return "NOT NULL"
		
	def field_def(self, db):
		""" return field definition as used for CREATE TABLE or ALTER TABLE command """
		data_type = self.data_type if (not self.modifier or self.modifier < 0) else "%s(%d)" % (self.data_type, self.modifier)
		txt = "%s %s %s" % (db._quote(self.name), data_type, self.is_null_txt())
		if self.default and len(self.default) > 0:
			txt += " DEFAULT %s" % self.default
		return txt
