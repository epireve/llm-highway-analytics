# JalanOw Analytics API

A FastAPI-based service for scraping, storing, and serving CCTV images from Malaysian highways, with PocketBase database integration.

## Features

- Automated image scraping at configurable intervals
- PocketBase database integration for metadata storage
- CORS-friendly API endpoints
- Image storage and management
- Error handling and retry mechanism
- Comprehensive logging

## Project Structure

- `/app` - FastAPI application code
- `/pocketbase` - PocketBase database server
- `/storage` - Image and metadata storage
- `/.venv` - Python virtual environment

## Prerequisites

- Python 3.10+ 
- PocketBase executable in the `/pocketbase` directory
- Virtual environment (recommended)

## Environment Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd jalanow-analytics
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables (copy from example and modify):
   ```bash
   cp .env.example .env
   ```

5. Edit `.env` with your configuration:
   ```bash
   POCKETBASE_URL=http://127.0.0.1:8090
   POCKETBASE_ADMIN_EMAIL=your_email@example.com
   POCKETBASE_ADMIN_PASSWORD=YourSecurePassword
   SCRAPE_INTERVAL_MINUTES=5
   ```

## Database Setup

1. Start PocketBase server:
   ```bash
   cd pocketbase
   ./pocketbase serve --http="127.0.0.1:8090"
   ```

2. On first run, open the PocketBase admin UI at http://127.0.0.1:8090/_/ and create an admin account with the same credentials specified in your `.env` file.

3. Create the following collections with their respective fields:

   - **highways**
     - code (text, required, unique)
     - name (text, required)
     - highway_id (text, required)

   - **cameras**
     - camera_id (text, required)
     - name (text, required)
     - location_id (text, required)
     - highway (relation to highways, required)

   - **camera_images**
     - camera (relation to cameras, required)
     - image_path (text, required)
     - capture_time (date, required)
     - file_size (number, required)

4. Alternatively, you can use our helper script to set up PocketBase:
   ```bash
   chmod +x init_pocketbase.sh
   ./init_pocketbase.sh
   ```

## Running the Application

### Quick Start (Both Services)
```bash
./run_services.sh
```
This script starts both PocketBase and FastAPI application.

### Separate Services

1. Start PocketBase (in one terminal):
   ```bash
   cd pocketbase && ./pocketbase serve --http="127.0.0.1:8090"
   ```

2. Start FastAPI (in another terminal):
   ```bash
   source .venv/bin/activate
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
   ```

## API Endpoints

- `GET /highways` - List all highways with camera data
- `GET /highway/{highway_code}` - Get data for a specific highway
- `GET /cameras` - List all cameras
- `GET /images/{camera_id}` - Get recent images for a specific camera
- `GET /static/{filename}` - Access stored images

## Troubleshooting

- Check `scraper.log` for detailed error messages and debugging information
- Ensure PocketBase is running before starting the FastAPI application
- Verify the correct admin credentials are set in `.env`
- Make sure the required collections exist in PocketBase

## Development

To set up a development environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
``` 