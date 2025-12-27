Supplementary Material: Source Code for "Hierarchical IoT Testbed: Enhancing Interoperability, Efficiency, and Security"

Overview:
This archive contains the complete source code for the proposed Hierarchical IoT Testbed system. The system integrates a backend for data processing and analysis, a frontend for visualization, and simulation scripts for performance validation.

Directory Structure:
- backend/: Python-based backend (FastAPI/Flask) handling data ingestion, processing, and the "Edge Gravity" algorithm implementation.
- frontend/: web-based dashboard (React/Next.js) for visualizing the network topology and security alerts.
- scripts/: automated scripts for generating traffic, running simulations, and producing the experimental plots used in the manuscript.
- tests/: Unit and integration tests, including the scalability and performance benchmarks.
- database/: Database schema and utilities.

Requirements:
- Python 3.12+
- Node.js (for frontend)
- See requirements.txt (backend) and package.json (frontend) for dependencies.

Usage:
1. Backend: Navigate to the root directory, install dependencies via `pip install -r requirements.txt`, and run the start script.
2. Frontend: Navigate to `frontend/`, run `npm install`, then `npm run dev`.

Note:
This code is provided to facilitate the replication of results presented in the study. User experience study data is excluded due to privacy restrictions.
