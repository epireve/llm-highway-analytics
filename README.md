# Highway CCTV Analytics API

A FastAPI-based service for scraping, storing, and serving CCTV images from Malaysian highways, with PocketBase database integration.

## Disclaimer

This project is not officially affiliated with or endorsed by Lembaga Lebuhraya Malaysia (LLM). The CCTV data and images used in this project are owned by [Lembaga Lebuhraya Malaysia (LLM)](https://www.llm.gov.my) and their respective highway concessionaires. This project is for educational and research purposes only.

### Data Attribution
- Data Source: [Lembaga Lebuhraya Malaysia (LLM)](https://www.llm.gov.my)
- All CCTV images and related data are the property of LLM and respective highway operators
- This project does not claim ownership of any data or images

## Features

- Automated image scraping at configurable intervals
- PocketBase database integration for metadata storage
- CORS-friendly API endpoints
- Image storage and management
- Error handling and retry mechanism
- Comprehensive logging
- Smart timestamp parsing (supports ISO, date-only, time-only formats)
- Versioned API endpoints (/api/v1)
- Flexible image filtering and retrieval

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
   git clone https://github.com/epireve/highway-cctv-analytics.git
   cd highway-cctv-analytics
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

### Legacy Endpoints (Still Available)
- `GET /highways` - List all highways with camera data
- `GET /highways/{highway_code}` - Get data for a specific highway
- `GET /cameras` - List all cameras
  - Query parameters:
    - `highway_code` - (Optional) Filter cameras by highway code
- `GET /images` - Get camera images with flexible filtering
  - Query parameters:
    - `highway_code` - (Optional) Filter images by highway code
    - `camera_id` - (Optional) Filter images by camera ID
    - `limit` - (Optional) Limit the number of results (default: 20)
- `GET /health` - API health check
- `GET /static/{filename}` - Access stored images

### Versioned API (v1)
- `GET /api/v1/cameras` - List all available cameras
  - Query parameters:
    - `highway_code` - (Optional) Filter cameras by highway code
    - `limit` - (Optional) Limit the number of results (default: 100, max: 500)

- `GET /api/v1/cameras/{camera_id}/latest` - Get the latest image from a specific camera

- `GET /api/v1/cameras/{camera_id}/images/{timestamp}` - Get a specific image closest to the timestamp
  - Supports flexible timestamp formats:
    - ISO: `2025-03-26T13:30:51`
    - Date only: `2025-03-26` (assumes 00:00:00)
    - Time only: `13:30` (assumes today's date)
    - Hour only: `13` (assumes today's date, 00 minutes)

- `GET /api/v1/cameras/{camera_id}/images` - Get images within a time range
  - Query parameters:
    - `from_time` - (Optional) Start timestamp with flexible format
    - `to_time` - (Optional) End timestamp with flexible format
    - `limit` - (Optional) Maximum number of images to return (default: 20, max: 100)

## Endpoint Examples

### Legacy API Examples
- List all highways:
  ```
  GET /highways
  ```

- Get a specific highway:
  ```
  GET /highways/DUKE
  ```

- Get all cameras:
  ```
  GET /cameras
  ```

- Get cameras for a specific highway:
  ```
  GET /cameras?highway_code=DUKE
  ```

- Get all images (most recent from all cameras):
  ```
  GET /images
  ```

- Get images for a specific highway:
  ```
  GET /images?highway_code=DUKE
  ```

- Get the most recent image for a specific camera:
  ```
  GET /images?camera_id=DUKE-1
  ```

### Versioned API Examples

- List all cameras:
  ```
  GET /api/v1/cameras
  ```

- List cameras for a specific highway:
  ```
  GET /api/v1/cameras?highway_code=DUKE
  ```

- Get the latest image from a camera:
  ```
  GET /api/v1/cameras/DUKE-1/latest
  ```

- Get an image from a specific time (returns the nearest match):
  ```
  GET /api/v1/cameras/DUKE-1/images/13:30
  ```

- Get an image from a specific date:
  ```
  GET /api/v1/cameras/DUKE-1/images/2025-03-26
  ```

- Get images within a time range:
  ```
  GET /api/v1/cameras/DUKE-1/images?from_time=13:00&to_time=14:00
  ```

- Get more images from a time range:
  ```
  GET /api/v1/cameras/DUKE-1/images?from_time=2025-03-26&to_time=2025-03-27&limit=50
  ```

## API Response Formats

### Image Response Format
All endpoints that return image data use this format:
```json
{
  "camera_id": "DUKE-1",
  "camera_name": "DUKE Camera 1",
  "highway_code": "DUKE",
  "highway_name": "Duta-Ulu Kelang Expressway",
  "timestamp": "2025-03-26T13:30:51",
  "image_url": "/static/DUKE_DUKE-1_20250326_133051.jpg",
  "file_size": 12345
}
```

### Health Check Response Format
The health endpoint (`GET /api/v1/health`) returns:
```json
{
  "status": "healthy",
  "storage_dir": "/path/to/storage",
  "storage_exists": true,
  "storage_is_dir": true,
  "active_highways": 15,
  "image_count": 1234
}
```

### Error Response Format
Error responses follow this format:
```json
{
  "detail": "Error message describing what went wrong"
}
```

## Image URLs

Images are served from the `/static` endpoint. The URL format is:
```
/static/{HIGHWAY_CODE}_{CAMERA_ID}_{YYYYMMDD}_{HHMMSS}.jpg
```

Example:
```
/static/DUKE_DUKE-1_20250326_133051.jpg
```

## Troubleshooting

- Check `scraper.log` for detailed error messages and debugging information
- Ensure PocketBase is running before starting the FastAPI application
- Verify the correct admin credentials are set in `.env`
- Make sure the required collections exist in PocketBase
- Check both `fastapi.log` and `pocketbase.log` for service-specific issues
- Verify network connectivity for image scraping
- Ensure proper permissions on storage directories

## Development

To set up a development environment:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

For development best practices:
1. Use the `--reload` flag with uvicorn for auto-reloading
2. Check the OpenAPI docs at `/docs` for testing endpoints
3. Monitor the log files in real-time using `tail -f scraper.log`
4. Use the health endpoint to verify system status

## Legal Notice

This project is provided "as is" without warranty of any kind. Users are responsible for complying with applicable laws and regulations regarding the use of traffic camera data. The developers of this project are not responsible for any misuse of the data or violation of terms of service.

### Usage Restrictions
- Data and images should not be used for commercial purposes without proper authorization from LLM
- Users must comply with Malaysian laws and regulations regarding traffic data usage
- Respect the intellectual property rights of LLM and highway operators