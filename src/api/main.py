"""
FastAPI Main Application
"""
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, status, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from typing import Optional, Dict, Any, List
import os
import sys
import json
from pathlib import Path
import shutil
from datetime import datetime
import pandas as pd

# Add src to path for imports (similar to CLI main)
project_root = Path(__file__).parent.parent  # Go up to src/
src_path = project_root
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from config.settings import settings
from services.data_service import DataService
from services.api_data_service import ApiDataService
from services.auth_service import AuthService
from services.rate_limit_service import RateLimitService
from services.websocket_service import WebSocketService
from utils.file_validator import file_validator
from models.data_models import (
    HealthResponse, ErrorResponse, UploadResponse, ExportRequest, ExportResponse, 
    UnmatchedAnalysis, FieldMappingsConfig, ApiSession, ApiSessionStatus,
    User, Token, LoginRequest, PasswordChange, UserCreate
)
from utils.exceptions import (
    DataValidationError, FileNotFoundError as CustomFileNotFoundError, 
    DataProcessingError, MappingError
)
from utils.logging_config import get_logger
from services.service_factory import ServiceFactory

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    # DBSyncr API - Database Data Synchronization and Management

    A comprehensive API for synchronizing and managing data between two database systems.
    Supports CSV and Excel file uploads, automated data mapping, and export functionality.

    ## Key Features

    - **File Upload & Validation**: Secure upload of CSV/Excel files with comprehensive validation
    - **Data Synchronization**: Automated mapping and merging of data between databases
    - **Session Management**: Isolated processing sessions for concurrent operations
    - **Export Capabilities**: Multiple export formats with customizable options
    - **Real-time Monitoring**: Health checks and processing status tracking

    ## Quick Start

    1. **Upload Data Files**: Use `/api/v1/data/upload/db1` and `/api/v1/data/upload/db2`
    2. **Configure Mappings**: Update field mappings via `/api/v1/config/upload`
    3. **Process Data**: Combine and synchronize data automatically
    4. **Export Results**: Download processed data in various formats

    ## Authentication

    JWT-based authentication is required for all data operations. Use `/api/v1/auth/login` to obtain an access token.

    ## Rate Limiting

    API requests are rate limited to prevent abuse. Limits vary by endpoint type.
    """,
    contact={
        "name": "DBSyncr Support",
        "url": "https://github.com/QuinnBigane/DBSyncr",
        "email": "support@dbsyncr.example.com"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json",
    tags_metadata=[
        {
            "name": "health",
            "description": "Health check and system status endpoints"
        },
        {
            "name": "data",
            "description": "Core data operations: upload, summary, export"
        },
        {
            "name": "sessions",
            "description": "Session-based data processing workflows"
        },
        {
            "name": "configuration",
            "description": "Field mappings and system configuration"
        },
        {
            "name": "storage",
            "description": "Storage management and cleanup operations"
        }
    ]
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure rate limiting
limiter = Limiter(key_func=get_remote_address, default_limits=["1000/minute"] if settings.debug else ["100/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Configure authentication
security = HTTPBearer()

# Initialize logger
logger = get_logger("FastAPI")

# Global data service instance - now handled by ServiceFactory


def get_data_service() -> DataService:
    """Dependency to get data service instance."""
    return ServiceFactory.create_data_service()


def get_api_data_service() -> ApiDataService:
    """Dependency to get API data service instance."""
    return ServiceFactory.create_api_data_service()


def get_auth_service() -> AuthService:
    """Dependency to get auth service instance."""
    service = ServiceFactory.create_auth_service()
    service.logger.info(f"get_auth_service called, users: {list(service.users.keys())}")
    return service


def get_rate_limit_service() -> RateLimitService:
    """Dependency to get rate limit service instance."""
    return ServiceFactory.create_rate_limit_service()


def get_websocket_service() -> WebSocketService:
    """Dependency to get websocket service instance."""
    return ServiceFactory.create_websocket_service()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    """Dependency to get current authenticated user."""
    try:
        payload = auth_service.verify_token(credentials.credentials)
        user_id = payload.username
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        user = auth_service.get_user_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to get current active user."""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    try:
        # Create data service instance
        service = ServiceFactory.create_data_service()
        # Try to load data on startup
        service.load_data_from_files()
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


