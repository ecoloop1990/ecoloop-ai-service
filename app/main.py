"""
FastAPI application for waste material detection and carbon footprint calculation.
"""
import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Dict, List

import uvicorn
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse

from app.carbon_math import CarbonCalculator
from app.model_loader import ModelLoader

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Ecoloop AI Service",
    description="AI inference service for waste material detection and carbon footprint calculation",
    version="1.0.0",
)

# Global model and calculator instances (loaded at startup)
model_loader: ModelLoader = None
carbon_calculator: CarbonCalculator = None

# Configuration
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
INFERENCE_TIMEOUT = 3.0  # seconds


@app.on_event("startup")
async def startup_event():
    """Initialize model and calculator at application startup."""
    global model_loader, carbon_calculator

    try:
        logger.info("Starting up Ecoloop AI Service...")
        
        # Load model
        model_path = Path("best.pt")
        if not model_path.exists():
            logger.warning(
                f"Model file 'best.pt' not found. Service will start but model will not be available."
            )
            # model_loader will remain None, service will be degraded
        else:
            try:
                model_loader = ModelLoader(model_path=str(model_path))
                logger.info("Model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                # model_loader will remain None
        
        # Initialize carbon calculator (this should always work)
        try:
            carbon_calculator = CarbonCalculator(carbon_factors_path="carbon_factors.json")
            logger.info("Carbon calculator initialized")
        except Exception as e:
            logger.error(f"Failed to initialize carbon calculator: {e}")
            # Create with defaults
            carbon_calculator = CarbonCalculator()
        
        logger.info("Service startup complete")
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        # Don't raise - let the service start but it will fail on first request
        # This allows health checks to pass even if model loading fails


@app.get("/health")
async def health_check():
    """
    Health check endpoint for Kubernetes liveness/readiness probes.
    """
    health_status = {
        "status": "healthy",
        "model_loaded": model_loader.is_loaded() if model_loader else False,
    }
    
    status_code = 200
    if not health_status["model_loaded"]:
        health_status["status"] = "degraded"
        status_code = 503  # Service Unavailable
    
    return JSONResponse(content=health_status, status_code=status_code)


@app.post("/analyze")
async def analyze_image(file: UploadFile = File(...)):
    """
    Analyze uploaded image for waste materials and calculate carbon footprint.

    Args:
        file: Uploaded image file

    Returns:
        JSON response with detection results and carbon footprint
    """
    # Validate file type
    if not file.filename:
        logger.warning("No filename provided")
        return JSONResponse(
            status_code=400,
            content={"error": "No file provided"},
        )
    
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        logger.warning(f"Invalid file type: {file_ext}")
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"},
        )

    # Validate file size
    file_content = await file.read()
    if len(file_content) > MAX_UPLOAD_SIZE:
        logger.warning(f"File too large: {len(file_content)} bytes")
        return JSONResponse(
            status_code=400,
            content={"error": f"File too large. Maximum size: {MAX_UPLOAD_SIZE / 1024 / 1024}MB"},
        )

    # Check if model is loaded
    if not model_loader or not model_loader.is_loaded():
        logger.error("Model not loaded")
        return JSONResponse(
            status_code=503,
            content={"error": "Model not available. Service is degraded."},
        )

    # Save uploaded file to temporary location
    temp_file = None
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_file.write(file_content)
            temp_path = temp_file.name

        logger.info(f"Processing image: {file.filename} ({len(file_content)} bytes)")

        # Run inference with timeout
        try:
            detected_items = await asyncio.wait_for(
                asyncio.to_thread(model_loader.predict, temp_path),
                timeout=INFERENCE_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.error(f"Inference timeout after {INFERENCE_TIMEOUT} seconds")
            return JSONResponse(
                status_code=504,
                content={"error": "Inference timeout. Request took too long."},
            )
        except Exception as e:
            logger.error(f"Inference error: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"error": "Inference failed. Please try again."},
            )

        # Calculate carbon footprint
        try:
            carbon_result = carbon_calculator.calculate_carbon_footprint(detected_items)
        except Exception as e:
            logger.error(f"Carbon calculation error: {e}", exc_info=True)
            # Default to zero values if calculation fails
            carbon_result = {
                "total_weight": 0.0,
                "total_carbon_footprint": 0.0,
                "material_breakdown": {},
            }

        # Build response
        response = {
            "total_weight": carbon_result["total_weight"],
            "total_carbon_footprint": carbon_result["total_carbon_footprint"],
            "detected_items": detected_items,
            "material_breakdown": carbon_result["material_breakdown"],
        }

        logger.info(
            f"Analysis complete: {len(detected_items)} items detected, "
            f"weight={carbon_result['total_weight']}kg, "
            f"carbon={carbon_result['total_carbon_footprint']}"
        )

        return JSONResponse(content=response)

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )
    finally:
        # Clean up temporary file
        if temp_file and Path(temp_path).exists():
            try:
                Path(temp_path).unlink()
            except Exception as e:
                logger.warning(f"Failed to delete temp file: {e}")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )

