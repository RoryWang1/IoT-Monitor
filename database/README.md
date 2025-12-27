Database Module
===============

Function
--------
PostgreSQL database and data storage

Start Scripts
-------------
./bin/start_database.sh    Start database
./bin/stop_database.sh     Stop database

Directory Structure
-------------------
schema/           Database schema
services/         Database services
repositories/     Data access layer
bin/              Management scripts

Main Tables
-----------
experiments       Experiment management
devices           Device information
packet_flows      Network packet flow data
known_devices     Known device information
vendor_patterns   Vendor pattern matching

Connection Parameters
---------------------
Port: 5433
User: iot_user
Database: iot_monitor 