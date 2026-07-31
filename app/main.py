"""
FastAPI application for waste material detection and carbon footprint calculation.
"""
import asyncio
import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, List

import uvicorn
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.carbon_math import CarbonCalculator
from app.model_loader import ModelLoader

# Configure structured logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Ecoloop AI Service",
    description="AI inference service for waste material detection and carbon footprint calculation",
    version="2.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on your backend service domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model and calculator instances (loaded at startup)
model_loader: ModelLoader = None
carbon_calculator: CarbonCalculator = None

# Configuration
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
INFERENCE_TIMEOUT = 30.0  # seconds


@app.on_event("startup")
async def startup_event():
    """Initialize model and calculator at application startup."""
    global model_loader, carbon_calculator

    try:
        logger.info("Starting up Ecoloop AI Service v2.0...")
        
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
                logger.error(f"Failed to load model: {e}", exc_info=True)
                # model_loader will remain None
        
        # Initialize carbon calculator (this should always work)
        try:
            carbon_calculator = CarbonCalculator(carbon_factors_path="carbon_factors.json")
            logger.info("Carbon calculator initialized")
        except Exception as e:
            logger.error(f"Failed to initialize carbon calculator: {e}", exc_info=True)
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
    try:
        health_status = {
            "status": "healthy",
            "model_loaded": model_loader.is_loaded() if model_loader else False,
        }
        
        status_code = 200
        if not health_status["model_loaded"]:
            health_status["status"] = "degraded"
            status_code = 503  # Service Unavailable
        
        return JSONResponse(content=health_status, status_code=status_code)
    except Exception as e:
        logger.error(f"Health check error: {e}", exc_info=True)
        return JSONResponse(
            content={"status": "unhealthy", "error": str(e)},
            status_code=503,
        )


@app.post("/analyze")
async def analyze_image(file: UploadFile = File(...)):
    """
    Analyze uploaded image for waste materials and calculate carbon footprint.

    Args:
        file: Uploaded image file

    Returns:
        JSON response with detection results and carbon footprint
    """
    temp_path = None
    
    try:
        # Validate file is provided
        if not file or not file.filename:
            logger.warning("No file provided in request")
            return JSONResponse(
                status_code=400,
                content={"error": "No file provided. Please upload an image file."},
            )
        
        # Validate file type
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            logger.warning(f"Invalid file type: {file_ext}")
            return JSONResponse(
                status_code=400,
                content={"error": f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"},
            )

        # Validate file size
        file_content = await file.read()
        if len(file_content) == 0:
            logger.warning("Empty file provided")
            return JSONResponse(
                status_code=400,
                content={"error": "File is empty. Please provide a valid image file."},
            )
        
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

        # Check if carbon calculator is initialized
        if not carbon_calculator:
            logger.error("Carbon calculator not initialized")
            return JSONResponse(
                status_code=503,
                content={"error": "Carbon calculator not available. Service is degraded."},
            )

        # Save uploaded file to temporary location
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
                temp_file.write(file_content)
                temp_path = temp_file.name
        except Exception as e:
            logger.error(f"Failed to save temporary file: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to process file. Please try again."},
            )

        logger.info(f"Processing image: {file.filename} ({len(file_content)} bytes)")

        # Run inference with timeout
        detected_items = []
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
            import traceback

            logger.error(traceback.format_exc())

            return JSONResponse(
                status_code=500,
                content={"error": str(e)},
            )

        # Calculate carbon footprint
        try:
            carbon_result = carbon_calculator.calculate_carbon_footprint(detected_items)
        except Exception as e:
            logger.error(f"Carbon calculation error: {e}", exc_info=True)
            # Default to zero values if calculation fails - never crash
            carbon_result = {
                "detected_items": [],
                "total_weight": 0.0,
                "total_carbon_footprint": 0.0,
            }
            logger.warning("Using default values due to carbon calculation error")

        # Build response in v2.0 format
        response = {
            "detected_items": carbon_result["detected_items"],
            "total_weight": carbon_result["total_weight"],
            "total_carbon_footprint": carbon_result["total_carbon_footprint"],
        }

        logger.info(
            f"Analysis complete: {len(detected_items)} items detected, "
            f"weight={carbon_result['total_weight']}kg, "
            f"carbon={carbon_result['total_carbon_footprint']}"
        )

        return JSONResponse(content=response)

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        # Never crash - return error response
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error. Please try again."},
        )
    finally:
        # Clean up temporary file
        if temp_path and Path(temp_path).exists():
            try:
                Path(temp_path).unlink()
                logger.debug(f"Cleaned up temporary file: {temp_path}")
            except Exception as e:
                logger.warning(f"Failed to delete temp file {temp_path}: {e}")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        log_level=log_level.lower(),
    )
