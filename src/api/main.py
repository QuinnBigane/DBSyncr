"""
FastAPI Main Application
"""
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from typing import Optional, Dict, Any, List
import os
from pathlib import Path
import shutil
from datetime import datetime

from src.config.settings import settings
from src.services.data_service import DataService
from src.models.data_models import (
    HealthResponse, ErrorResponse, UploadResponse, ExportRequest, ExportResponse, 
    UnmatchedAnalysis, FieldMappingsConfig
)
from src.utils.exceptions import (
    DataValidationError, FileNotFoundError as CustomFileNotFoundError, 
    DataProcessingError, MappingError
)
from src.utils.logging_config import get_logger

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API for UPS Data Manager - NetSuite and Shopify data synchronization",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize logger
logger = get_logger("FastAPI")

# Global data service instance
data_service: Optional[DataService] = None


def get_data_service() -> DataService:
    """Dependency to get data service instance."""
    global data_service
    if data_service is None:
        data_service = DataService()
    return data_service


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    global data_service
    try:
        data_service = DataService()
        # Try to load data on startup
        data_service.load_data_from_files()
        logger.info("FastAPI application started successfully")
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("FastAPI application shutting down")


@app.exception_handler(DataValidationError)
async def data_validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(message=str(exc)).dict()
    )


@app.exception_handler(CustomFileNotFoundError)
async def file_not_found_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=ErrorResponse(message=str(exc)).dict()
    )


@app.exception_handler(DataProcessingError)
async def data_processing_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(message=str(exc)).dict()
    )


@app.exception_handler(MappingError)
async def mapping_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(message=str(exc)).dict()
    )


# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        services_status={"data_service": "healthy"}
    )