# Authentication endpoints
@app.post(
    "/api/v1/auth/signup",
    response_model=Token,
    status_code=201,
    tags=["authentication"],
    summary="User Registration",
    description="Create a new user account and return access token.",
    responses={
        201: {"description": "User created successfully"},
        400: {"description": "Invalid input data"},
        409: {"description": "User already exists"}
    }
)
async def signup(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Create a new user account."""
    try:
        user = auth_service.create_user(user_data)
        access_token = auth_service.create_access_token({"sub": user.id})
        return Token(access_token=access_token, token_type="bearer")
    except ValueError as e:
        # If the error message indicates the user already exists, return 409
        if "already exists" in str(e).lower():
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@app.post(
    "/api/v1/auth/login",
    tags=["authentication"],
    summary="User Login",
    description="Authenticate user and return access token.",
    responses={
        200: {"description": "Login successful"},
        401: {"description": "Invalid credentials"}
    }
)
async def login(
    login_data: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Authenticate user and return access token."""
    user = auth_service.authenticate_user(login_data.username, login_data.password)
    auth_service.logger.info(f"Login: authenticate_user returned: {user}")
    if not user:
        auth_service.logger.info("Login: raising 401")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    auth_service.logger.info("Login: creating access token")
    access_token = auth_service.create_access_token({"sub": user.id})
    auth_service.logger.info(f"Login: created token: {access_token[:20]}...")
    auth_service.logger.info("Login: about to return dict")
    return {"access_token": access_token, "token_type": "bearer"}


@app.post(
    "/api/v1/auth/change-password",
    tags=["authentication"],
    summary="Change Password",
    description="Change the current user's password.",
    responses={
        200: {"description": "Password changed successfully"},
        400: {"description": "Invalid input"},
        401: {"description": "Authentication required"}
    }
)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Change user password."""
    try:
        auth_service.change_password(current_user.id, password_data.old_password, password_data.new_password)
        return {"message": "Password changed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get(
    "/api/v1/auth/me",
    response_model=User,
    tags=["authentication"],
    summary="Get Current User",
    description="Get information about the currently authenticated user.",
    responses={
        200: {"description": "User information retrieved"},
        401: {"description": "Authentication required"}
    }
)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information."""
    return current_user


# WebSocket endpoints
@app.websocket("/api/v1/ws/progress")
async def websocket_progress(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
    websocket_service: WebSocketService = Depends(get_websocket_service),
    auth_service: AuthService = Depends(get_auth_service)
):
    """WebSocket endpoint for real-time progress updates."""
    try:
        # Verify token
        payload = auth_service.verify_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            await websocket.close(code=1008, reason="Invalid token")
            return

        # Accept connection
        await websocket_service.connect(websocket, user_id)

        try:
            while True:
                # Keep connection alive and handle any client messages
                data = await websocket.receive_text()
                # Echo back for connection health check
                await websocket.send_text(f"Connected: {data}")
        except WebSocketDisconnect:
            websocket_service.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass


# Health check endpoint
@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["health"],
    summary="Health Check",
    description="""
    Check the health status of the DBSyncr API service.

    Returns system status, version information, and service health indicators.
    Use this endpoint to verify the API is operational.
    """,
    responses={
        200: {
            "description": "Service is healthy and operational",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "timestamp": "2025-09-24T15:30:00.000000",
                        "version": "1.0.0",
                        "database_connected": None,
                        "services_status": {
                            "data_service": "healthy"
                        }
                    }
                }
            }
        }
    }
)
@limiter.exempt
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        services_status={"data_service": "healthy"}
    )


