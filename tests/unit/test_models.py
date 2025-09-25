"""
Unit tests for Pydantic data models in data_models.py
Tests field validation, type checking, serialization/deserialization, and configuration model validation
"""
import pytest
from datetime import datetime
from pydantic import ValidationError
from src.models.data_models import (
    HealthResponse, ErrorResponse, UploadResponse, ExportRequest, ExportResponse,
    UnmatchedAnalysis, FieldMappingsConfig, DatabaseRecord, CombinedRecord
)


class TestHealthResponseModel:
    """Test HealthResponse model."""

    def test_health_response(self):
        """Test HealthResponse creation."""
        response = HealthResponse(
            status="healthy",
            version="1.0.0",
            timestamp=datetime.now()
        )

        assert response.status == "healthy"
        assert response.version == "1.0.0"
        assert isinstance(response.timestamp, datetime)


class TestErrorResponseModel:
    """Test ErrorResponse model."""

    def test_error_response(self):
        """Test ErrorResponse creation."""
        response = ErrorResponse(
            message="Validation failed",
            details={"field": "username", "issue": "required"}
        )

        assert response.error is True
        assert response.message == "Validation failed"
        assert response.details["field"] == "username"
        assert isinstance(response.timestamp, datetime)


class TestUploadResponseModel:
    """Test UploadResponse model."""

    def test_upload_response(self):
        """Test UploadResponse creation."""
        response = UploadResponse(
            success=True,
            message="File uploaded successfully",
            filename="test.csv",
            records_processed=100
        )

        assert response.success is True
        assert response.message == "File uploaded successfully"
        assert response.filename == "test.csv"
        assert response.records_processed == 100


class TestExportRequestModel:
    """Test ExportRequest model."""

    def test_export_request_minimal(self):
        """Test ExportRequest with minimal data."""
        request = ExportRequest(data_type="combined")

        assert request.data_type == "combined"
        assert request.format == "csv"  # default

    def test_export_request_full(self):
        """Test ExportRequest with all fields."""
        request = ExportRequest(
            data_type="combined",
            format="excel",
            filename="export.xlsx",
            include_columns=["id", "name", "price"]
        )

        assert request.data_type == "combined"
        assert request.format == "excel"
        assert request.filename == "export.xlsx"
        assert request.include_columns == ["id", "name", "price"]


class TestExportResponseModel:
    """Test ExportResponse model."""

    def test_export_response(self):
        """Test ExportResponse creation."""
        response = ExportResponse(
            success=True,
            message="Export completed",
            download_url="/api/v1/download/export_123.csv",
            records_exported=150
        )

        assert response.success is True
        assert response.download_url == "/api/v1/download/export_123.csv"
        assert response.records_exported == 150


class TestUnmatchedAnalysisModel:
    """Test UnmatchedAnalysis model."""

    def test_unmatched_analysis(self):
        """Test UnmatchedAnalysis creation."""
        analysis = UnmatchedAnalysis(
            total_db1_items=100,
            total_db2_items=80,
            matched_items=70,
            db1_only_items=30,
            db2_only_items=10,
            match_rate=0.875,
            db1_only_keys=["SKU001", "SKU002"],
            db2_only_keys=["PROD001"],
            analysis_timestamp=datetime.now()
        )

        assert analysis.total_db1_items == 100
        assert analysis.total_db2_items == 80
        assert analysis.matched_items == 70
        assert analysis.db1_only_items == 30
        assert analysis.db2_only_items == 10
        assert analysis.match_rate == 0.875
        assert len(analysis.db1_only_keys) == 2
        assert len(analysis.db2_only_keys) == 1


class TestFieldMappingsConfigModel:
    """Test FieldMappingsConfig model."""

    def test_field_mappings_config(self):
        """Test FieldMappingsConfig creation."""
        from src.models.data_models import DatabaseNames, LinkingConfig, FieldMapping, DataSource, FileType, MappingDirection

        config = FieldMappingsConfig(
            database_names=DatabaseNames(db1_name="Shopify", db2_name="NetSuite"),
            field_mappings={
                "product_name": FieldMapping(
                    db1_field="Title",
                    db2_field="Name",
                    direction=MappingDirection.BIDIRECTIONAL
                )
            },
            data_sources={
                "db1": DataSource(
                    file_path="data/db1.csv",
                    file_type=FileType.CSV,
                    name="Database 1"
                )
            },
            primary_link=LinkingConfig(db1="ID", db2="ID")
        )

        assert config.database_names.db1_name == "Shopify"
        assert "product_name" in config.field_mappings
        assert len(config.data_sources) == 1


class TestDataRecordModels:
    """Test data record models."""

    def test_database_record(self):
        """Test DatabaseRecord creation."""
        record = DatabaseRecord(
            id_field="TEST001",
            weight=10.5,
            price=29.99
        )

        assert record.id_field == "TEST001"
        assert record.weight == 10.5
        assert record.price == 29.99

    def test_database_record_numeric_parsing(self):
        """Test numeric field parsing in DatabaseRecord."""
        # Test string to float conversion
        record = DatabaseRecord(
            weight="15.5",
            price="39.99",
            cost=""  # Empty string should become None
        )

        assert record.weight == 15.5
        assert record.price == 39.99
        assert record.cost is None

    def test_combined_record(self):
        """Test CombinedRecord creation."""
        record = CombinedRecord(
            linking_key="TEST001",
            db1_data={"name": "Product 1", "price": 29.99},
            db2_data={"item_name": "Product 1", "unit_price": 29.99},
            sync_status="matched"
        )

        assert record.linking_key == "TEST001"
        assert record.db1_data["name"] == "Product 1"
        assert record.db2_data["item_name"] == "Product 1"
        assert record.sync_status == "matched"