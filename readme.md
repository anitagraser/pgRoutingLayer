# Welcome to PgRouting Layer!

A plugin for QGIS by Anita Graser and Ko Nagase

* project home and bug tracker: https://github.com/anitagraser/pgRoutingLayer
* plugin repository: http://plugins.qgis.org/plugins


## What is the goal

PgRouting Layer is a plugin for QGIS that serves as a GUI for pgRouting - a popular routing solution for PostGIS databases.

## What this plugin currently does

Please check the pgRouting documentation for detailed descriptons: http://docs.pgrouting.org/2.0/en/doc/index.html

PgRoutingLayer currently supports the following functions:

* alphashape
* astar
* bdAstar
* bdDijkstra
* dijkstra
* drivingDistance
* kdijkstra_cost
* kdijkstra_path
* ksp
* shootingStar
* trsp_edge
* trsp_vertex
* tsp_euclid

## License

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

## Installation

This plugin can be installed using the QGIS Plugin Manager. You will have to enable "experimental" plugins.

### Dependencies

You'll need pgRouting up and running to use this plugin.

Additionally, QGIS needs python-psycopg2 installed to be able to connect to the database.
