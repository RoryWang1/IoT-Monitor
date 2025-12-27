Utility Scripts Module
======================

Function
--------
System deployment and data processing tools

System Management Scripts
-------------------------
deploy_system.sh      System deployment
start_system.sh       Start system
stop_system.sh        Stop system

Data Processing Scripts
-----------------------
pcap_time_processor.py        PCAP time processing
export_reference_data.py      Export reference data
import_reference_data.py      Import reference data
quick_reference_setup.py      Quick reference data management

Main Usage
----------
System deployment (run once):
  ./utils/deploy_system.sh

Daily start/stop:
  ./utils/start_system.sh
  ./utils/stop_system.sh

PCAP time processing:
  python utils/pcap_time_processor.py SOURCE_DIR --timezone UTC

Reference data management:
  python utils/export_reference_data.py
  python utils/import_reference_data.py
  python utils/quick_reference_setup.py export 