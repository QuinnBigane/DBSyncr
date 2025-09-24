"""
Data Models for DBSyncr
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


class MappingDirection(str, Enum):
    """Direction enum for field mappings."""
    BIDIRECTIONAL = "bidirectional"
    DB1_TO_DB2 = "db1_to_db2"
    DB2_TO_DB1 = "db2_to_db1"


class FileType(str, Enum):
    """Supported file types."""
    EXCEL = "excel"
    CSV = "csv"


class DataSource(BaseModel):
    """Data source configuration model."""
    file_path: str
    file_type: FileType
    name: Optional[str] = None
    description: Optional[str] = None


class FieldMapping(BaseModel):
    """Field mapping configuration model."""
    db1_field: str
    db2_field: str
    direction: MappingDirection = MappingDirection.BIDIRECTIONAL
    description: Optional[str] = None
    data_type: Optional[str] = None
    validation_rules: Optional[Dict[str, Any]] = None


class DatabaseNames(BaseModel):
    """Database names configuration."""
    db1_name: str = "Database 1"
    db2_name: str = "Database 2"


class LinkingConfig(BaseModel):
    """Primary linking configuration."""
    db1: str = "ID"
    db2: str = "ID"


class FieldMappingsConfig(BaseModel):
    """Complete field mappings configuration model."""
    database_names: DatabaseNames
    field_mappings: Dict[str, FieldMapping]
    data_sources: Dict[str, DataSource]
    primary_link: LinkingConfig


class DataRecord(BaseModel):
    """Base data record model."""
    id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        extra = "allow"  # Allow additional fields


class DatabaseRecord(DataRecord):
    """Generic database record model."""
    id_field: Optional[str] = Field(None, alias="ID")
    weight: Optional[float] = Field(None, alias="Weight")
    price: Optional[float] = Field(None, alias="Price")
    cost: Optional[float] = Field(None, alias="Cost")
    
    @validator('weight', 'price', 'cost', pre=True)
    def parse_numeric(cls, v):
        if v is None or v == '':
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None


class CombinedRecord(BaseModel):
    """Combined data record model."""
    linking_key: str
    db1_data: Optional[Dict[str, Any]] = None
    db2_data: Optional[Dict[str, Any]] = None
    sync_status: Optional[str] = None
    last_synced: Optional[datetime] = None
    
    class Config:
        extra = "allow"


class UnmatchedAnalysis(BaseModel):
    """Analysis result for unmatched items."""
    total_db1_items: int
    total_db2_items: int
    matched_items: int
    db1_only_items: int
    db2_only_items: int
    match_rate: float
    db1_only_keys: List[str]
    db2_only_keys: List[str]
    analysis_timestamp: datetime


class UploadResponse(BaseModel):
    """Response model for file uploads."""
    success: bool
    message: str
    filename: Optional[str] = None
    file_path: Optional[str] = None
    records_processed: Optional[int] = None
    errors: Optional[List[str]] = None


class ErrorResponse(BaseModel):
    """Error response model."""
    error: bool = True
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str
    database_connected: Optional[bool] = None
    services_status: Optional[Dict[str, str]] = None


class ExportRequest(BaseModel):
    """Export request model."""
    data_type: str  # netsuite, shopify, combined
    format: str = "csv"  # csv, excel
    include_columns: Optional[List[str]] = None
    filter_criteria: Optional[Dict[str, Any]] = None
    filename: Optional[str] = None


class ExportResponse(BaseModel):
    """Export response model."""
    success: bool
    message: str
    file_path: Optional[str] = None
    download_url: Optional[str] = None
    file_size: Optional[int] = None
    records_exported: Optional[int] = None