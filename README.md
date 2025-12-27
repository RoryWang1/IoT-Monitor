IoT Device Monitor
==================

Function
--------
PCAP file network traffic monitoring and analysis

Executable Scripts
------------------
sudo ./deployment/local/local_deploy.sh    (Initial deployment)

sudo ./start_system.sh     (Start system)

sudo ./stop_system.sh      (Stop system)

Access URL
----------
http://IP_ADDRESS:3001

Directory Structure
-------------------
backend/         Backend API and data processing
frontend/        Frontend interface
database/        Database
config/          Configuration files
utils/           Management scripts
pcap_input/      PCAP file input directory

Ports
-----
Database: 5433
Backend: 8001
Frontend: 3001

PCAP File Naming
----------------
MAC_YY-MM-DD-HH-MM-SS_TIMEZONE.pcap 