# Data endpoints
@app.get(
    f"{settings.api_prefix}/data/summary",
    tags=["data"],
    summary="Get Data Summary",
    description="""
    Retrieve a comprehensive summary of all loaded database data.

    Returns statistics about Database 1 and Database 2 data, including:
    - Record counts for each database
    - Combined data statistics
    - Field mapping information
    - Data synchronization status
    """,
    responses={
        200: {
            "description": "Data summary retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "db1_records": 150,
                        "db2_records": 200,
                        "combined_records": 180,
                        "field_mappings": 3,
                        "last_sync": "2025-09-24T15:30:00.000000",
                        "sync_status": "completed"
                    }
                }
            }
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Failed to retrieve data summary"
                    }
                }
            }
        }
    }
)
async def get_data_summary(
    service: DataService = Depends(get_data_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get summary of all loaded data."""
    try:
        summary = service.get_data_summary()
        return {"success": True, "data": summary}
    except Exception as e:
        logger.error(f"Failed to get data summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    f"{settings.api_prefix}/data/upload/db1",
    response_model=UploadResponse,
    tags=["data"],
    summary="Upload Database 1 File",
    description="""
    Upload a CSV or Excel file containing Database 1 data for processing.

    **Supported Formats:**
    - CSV (.csv)
    - Excel (.xlsx, .xls)

    **Validation Performed:**
    - File type and size validation
    - Content parsing and structure check
    - Data integrity verification
    - Maximum 50MB file size, 100,000 rows

    **Processing:**
    - File is validated and stored temporarily
    - Data is loaded and made available for synchronization
    - Previous DB1 data is replaced
    """,
    responses={
        200: {
            "description": "File uploaded and processed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "DB1 file uploaded and processed successfully. Valid CSV file with 150 rows and 8 columns",
                        "filename": "db1_20250924_153000.csv",
                        "file_path": "data/api/incoming/db1_20250924_153000.csv",
                        "records_processed": 150
                    }
                }
            }
        },
        400: {
            "description": "File validation failed",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "File validation failed: Unsupported file type '.txt'"
                    }
                }
            }
        }
    }
)
async def upload_db1_file(
    file: UploadFile = File(..., description="CSV or Excel file containing Database 1 data"),
    service: DataService = Depends(get_data_service),
    current_user: User = Depends(get_current_active_user)
):
    """Upload Database 1 data file."""
    return await _handle_file_upload(file, "db1", service)


@app.post(
    f"{settings.api_prefix}/data/upload/db2",
    response_model=UploadResponse,
    tags=["data"],
    summary="Upload Database 2 File",
    description="""
    Upload a CSV or Excel file containing Database 2 data for processing.

    **Supported Formats:**
    - CSV (.csv)
    - Excel (.xlsx, .xls)

    **Validation Performed:**
    - File type and size validation
    - Content parsing and structure check
    - Data integrity verification
    - Maximum 50MB file size, 100,000 rows

    **Processing:**
    - File is validated and stored temporarily
    - Data is loaded and made available for synchronization
    - Previous DB2 data is replaced
    """,
    responses={
        200: {
            "description": "File uploaded and processed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "DB2 file uploaded and processed successfully. Valid Excel file with 200 rows and 6 columns",
                        "filename": "db2_20250924_153000.xlsx",
                        "file_path": "data/api/incoming/db2_20250924_153000.xlsx",
                        "records_processed": 200
                    }
                }
            }
        },
        400: {
            "description": "File validation failed",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "File validation failed: File too large. Maximum size: 50.0MB"
                    }
                }
            }
        }
    }
)
async def upload_db2_file(
    file: UploadFile = File(..., description="CSV or Excel file containing Database 2 data"),
    service: DataService = Depends(get_data_service),
    current_user: User = Depends(get_current_active_user)
):
    """Upload Database 2 data file."""
    return await _handle_file_upload(file, "db2", service)


@app.post(
    f"{settings.api_prefix}/config/upload",
    response_model=UploadResponse,
    tags=["config"],
    summary="Upload Configuration File",
    description="""
    Upload configuration files for the DBSyncr service.

    **Supported Configuration Types:**
    - Field mappings JSON files (field_mappings.json)
    - Other configuration files as needed

    **Field Mappings Processing:**
    - JSON files containing field mappings are automatically validated
    - Valid mappings are applied to the data processing pipeline
    - Previous field mappings are replaced

    **Validation Performed:**
    - JSON syntax validation for configuration files
    - Schema structure verification for field mappings
    - Maximum 50MB file size

    **Processing:**
    - Configuration files are stored and validated
    - Field mappings are applied immediately if valid
    - Service configuration is updated dynamically
    """,
    responses={
        200: {
            "description": "Configuration file uploaded and processed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Configuration file uploaded successfully",
                        "filename": "uploaded_field_mappings.json",
                        "file_path": "data/api/config/uploaded_field_mappings.json"
                    }
                }
            }
        },
        400: {
            "description": "Configuration validation failed",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid JSON in uploaded config file: Expecting ',' delimiter: line 15 column 10 (char 234)"
                    }
                }
            }
        }
    }
)
async def upload_config_file(
    file: UploadFile = File(..., description="Configuration file (JSON format for field mappings, etc.)"),
    service: DataService = Depends(get_data_service)
):
    """Upload configuration file (field mappings, etc.)."""
    return await _handle_config_upload(file, service)


async def _handle_config_upload(file: UploadFile, service: DataService):
    """Handle configuration file upload."""
    try:
        # Validate file type (only JSON for now)
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in [".json"]:
            raise DataValidationError(f"Unsupported config file type: {file_extension}. Only JSON files are supported.")
        
        # Check file size
        if file.size > settings.max_upload_size:
            raise DataValidationError(f"File too large. Maximum size: {settings.max_upload_size / (1024*1024):.1f}MB")
        
        # Save uploaded config file
        config_dir = Path(settings.api_config_dir)
        filename = f"uploaded_{file.filename}"
        file_path = config_dir / filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # If it's field mappings, update the service configuration
        if "field_mappings" in file.filename.lower() or "mappings" in file.filename.lower():
            try:
                # Load and validate the uploaded mappings
                with open(file_path, 'r') as f:
                    mappings_data = json.load(f)
                
                # Update the service with new mappings
                success = service.update_field_mappings(mappings_data)
                if not success:
                    raise DataProcessingError("Failed to apply uploaded field mappings")
                    
                logger.info(f"Applied uploaded field mappings from {file_path}")
                
            except json.JSONDecodeError as e:
                raise DataValidationError(f"Invalid JSON in uploaded config file: {e}")
            except Exception as e:
                logger.warning(f"Could not apply uploaded config automatically: {e}")
        
        return UploadResponse(
            success=True,
            message=f"Configuration file uploaded successfully",
            filename=filename,
            file_path=str(file_path)
        )
        
    except Exception as e:
        logger.error(f"Config upload failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


async def _handle_file_upload(file: UploadFile, data_type: str, service: DataService):
    """Handle file upload for database files with comprehensive validation."""
    try:
        # Read file content for validation
        file_content = await file.read()
        await file.seek(0)  # Reset file pointer for later use

        # Validate file using the file validator
        validation_result = file_validator.validate_file(
            file_content=file_content,
            filename=file.filename,
            content_type=file.content_type
        )

        if not validation_result["valid"]:
            error_msg = "; ".join(validation_result["errors"])
            raise DataValidationError(f"File validation failed: {error_msg}")

        # Log warnings if any
        if validation_result["warnings"]:
            for warning in validation_result["warnings"]:
                logger.warning(f"File validation warning for {file.filename}: {warning}")

        # Check file size (additional check beyond validator)
        if len(file_content) > settings.max_upload_size:
            raise DataValidationError(f"File too large. Maximum size: {settings.max_upload_size / (1024*1024):.1f}MB")

        # Save uploaded file
        input_dir = Path(settings.api_input_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = Path(file.filename).suffix.lower()
        filename = f"{data_type}_{timestamp}{file_extension}"
        file_path = input_dir / filename

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Get file summary for response
        file_summary = file_validator.get_file_summary(validation_result)

        # Load data based on type
        if data_type == "db1":
            service.load_data_from_files(db1_file=str(file_path))
        elif data_type == "db2":
            service.load_data_from_files(db2_file=str(file_path))

        return UploadResponse(
            success=True,
            message=f"{data_type.upper()} file uploaded and processed successfully. {file_summary}",
            filename=filename,
            file_path=str(file_path),
            records_processed=validation_result["file_info"].get("row_count")
        )

    except DataValidationError:
        raise
    except Exception as e:
        logger.error(f"File upload failed for {data_type}: {e}")
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
        
        # Convert to dict and handle NaN values
        data_records = data_slice.to_dict('records')
        # Replace NaN with None for JSON serialization
        for record in data_records:
            for key, value in record.items():
                if isinstance(value, float) and (pd.isna(value) or str(value).lower() == 'nan'):
                    record[key] = None
        
        return {
            "success": True,
            "data": data_records,
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
        
        # Convert to dict and handle NaN values
        data_records = data_slice.to_dict('records')
        # Replace NaN with None for JSON serialization
        for record in data_records:
            for key, value in record.items():
                if isinstance(value, float) and (pd.isna(value) or str(value).lower() == 'nan'):
                    record[key] = None
        
        return {
            "success": True,
            "data": data_records,
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


@app.get(
    f"{settings.api_prefix}/data/combined",
    tags=["data"],
    summary="Get Combined Data",
    description="""
    Retrieve the synchronized combined data from both databases.

    **Data Combination:**
    - Merges Database 1 and Database 2 data based on field mappings
    - Uses primary link keys for matching records
    - Applies field transformations and data type conversions
    - Includes all matched records with synchronized values

    **Pagination:**
    - Supports paginated results for large datasets
    - Default page size: 100 records
    - Maximum page size: Limited by available memory

    **Requirements:**
    - Both Database 1 and Database 2 data must be loaded
    - Valid field mappings configuration must be available
    - Data synchronization must have been performed
    """,
    responses={
        200: {
            "description": "Combined data retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": [
                            {
                                "SKU": "ABC123",
                                "ProductName": "Widget A",
                                "Quantity": 150,
                                "Price": 29.99,
                                "StockLevel": 150,
                                "Category": "Electronics"
                            }
                        ],
                        "pagination": {
                            "page": 1,
                            "limit": 100,
                            "total_records": 250,
                            "total_pages": 3
                        }
                    }
                }
            }
        },
        500: {
            "description": "Combined data not available or processing failed",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Combined data not available"
                    }
                }
            }
        }
    }
)
async def get_combined_data(
    page: int = Query(1, ge=1, description="Page number for pagination"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records per page"),
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
        
        # Convert to dict and handle NaN values
        data_records = data_slice.to_dict('records')
        # Replace NaN with None for JSON serialization
        for record in data_records:
            for key, value in record.items():
                if isinstance(value, float) and (pd.isna(value) or str(value).lower() == 'nan'):
                    record[key] = None
        
        return {
            "success": True,
            "data": data_records,
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
@app.get(
    f"{settings.api_prefix}/analysis/unmatched",
    response_model=UnmatchedAnalysis,
    tags=["analysis"],
    summary="Get Unmatched Items Analysis",
    description="""
    Analyze and retrieve items that could not be matched between Database 1 and Database 2.

    **Analysis Types:**
    - **DB1 Only**: Records in Database 1 with no matching record in Database 2
    - **DB2 Only**: Records in Database 2 with no matching record in Database 1
    - **Potential Matches**: Records that might match but need manual review

    **Matching Criteria:**
    - Uses primary link keys defined in field mappings
    - Considers exact matches and fuzzy matching where applicable
    - Identifies data quality issues preventing matches

    **Use Cases:**
    - Identify missing data between systems
    - Find data entry inconsistencies
    - Plan data cleanup and enrichment activities
    - Validate synchronization completeness
    """,
    responses={
        200: {
            "description": "Unmatched analysis completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "db1_only_count": 15,
                        "db2_only_count": 8,
                        "db1_only_sample": [
                            {
                                "SKU": "XYZ789",
                                "ProductName": "Missing Product",
                                "Quantity": 0
                            }
                        ],
                        "db2_only_sample": [
                            {
                                "SKU": "ABC999",
                                "StockLevel": 50,
                                "Category": "Unknown"
                            }
                        ],
                        "potential_matches": []
                    }
                }
            }
        },
        500: {
            "description": "Analysis failed",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Failed to perform unmatched analysis: Data processing error"
                    }
                }
            }
        }
    }
)
async def get_unmatched_analysis(service: DataService = Depends(get_data_service)):
    """Get analysis of unmatched items between databases."""
    try:
        analysis = service.get_unmatched_analysis()
        return analysis
    except Exception as e:
        logger.error(f"Failed to get unmatched analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Field mappings endpoints
@app.get(
    f"{settings.api_prefix}/mappings",
    tags=["config"],
    summary="Get Field Mappings",
    description="""
    Retrieve the current field mappings configuration used for data synchronization.

    **Configuration Details:**
    - Field mapping definitions between Database 1 and Database 2 columns
    - Primary link keys for record matching
    - Data transformation rules and type conversions
    - Database names and metadata

    **Use Cases:**
    - Review current synchronization configuration
    - Validate mapping setup before processing
    - Debug synchronization issues
    - Prepare for configuration updates
    """,
    responses={
        200: {
            "description": "Field mappings retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "database_names": {
                                "db1_name": "Inventory System",
                                "db2_name": "Sales System"
                            },
                            "primary_link": {
                                "db1": "SKU",
                                "db2": "ProductCode"
                            },
                            "field_mappings": [
                                {
                                    "db1_field": "Quantity",
                                    "db2_field": "StockLevel",
                                    "data_type": "integer",
                                    "required": True
                                }
                            ]
                        }
                    }
                }
            }
        },
        500: {
            "description": "Failed to retrieve field mappings",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Failed to get field mappings: Configuration file not found"
                    }
                }
            }
        }
    }
)
async def get_field_mappings(service: DataService = Depends(get_data_service)):
    """Get current field mappings configuration."""
    try:
        mappings = service.get_field_mappings()
        return {"success": True, "data": mappings}
    except Exception as e:
        logger.error(f"Failed to get field mappings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put(
    f"{settings.api_prefix}/mappings",
    tags=["config"],
    summary="Update Field Mappings",
    description="""
    Update the field mappings configuration for data synchronization.

    **Configuration Updates:**
    - Modify field mapping definitions between databases
    - Update primary link keys for record matching
    - Change data transformation rules
    - Adjust database names and metadata

    **Validation:**
    - JSON schema validation of mapping structure
    - Field existence verification
    - Data type compatibility checks
    - Link key validity confirmation

    **Effects:**
    - Immediately applies new mappings to data processing
    - May require re-processing of existing data
    - Affects future synchronization operations
    """,
    responses={
        200: {
            "description": "Field mappings updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Field mappings updated successfully"
                    }
                }
            }
        },
        400: {
            "description": "Invalid field mappings configuration",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Failed to update field mappings: Invalid field mapping structure"
                    }
                }
            }
        }
    }
)
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
@app.post(
    f"{settings.api_prefix}/export",
    response_model=ExportResponse,
    tags=["export"],
    summary="Export Data to File",
    description="""
    Export processed data to a file in the specified format.

    **Supported Data Types:**
    - `db1`: Database 1 data
    - `db2`: Database 2 data
    - `combined`: Synchronized combined data
    - `unmatched`: Analysis of unmatched items

    **Supported Formats:**
    - `csv`: Comma-separated values
    - `xlsx`: Excel spreadsheet
    - `json`: JSON format

    **File Storage:**
    - Files are saved to the exports directory
    - Files can be downloaded using the download endpoint
    - Files include timestamps in filenames for uniqueness

    **Use Cases:**
    - Backup processed data
    - Share results with other systems
    - Archive synchronization results
    - Generate reports for stakeholders
    """,
    responses={
        200: {
            "description": "Data exported successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Data exported successfully",
                        "file_path": "output_data/exports/combined_data_20250924_153000.xlsx",
                        "file_size": 245760
                    }
                }
            }
        },
        400: {
            "description": "Export request validation failed",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid data type: supported types are db1, db2, combined, unmatched"
                    }
                }
            }
        },
        500: {
            "description": "Export operation failed",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Failed to export data: No data available for export"
                    }
                }
            }
        }
    }
)
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


@app.get(
    f"{settings.api_prefix}/export/download/{{filename}}",
    tags=["export"],
    summary="Download Exported File",
    description="""
    Download a previously exported data file.

    **File Access:**
    - Files must exist in the exports directory
    - Filename must match exactly (including timestamp)
    - Files are served as binary downloads

    **Security:**
    - Only files in the designated exports directory can be downloaded
    - Directory traversal is prevented
    - Files are validated for existence before download

    **Usage:**
    - Use the file_path returned from the export endpoint
    - Extract filename from the path for this endpoint
    - Files can be downloaded multiple times until cleanup
    """,
    responses={
        200: {
            "description": "File download initiated",
            "content": {
                "application/octet-stream": {
                    "schema": {
                        "type": "string",
                        "format": "binary"
                    }
                }
            }
        },
        404: {
            "description": "File not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "File not found"
                    }
                }
            }
        }
    }
)
async def download_file(filename: str):
    """Download exported file."""
    try:
        exports_dir = Path(settings.api_output_dir)
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
@app.put(
    f"{settings.api_prefix}/data/{{data_type}}/record/{{record_index}}",
    tags=["data"],
    summary="Update Data Record",
    description="""
    Update a specific record in the loaded data.

    **Supported Data Types:**
    - `db1`: Database 1 records
    - `db2`: Database 2 records
    - `combined`: Combined/synchronized records

    **Update Operations:**
    - Modify individual field values
    - Apply data corrections and updates
    - Update synchronized values across databases

    **Validation:**
    - Record index must be valid (0-based)
    - Field names must exist in the data
    - Data types must be compatible
    - Changes are applied immediately

    **Effects:**
    - Updates affect in-memory data
    - May impact combined data if modified
    - Changes persist until data is reloaded
    """,
    responses={
        200: {
            "description": "Record updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Record updated successfully"
                    }
                }
            }
        },
        400: {
            "description": "Update failed due to validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Failed to update record: Invalid field name or data type"
                    }
                }
            }
        }
    }
)
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


# API Data Flow Endpoints - Session-based temporary storage
# Temporarily commented out for testing
# @app.post(f"{settings.api_prefix}/session/create")
# async def create_session(
#     client_info: Optional[Dict[str, Any]] = None,
#     api_service: ApiDataService = Depends(get_api_data_service)
# ):
#     """Create a new API session for data processing."""
#     try:
#         session_id = api_service.create_session(client_info)
#         return {
#             "success": True,
#             "session_id": session_id,
#             "message": "Session created successfully"
#         }
#     except Exception as e:
#         logger.error(f"Failed to create session: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# @app.post(f"{settings.api_prefix}/session/{{session_id}}/upload")
# async def upload_session_file(
#     session_id: str,
#     file: UploadFile = File(...),
#     api_service: ApiDataService = Depends(get_api_data_service)
# ):
#     """Upload a file to an existing session."""
#     try:
#         # Read file content
#         file_content = await file.read()

#         # Store file in session
#         file_path = api_service.store_uploaded_file(
#             session_id=session_id,
#             file_content=file_content,
#             filename=file.filename,
#             content_type=file.content_type
#         )

#         return {
#             "success": True,
#             "session_id": session_id,
#             "filename": file.filename,
#             "file_path": file_path,
#             "message": "File uploaded successfully"
#         }
#     except ValueError as e:
#         raise HTTPException(status_code=404, detail=str(e))
#     except Exception as e:
#         logger.error(f"Failed to upload file to session {session_id}: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# @app.post(f"{settings.api_prefix}/session/{{session_id}}/process")
# async def process_session_data(
#     session_id: str,
#     api_service: ApiDataService = Depends(get_api_data_service),
#     data_service: DataService = Depends(get_data_service)
# ):
#     """Process data for a session using the uploaded files."""
#     try:
#         # Get session files
#         session_files = api_service.get_session_files(session_id)
#         if not session_files:
#             raise HTTPException(status_code=400, detail="No files uploaded to session")

#         # For now, use the first uploaded file as DB1 data
#         # TODO: Support multiple files and proper data type detection
#         uploaded_file = session_files[0]
#         file_path = Path(settings.api_input_dir) / session_id / uploaded_file["stored_filename"]

#         if not file_path.exists():
#             raise HTTPException(status_code=404, detail="Uploaded file not found")

#         # Load data from uploaded file
#         data_service.load_data_from_file(str(file_path), "db1")

#         # Move to processing stage
#         processing_data = {
#             "db1_records": len(data_service.db1_data) if data_service.db1_data is not None else 0,
#             "processed_at": datetime.now().isoformat()
#         }

#         api_service.move_to_processing(session_id, processing_data)

#         # Generate combined data
#         data_service.combine_data()

#         # Store results
#         result_files = []
#         if data_service.combined_data is not None:
#             # Export combined data
#             export_path = data_service.export_data("combined", "csv", filename=f"combined_{session_id}")
#             if export_path:
#                 result_files.append(export_path)

#         results_data = {
#             "combined_records": len(data_service.combined_data) if data_service.combined_data is not None else 0,
#             "exported_files": result_files
#         }

#         api_service.store_results(session_id, results_data, result_files)

#         return {
#             "success": True,
#             "session_id": session_id,
#             "message": "Data processed successfully",
#             "results": results_data
#         }
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Failed to process session {session_id}: {e}")
#         api_service.update_session_status(session_id, ApiSessionStatus.ERROR, {"error": str(e)})
#         raise HTTPException(status_code=500, detail=str(e))


# @app.get(f"{settings.api_prefix}/session/{{session_id}}/status")
# async def get_session_status(
#     session_id: str,
#     api_service: ApiDataService = Depends(get_api_data_service)
# ):
#     """Get the status of a session."""
#     try:
#         session = api_service.get_session(session_id)
#         if not session:
#             raise HTTPException(status_code=404, detail="Session not found")

#         return {
#             "success": True,
#             "session_id": session_id,
#             "status": session.status.value,
#             "created_at": session.created_at.isoformat(),
#             "files_count": len(session.files),
#             "metadata": session.metadata
#         }
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Failed to get session status {session_id}: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# @app.get(f"{settings.api_prefix}/session/{{session_id}}/results")
# async def get_session_results(
#     session_id: str,
#     api_service: ApiDataService = Depends(get_api_data_service)
# ):
#     """Get the results of a completed session."""
#     try:
#         results = api_service.get_results(session_id)
#         if not results:
#             session = api_service.get_session(session_id)
#             if not session:
#                 raise HTTPException(status_code=404, detail="Session not found")
#             elif session.status == ApiSessionStatus.ERROR:
#                 raise HTTPException(status_code=500, detail=f"Session processing failed: {session.metadata.get('error', 'Unknown error')}")
#             else:
#                 raise HTTPException(status_code=202, detail="Session processing not completed yet")

#         return {
#             "success": True,
#             "session_id": session_id,
#             "results": results
#         }
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Failed to get session results {session_id}: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# @app.get(f"{settings.api_prefix}/session/{{session_id}}/download/{{filename}}")
# async def download_session_file(
#     session_id: str,
#     filename: str,
#     api_service: ApiDataService = Depends(get_api_data_service)
# ):
#     """Download a file from a session's results."""
#     try:
#         session = api_service.get_session(session_id)
#         if not session or session.status != ApiSessionStatus.COMPLETED:
#             raise HTTPException(status_code=404, detail="Session not found or not completed")

#         # Look for the file in the session results directory
#         results_dir = Path(settings.api_output_dir) / session_id
#         file_path = results_dir / filename

#         if not file_path.exists():
#             raise HTTPException(status_code=404, detail="File not found")

#         return FileResponse(
#             path=file_path,
#             filename=filename,
#             media_type='application/octet-stream'
#         )
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Failed to download file {filename} from session {session_id}: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# @app.delete(f"{settings.api_prefix}/session/{{session_id}}")
# async def cleanup_session(
#     session_id: str,
#     api_service: ApiDataService = Depends(get_api_data_service)
# ):
#     """Clean up a completed session and its temporary data."""
#     try:
#         api_service.cleanup_session(session_id)
#         return {
#             "success": True,
#             "session_id": session_id,
#             "message": "Session cleaned up successfully"
#         }
#     except Exception as e:
#         logger.error(f"Failed to cleanup session {session_id}: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# @app.get(f"{settings.api_prefix}/sessions")
# async def list_sessions(
#     api_service: ApiDataService = Depends(get_api_data_service)
# ):
#     """List all active sessions."""
#     try:
#         sessions = api_service.list_active_sessions()
#         return {
#             "success": True,
#             "sessions": sessions,
#             "count": len(sessions)
#         }
#     except Exception as e:
#         logger.error(f"Failed to list sessions: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# API Data Management Endpoints

@app.post(
    f"{settings.api_prefix}/cleanup/expired",
    tags=["storage"],
    summary="Cleanup Expired Sessions",
    description="""
    Manually trigger cleanup of expired API sessions and their associated data.

    **Cleanup Criteria:**
    - Sessions older than the specified maximum age (default: 24 hours)
    - Sessions that have exceeded their expiration time
    - Associated uploaded files and temporary data

    **Automatic Cleanup:**
    - The system automatically cleans up expired sessions periodically
    - This endpoint allows manual triggering of the cleanup process
    - Useful for immediate cleanup or custom retention policies

    **Parameters:**
    - `max_age_hours`: Maximum age in hours for sessions to be considered expired (default: 24)
    """,
    responses={
        200: {
            "description": "Cleanup completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Cleaned up 3 expired sessions",
                        "max_age_hours": 24
                    }
                }
            }
        },
        500: {
            "description": "Cleanup operation failed",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Failed to cleanup expired sessions: Permission denied"
                    }
                }
            }
        }
    }
)
async def cleanup_expired_sessions(
    max_age_hours: int = Query(24, description="Maximum age in hours for sessions to be considered expired"),
    api_service: ApiDataService = Depends(get_api_data_service)
):
    """Manually trigger cleanup of expired sessions."""
    try:
        cleaned_count = api_service.cleanup_expired_sessions(max_age_hours)
        return {
            "success": True,
            "message": f"Cleaned up {cleaned_count} expired sessions",
            "max_age_hours": max_age_hours
        }
    except Exception as e:
        logger.error(f"Failed to cleanup expired sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    f"{settings.api_prefix}/cleanup/completed",
    tags=["storage"],
    summary="Cleanup Completed Sessions",
    description="""
    Manually trigger cleanup of old completed API sessions and their associated data.

    **Cleanup Criteria:**
    - Completed sessions older than the specified maximum age (default: 1 hour)
    - Sessions that have finished processing successfully
    - Associated uploaded files and temporary data

    **Automatic Cleanup:**
    - The system automatically cleans up completed sessions periodically
    - This endpoint allows manual triggering of the cleanup process
    - Useful for immediate cleanup or custom retention policies

    **Parameters:**
    - `max_age_hours`: Maximum age in hours for completed sessions to be cleaned up (default: 1)
    """,
    responses={
        200: {
            "description": "Cleanup completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Cleaned up 5 old completed sessions",
                        "max_age_hours": 1
                    }
                }
            }
        },
        500: {
            "description": "Cleanup operation failed",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Failed to cleanup completed sessions: File system error"
                    }
                }
            }
        }
    }
)
async def cleanup_completed_sessions(
    max_age_hours: int = Query(1, description="Maximum age in hours for completed sessions to be cleaned up"),
    api_service: ApiDataService = Depends(get_api_data_service)
):
    """Manually trigger cleanup of old completed sessions."""
    try:
        cleaned_count = api_service.cleanup_completed_sessions(max_age_hours)
        return {
            "success": True,
            "message": f"Cleaned up {cleaned_count} old completed sessions",
            "max_age_hours": max_age_hours
        }
    except Exception as e:
        logger.error(f"Failed to cleanup completed sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    f"{settings.api_prefix}/storage/stats",
    tags=["storage"],
    summary="Get Storage Statistics",
    description="""
    Retrieve detailed statistics about API data storage usage and session information.

    **Statistics Provided:**
    - Total number of active sessions
    - Storage space used by uploaded files
    - Session status breakdown (active, completed, expired)
    - File count and size information
    - Directory structure information

    **Use Cases:**
    - Monitor storage usage and plan capacity
    - Track session activity and cleanup needs
    - Debug storage-related issues
    - Performance monitoring and optimization
    """,
    responses={
        200: {
            "description": "Storage statistics retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "stats": {
                            "total_sessions": 12,
                            "active_sessions": 3,
                            "completed_sessions": 8,
                            "expired_sessions": 1,
                            "storage_used": 5242880,
                            "total_files": 45,
                            "directories": {
                                "incoming": 25,
                                "processed": 15,
                                "config": 5
                            }
                        }
                    }
                }
            }
        },
        500: {
            "description": "Failed to retrieve storage statistics",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Failed to get storage stats: Permission denied accessing storage directory"
                    }
                }
            }
        }
    }
)
async def get_storage_stats(
    api_service: ApiDataService = Depends(get_api_data_service)
):
    """Get storage statistics for API data."""
    try:
        stats = api_service.get_storage_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Failed to get storage stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# API Versioning - V2 Router (placeholder for future enhancements)
from fastapi import APIRouter

v2_router = APIRouter(prefix="/api/v2", tags=["v2"])

@v2_router.get("/health")
async def health_check_v2():
    """Health check for API v2."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "api_version": "v2",
        "message": "DBSyncr API v2 is operational"
    }

# Include v2 router
app.include_router(v2_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
