# Enterprise Employee Analytics & Data Warehouse System

## Overview
This is a modern, enterprise-grade Employee Analytics Dashboard and Data Warehouse application. It provides HR managers and executives with self-explanatory KPIs, clear charts, and resource allocation insights. 

The application is built with Python 3.12, Streamlit for the frontend dashboard, and a MySQL 8.0+ backend database using Common Table Expressions (CTEs) and Window functions for complex analytics.

## Prerequisites
- **Python**: 3.12 or newer.
- **Database**: MySQL 8.0 or newer (Required for CTEs and Window functions).
- **OS**: Windows (compatible with others, but optimized/tested for Windows).

## Deployment & Setup Instructions

Follow these steps to host and run the project on a new system:

### 1. Clone the Repository
```powershell
git clone <repository_url>
cd greenfield-employee-dw
```

### 2. Set Up a Virtual Environment
It is highly recommended to use a virtual environment to manage dependencies.
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
Install all required libraries specified in `requirements.txt`.
```powershell
pip install -r requirements.txt
```

### 4. Database Setup
1. Create a new MySQL database for the project.
2. Run the SQL scripts in the `sql/` folder in order (from `01_` to the latest) to set up the schema and load sample data.

### 5. Environment Configuration
1. Copy the `.env.example` file to create your own `.env` file:
```powershell
Copy-Item .env.example .env
```
2. Open `.env` and configure your database connection settings (`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`).

### 6. Verify Database Connection
Run the connection check script to ensure everything is set up correctly:
```powershell
python scripts/check_connection.py
```

### 7. Run Tests
Ensure all components are functioning correctly by running `pytest`.
```powershell
$env:PYTHONPATH='.'
pytest -q
```
*(All tests should pass.)*

### 8. Start the Application
Run the Streamlit dashboard:
```powershell
python -m streamlit run app/app.py
```
The dashboard will open automatically in your default web browser (usually at `http://localhost:8501`).

## Application Structure
- `app/`: Streamlit frontend application (`app.py`, `dashboard.py`, `styles.py`, `db_queries.py`).
- `src/`: Backend logic, database connection pooling (`db_manager.py`), and entity managers.
- `sql/`: SQL scripts for DDL, DML, stored procedures, and triggers.
- `tests/`: Pytest test suite for backend logic and DB management.
- `scripts/`: Utility scripts.
