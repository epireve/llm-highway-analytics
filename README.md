# JalanOw Analytics API

A FastAPI-based service for scraping and serving CCTV images from Malaysian highways.

## Features

- Automated image scraping every 3 minutes
- CORS-friendly API endpoints
- Image storage and management
- Error handling and retry mechanism
- Comprehensive logging

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python run.py
```

## API Endpoints

- `GET /locations` - List all active CCTV locations
- `GET /images/{location_id}` - Get recent images for a specific location

## Configuration

The application is configured to:
- Store images in `storage/images/`
- Log to `scraper.log`
- Run on port 8000

## Error Handling

The application includes:
- Automatic retry mechanism
- Error logging
- Status tracking for each image fetch
- CORS issue handling through server-side requests 