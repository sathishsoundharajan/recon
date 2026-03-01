# Recon Project

**Author:** Sathish Kumar Soundharajan

This repository contains the Recon backend API (Python) and the Recon Dashboard frontend (Node.js).

## Backend (Python)
The backend is a FastAPI application that provides chat capabilities using PandasAI and Ollama. It relies on `uv` for dependency management.

### Prerequisites
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- Ollama running locally (with the `llama3.1:8b` model)

### Setup & Run
1. Install dependencies:
   ```bash
   uv sync
   ```
2. Run the server:
   ```bash
   uv run chat_server.py
   ```
   Or using uvicorn directly:
   ```bash
   uv run uvicorn chat_server:app --reload
   ```

The API will be available at `http://localhost:8000`.

### Running the Reconciliation Engine
1. Place the invoice Excel file in the `invoice/` directory and ensure `source/do_details_v1.csv` and `source/charge_types.csv` exist.
2. Update the `INVOICE_PATH` in `reconciler.py` if necessary.
3. Run the script:
   ```bash
   uv run reconciler.py
   ```
4. This will generate a file named `recon_final_v2.csv` in the root directory.

### Updating the Dashboard Data
To use the newly generated data in the dashboard:
1. Move the generated CSV to the dashboard's public directory:
   ```bash
   mv recon_final_v2.csv recon-dashboard/public/
   ```
2. The Chat API and dashboard will now use this updated context.

## Frontend (Node.js)
The frontend is a React application built with Vite and Tailwind CSS.

### Prerequisites
- Node.js (v18+ recommended)
- npm or yarn

### Setup & Run
1. Navigate to the dashboard directory:
   ```bash
   cd recon-dashboard
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```

The frontend will be available at the URL provided by Vite (typically `http://localhost:5173`).
