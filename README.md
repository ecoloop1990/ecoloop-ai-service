# Ecoloop AI Service

Production-ready FastAPI microservice for waste material detection and carbon footprint calculation using YOLOv8.

## Features

- 🎯 YOLOv8-based waste material detection
- 📊 Carbon footprint calculation
- 🚀 Preloaded model for fast inference
- 🐳 Docker containerization
- ☸️ Kubernetes-ready
- ⚡ Async endpoints with timeout handling
- 🏥 Health check endpoint
- 📝 Structured logging

## Project Structure

```
ecoloop-ai-service/
  app/
    main.py              # FastAPI application
    model_loader.py      # YOLOv8 model loading
    carbon_math.py       # Carbon footprint calculations
  best.pt                # YOLOv8 model file (required)
  carbon_factors.json    # Carbon factors configuration
  requirements.txt       # Python dependencies
  Dockerfile             # Container definition
```

## Setup

### Prerequisites

- Python 3.10+
- YOLOv8 model file (`best.pt`) - must be provided
- Docker (for containerization)

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure `best.pt` model file is in the root directory

3. Run the service:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Docker

1. Build the image:
```bash
docker build -t ecoloop-ai-service .
```

2. Run the container:
```bash
docker run -p 8000:8000 ecoloop-ai-service
```

## API Endpoints

### POST /analyze

Analyze an uploaded image for waste materials.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Field name: `file`
- Max file size: 10MB
- Allowed formats: JPG, JPEG, PNG, BMP, TIFF, WEBP

**Response:**
```json
{
  "total_weight": 0.125,
  "total_carbon_footprint": 0.375,
  "detected_items": ["plastic", "metal", "plastic"],
  "material_breakdown": {
    "plastic": 2,
    "metal": 1
  }
}
```

**Error Response:**
```json
{
  "error": "Error message"
}
```

### GET /health

Health check endpoint for Kubernetes probes.

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true
}
```

## Carbon Calculation

The service calculates carbon footprint using:

```
Total Carbon = Object Count × Average Weight × Carbon Factor
```

**Average Weights (kg per item):**
- metal: 0.015
- plastic: 0.025
- glass: 0.200
- cardboard: 0.050

**Carbon Factors:**
Configured in `carbon_factors.json` (default values provided).

## Kubernetes Deployment

The service is designed to run in Kubernetes (EKS) and can be called internally:

```
http://ecoloop-ai-service:8000/analyze
```

- No CORS required (internal traffic)
- No authentication (internal service)
- Stateless design for horizontal scaling
- Health checks at `/health`

## Error Handling

- **400**: Invalid file type or size
- **500**: Inference failure or internal error
- **503**: Model not loaded (service degraded)
- **504**: Inference timeout (>3 seconds)

## Performance

- Model preloaded at startup (no per-request loading)
- Async endpoints for non-blocking operations
- Inference timeout: 3 seconds
- Target latency: <2 seconds

## Notes

- The `best.pt` model file must be provided separately
- Material names are normalized to lowercase
- Unknown materials default to weight 0.01kg and carbon factor 0
- Temporary files are automatically cleaned up after processing