# Data endpoints
@app.get(f"{settings.api_prefix}/data/summary")
async def get_data_summary(service: DataService = Depends(get_data_service)):
    """Get summary of all loaded data."""
    try:
        summary = service.get_data_summary()
        return {"success": True, "data": summary}
    except Exception as e:
        logger.error(f"Failed to get data summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(f"{settings.api_prefix}/data/upload/db1", response_model=UploadResponse)
async def upload_db1_file(
    file: UploadFile = File(...),
    service: DataService = Depends(get_data_service)
):
    """Upload Database 1 data file."""
    return await _handle_file_upload(file, "db1", service)


@app.post(f"{settings.api_prefix}/data/upload/db2", response_model=UploadResponse)
async def upload_db2_file(
    file: UploadFile = File(...),
    service: DataService = Depends(get_data_service)
):
    """Upload Database 2 data file."""
    return await _handle_file_upload(file, "db2", service)


async def _handle_file_upload(file: UploadFile, data_type: str, service: DataService):
    """Handle file upload for database files."""
    try:
        # Validate file type
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in settings.allowed_file_types:
            raise DataValidationError(f"Unsupported file type: {file_extension}")
        
        # Check file size
        if file.size > settings.max_upload_size:
            raise DataValidationError(f"File too large. Maximum size: {settings.max_upload_size / (1024*1024):.1f}MB")
        
        # Save uploaded file
        input_dir = Path(settings.input_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{data_type}_{timestamp}{file_extension}"
        file_path = input_dir / filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Load data based on type
        if data_type == "db1":
            service.load_data_from_files(db1_file=str(file_path))
        elif data_type == "db2":
            service.load_data_from_files(db2_file=str(file_path))
        
        return UploadResponse(
            success=True,
            message=f"{data_type.upper()} file uploaded and processed successfully",
            filename=filename,
            file_path=str(file_path)
        )
        
    except Exception as e:
        logger.error(f"File upload failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get(f"{settings.api_prefix}/data/db1")
async def get_db1_data(
    page: int = 1,
    limit: int = 100,
    service: DataService = Depends(get_data_service)
):
    """Get Database 1 data with pagination."""
    try:
        if service.db1_data is None:
            raise DataProcessingError("Database 1 data not loaded")
        
        # Calculate pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        
        total_records = len(service.db1_data)
        data_slice = service.db1_data.iloc[start_idx:end_idx]
        
        return {
            "success": True,
            "data": data_slice.to_dict('records'),
            "pagination": {
                "page": page,
                "limit": limit,
                "total_records": total_records,
                "total_pages": (total_records + limit - 1) // limit
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get Database 1 data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(f"{settings.api_prefix}/data/db2")
async def get_db2_data(
    page: int = 1,
    limit: int = 100,
    service: DataService = Depends(get_data_service)
):
    """Get Database 2 data with pagination."""
    try:
        if service.db2_data is None:
            raise DataProcessingError("Database 2 data not loaded")
        
        # Calculate pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        
        total_records = len(service.db2_data)
        data_slice = service.db2_data.iloc[start_idx:end_idx]
        
        return {
            "success": True,
            "data": data_slice.to_dict('records'),
            "pagination": {
                "page": page,
                "limit": limit,
                "total_records": total_records,
                "total_pages": (total_records + limit - 1) // limit
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get Database 2 data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(f"{settings.api_prefix}/data/combined")
async def get_combined_data(
    page: int = 1,
    limit: int = 100,
    service: DataService = Depends(get_data_service)
):
    """Get combined data with pagination."""
    try:
        if service.combined_data is None:
            raise DataProcessingError("Combined data not available")
        
        # Calculate pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        
        total_records = len(service.combined_data)
        data_slice = service.combined_data.iloc[start_idx:end_idx]
        
        return {
            "success": True,
            "data": data_slice.to_dict('records'),
            "pagination": {
                "page": page,
                "limit": limit,
                "total_records": total_records,
                "total_pages": (total_records + limit - 1) // limit
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get combined data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Analysis endpoints
@app.get(f"{settings.api_prefix}/analysis/unmatched", response_model=UnmatchedAnalysis)
async def get_unmatched_analysis(service: DataService = Depends(get_data_service)):
    """Get analysis of unmatched items between NetSuite and Shopify."""
    try:
        analysis = service.get_unmatched_analysis()
        return analysis
    except Exception as e:
        logger.error(f"Failed to get unmatched analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Field mappings endpoints
@app.get(f"{settings.api_prefix}/mappings")
async def get_field_mappings(service: DataService = Depends(get_data_service)):
    """Get current field mappings configuration."""
    try:
        mappings = service.get_field_mappings()
        return {"success": True, "data": mappings}
    except Exception as e:
        logger.error(f"Failed to get field mappings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put(f"{settings.api_prefix}/mappings")
async def update_field_mappings(
    mappings: Dict[str, Any],
    service: DataService = Depends(get_data_service)
):
    """Update field mappings configuration."""
    try:
        success = service.update_field_mappings(mappings)
        if success:
            return {"success": True, "message": "Field mappings updated successfully"}
        else:
            raise DataProcessingError("Failed to update field mappings")
    except Exception as e:
        logger.error(f"Failed to update field mappings: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# Export endpoints
@app.post(f"{settings.api_prefix}/export", response_model=ExportResponse)
async def export_data(
    request: ExportRequest,
    service: DataService = Depends(get_data_service)
):
    """Export data to file."""
    try:
        file_path = service.export_data(
            data_type=request.data_type,
            format=request.format,
            file_path=request.filename
        )
        
        return ExportResponse(
            success=True,
            message="Data exported successfully",
            file_path=file_path,
            file_size=os.path.getsize(file_path) if os.path.exists(file_path) else None
        )
        
    except Exception as e:
        logger.error(f"Failed to export data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(f"{settings.api_prefix}/export/download/{{filename}}")
async def download_file(filename: str):
    """Download exported file."""
    try:
        exports_dir = Path(settings.exports_dir)
        file_path = exports_dir / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type='application/octet-stream'
        )
        
    except Exception as e:
        logger.error(f"Failed to download file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Record update endpoints
@app.put(f"{settings.api_prefix}/data/{{data_type}}/record/{{record_index}}")
async def update_record(
    data_type: str,
    record_index: int,
    updates: Dict[str, Any],
    service: DataService = Depends(get_data_service)
):
    """Update a specific record."""
    try:
        success = service.update_record(data_type, record_index, updates)
        if success:
            return {"success": True, "message": "Record updated successfully"}
        else:
            raise DataProcessingError("Failed to update record")
    except Exception as e:
        logger.error(f"Failed to update record: {e}")
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )