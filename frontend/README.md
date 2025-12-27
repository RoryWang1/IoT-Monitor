Frontend Module
===============

Function
--------
Device monitoring interface and data visualization

Start Scripts
-------------
npm run dev        Development mode
npm run build      Build
npm start          Production mode

Directory Structure
-------------------
src/
  components/      Components
  pages/           Page routing
  hooks/           Custom hooks
  services/        API services

Main Pages
----------
/                        Experiment overview
/experiment-detail/[id]  Experiment details
/device-detail/[id]      Device details
/reference-management    Reference data management

Script Files
------------
scripts/start-dev.js     Development start script
scripts/start-prod.js    Production start script 