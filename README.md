Sudan Intervention Dashboard

An interactive web dashboard for monitoring and analysing humanitarian interventions across Sudan, built with Streamlit and Plotly.

Features

Secure Login — Password-protected access with SHA-256 hashed credentials via Streamlit secrets
Interactive Map — Dark-themed Plotly map with Sudan admin2 boundaries, colour-coded project dots, and rich hover tooltips
KPI Metrics — At-a-glance cards for total interventions, projects, states covered, and implementing agencies
Dynamic Filters — Sidebar filters for date range, agency, sector, location, project, and status
Project Table — Paginated, downloadable CSV table of all filtered projects
AI Insights — On-demand analysis via built-in summary or local Ollama LLM (Llama 3.2 / Mistral)

Requirements

Python 3.9+
Streamlit
Pandas
Plotly
Requests

Install all dependencies:

pip install -r requirements.txt


Setup
Clone the repository

git clone https://github.com/your-username/sudan-intervention-dashboard.git
cd sudan-intervention-dashboard

Add your credentials

Create a .streamlit/secrets.toml file:

[credentials]
admin = "your\sha256\hashed\_password"


To generate a SHA-256 hash of your password in Python:

import hashlib
print(hashlib.sha256("your\_password".encode()).hexdigest())

Add your data files

Place the following files in the root directory:

project\summary\v2.csv
sudan\_admin2.geojson
United-Nations\_logo.webp

Run the app

streamlit run app.py


Data Format

The CSV file must contain the following columns:

ChfProjectCode — Unique project code
ProjectTitle — Full project title
OrganizationName — Implementing agency name
ActualStartDate — Project start date (e.g. 10-Apr-14)
ActualEndDate — Project end date (e.g. 31-Mar-15)
ProjectStatus — Status (Ongoing, Completed, Pipeline, Cancelled)
Cluster — Sector or intervention type
AdminLocation1 — State name
AdmLoc2 — Locality name
Lat\_Admin2 — Latitude at locality level
Lon\_Admin2 — Longitude at locality level
Budget — Project budget in USD

AI Insights

The dashboard supports three analysis modes:

| Mode | Description |
|---|---|
| Simple Summary | Built-in statistical digest, no external dependencies |
| Ollama (Llama 3.2) | Local LLM via Ollama |
| Ollama (Mistral) | Local LLM via Ollama |

To use Ollama, install it from ollama.com and run:

ollama serve
ollama pull llama3.2


Project Structure

sudan-intervention-dashboard/
├── app.py
├── project\summary\v2.csv
├── sudan\_admin2.geojson
├── United-Nations\_logo.webp
├── requirements.txt
└── .streamlit/
    └── secrets.toml


Notes

Date formats like Sept (instead of Sep) are handled automatically using format='mixed'
The map boundary layer is loaded from a local GeoJSON file and is independent of the active filters
All filters update the map, metrics, table, and AI summary dynamically

License

This project is intended for internal use by the Durable Solutions Unit. Please contact the repository owner for licensing information.
