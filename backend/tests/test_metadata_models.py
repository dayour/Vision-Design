"""Unit tests for metadata models and validators."""

import pytest
import sys
from pathlib import Path
from datetime import datetime
from pydantic import ValidationError

# Ensure project root (two levels up) is available for backend imports
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.models.metadata_models import (
    AssetMetadata,
    AssetTag,
    GenerationHistory,
    TagCategory,
    MediaApplicability,
    RequestType,
    GenerationStatus,
    validate_iso_ts,
    validate_max_len,
    validate_json_serializable,
)


class TestValidators:
    """Test shared validators."""

    def test_validate_iso_ts_valid(self):
        """Test ISO-8601 timestamp validation with valid input."""
        ts = "2025-09-30T10:00:00Z"
        result = validate_iso_ts(ts)
        assert result == ts

    def test_validate_iso_ts_with_timezone(self):
        """Test ISO-8601 timestamp with timezone offset."""
        ts = "2025-09-30T10:00:00+00:00"
        result = validate_iso_ts(ts)
        assert result == ts

    def test_validate_iso_ts_none(self):
        """Test ISO-8601 timestamp validation with None."""
        result = validate_iso_ts(None)
        assert result is None

    def test_validate_iso_ts_datetime_object(self):
        """Test ISO-8601 timestamp validation with datetime object."""
        dt = datetime(2025, 9, 30, 10, 0, 0)
        result = validate_iso_ts(dt)
        assert result == dt.isoformat()

    def test_validate_iso_ts_invalid(self):
        """Test ISO-8601 timestamp validation with invalid input."""
        with pytest.raises(ValueError, match="Invalid ISO-8601 timestamp"):
            validate_iso_ts("not-a-timestamp")

    def test_validate_max_len_valid(self):
        """Test max length validation with valid input."""
        value = "short string"
        result = validate_max_len(value, 100, "test_field")
        assert result == value

    def test_validate_max_len_exact(self):
        """Test max length validation at exact boundary."""
        value = "x" * 100
        result = validate_max_len(value, 100, "test_field")
        assert result == value

    def test_validate_max_len_exceeds(self):
        """Test max length validation exceeds limit."""
        value = "x" * 101
        with pytest.raises(ValueError, match="exceeds maximum length"):
            validate_max_len(value, 100, "test_field")

    def test_validate_max_len_none(self):
        """Test max length validation with None."""
        result = validate_max_len(None, 100, "test_field")
        assert result is None

    def test_validate_json_serializable_dict(self):
        """Test JSON serializable validation with dict."""
        value = {"key": "value"}
        result = validate_json_serializable(value)
        assert result == value

    def test_validate_json_serializable_list(self):
        """Test JSON serializable validation with list."""
        value = ["item1", "item2"]
        result = validate_json_serializable(value)
        assert result == value

    def test_validate_json_serializable_none(self):
        """Test JSON serializable validation with None."""
        result = validate_json_serializable(None)
        assert result is None

    def test_validate_json_serializable_invalid(self):
        """Test JSON serializable validation with invalid input."""
        # Functions are not JSON serializable
        with pytest.raises(ValueError, match="must be JSON-serializable"):
            validate_json_serializable(lambda x: x)


class TestAssetMetadata:
    """Test AssetMetadata model."""

    def test_asset_metadata_minimal(self):
        """Test AssetMetadata with minimal required fields."""
        asset = AssetMetadata(
            id="test-guid-123",
            media_type="image",
            blob_name="test.jpg",
            container="images",
            url="https://example.com/test.jpg",
            filename="test.jpg",
            size=1024,
            created_at="2025-09-30T10:00:00Z",
            updated_at="2025-09-30T10:00:00Z",
        )
        assert asset.id == "test-guid-123"
        assert asset.media_type == "image"
        assert asset.doc_type == "asset_metadata"

    def test_asset_metadata_full(self):
        """Test AssetMetadata with all fields."""
        asset = AssetMetadata(
            id="test-guid-123",
            media_type="image",
            blob_name="test.jpg",
            container="images",
            url="https://example.com/test.jpg",
            filename="test.jpg",
            size=1024,
            content_type="image/jpeg",
            folder_path="/test/folder",
            prompt="A beautiful sunset",
            model="flux-1-pro",
            generation_id="gen-123",
            summary="An image of a sunset",
            description="Beautiful sunset over mountains",
            products="Camera X",
            tags=["sunset", "mountains"],
            feedback="Great image",
            quality="high",
            background="transparent",
            output_format="PNG",
            has_transparency=True,
            duration=None,
            fps=None,
            resolution=None,
            custom_metadata={"key": "value"},
            created_at="2025-09-30T10:00:00Z",
            updated_at="2025-09-30T10:00:00Z",
        )
        assert asset.prompt == "A beautiful sunset"
        assert len(asset.tags) == 2
        assert asset.custom_metadata["key"] == "value"

    def test_asset_metadata_invalid_timestamp(self):
        """Test AssetMetadata with invalid timestamp."""
        with pytest.raises(ValidationError):
            AssetMetadata(
                id="test-guid-123",
                media_type="image",
                blob_name="test.jpg",
                container="images",
                url="https://example.com/test.jpg",
                filename="test.jpg",
                size=1024,
                created_at="invalid-timestamp",
                updated_at="2025-09-30T10:00:00Z",
            )

    def test_asset_metadata_prompt_too_long(self):
        """Test AssetMetadata with prompt exceeding max length."""
        with pytest.raises(ValidationError):
            AssetMetadata(
                id="test-guid-123",
                media_type="image",
                blob_name="test.jpg",
                container="images",
                url="https://example.com/test.jpg",
                filename="test.jpg",
                size=1024,
                prompt="x" * 4001,  # Exceeds 4000 char limit
                created_at="2025-09-30T10:00:00Z",
                updated_at="2025-09-30T10:00:00Z",
            )


class TestAssetTag:
    """Test AssetTag model."""

    def test_asset_tag_minimal(self):
        """Test AssetTag with minimal required fields."""
        tag = AssetTag(
            id="tag-guid-123",
            name="sunset",
            created_at="2025-09-30T10:00:00Z",
            updated_at="2025-09-30T10:00:00Z",
        )
        assert tag.id == "tag-guid-123"
        assert tag.name == "sunset"
        assert tag.usage_count == 0
        assert tag.media_applicability == MediaApplicability.BOTH

    def test_asset_tag_full(self):
        """Test AssetTag with all fields."""
        tag = AssetTag(
            id="tag-guid-123",
            name="sunset",
            tag_name="beautiful_sunset",
            category=TagCategory.MOOD,
            description="Tag for sunset images",
            usage_count=42,
            last_used="2025-09-30T10:00:00Z",
            media_applicability=MediaApplicability.IMAGE,
            created_at="2025-09-30T10:00:00Z",
            updated_at="2025-09-30T10:00:00Z",
        )
        assert tag.category == TagCategory.MOOD
        assert tag.usage_count == 42
        assert tag.media_applicability == MediaApplicability.IMAGE

    def test_asset_tag_name_too_long(self):
        """Test AssetTag with name exceeding max length."""
        with pytest.raises(ValidationError):
            AssetTag(
                id="tag-guid-123",
                name="x" * 201,  # Exceeds 200 char limit
                created_at="2025-09-30T10:00:00Z",
                updated_at="2025-09-30T10:00:00Z",
            )

    def test_asset_tag_description_too_long(self):
        """Test AssetTag with description exceeding max length."""
        with pytest.raises(ValidationError):
            AssetTag(
                id="tag-guid-123",
                name="sunset",
                description="x" * 1001,  # Exceeds 1000 char limit
                created_at="2025-09-30T10:00:00Z",
                updated_at="2025-09-30T10:00:00Z",
            )

    def test_asset_tag_invalid_timestamp(self):
        """Test AssetTag with invalid timestamp."""
        with pytest.raises(ValidationError):
            AssetTag(
                id="tag-guid-123",
                name="sunset",
                created_at="invalid-timestamp",
                updated_at="2025-09-30T10:00:00Z",
            )


class TestGenerationHistory:
    """Test GenerationHistory model."""

    def test_generation_history_minimal(self):
        """Test GenerationHistory with minimal required fields."""
        gen = GenerationHistory(
            id="gen-guid-123",
            generation_id="gen-123",
            request_type=RequestType.IMAGE,
            prompt="A sunset",
            model="flux-1-pro",
            status=GenerationStatus.PENDING,
            started_at="2025-09-30T10:00:00Z",
            created_at="2025-09-30T10:00:00Z",
            updated_at="2025-09-30T10:00:00Z",
        )
        assert gen.id == "gen-guid-123"
        assert gen.generation_id == "gen-123"
        assert gen.status == GenerationStatus.PENDING
        assert gen.result_count == 0
        assert gen.estimated_cost == 0.0

    def test_generation_history_full(self):
        """Test GenerationHistory with all fields."""
        gen = GenerationHistory(
            id="gen-guid-123",
            generation_id="gen-123",
            request_type=RequestType.IMAGE,
            prompt="A beautiful sunset",
            enhanced_prompt="A beautiful sunset over mountains at golden hour",
            model="flux-1-pro",
            parameters_json='{"quality": "high"}',
            status=GenerationStatus.COMPLETED,
            result_count=4,
            started_at="2025-09-30T10:00:00Z",
            completed_at="2025-09-30T10:01:00Z",
            duration_ms=60000,
            tokens_used=1500,
            input_tokens=100,
            output_tokens=1400,
            estimated_cost=0.50,
            error_message=None,
            created_at="2025-09-30T10:00:00Z",
            updated_at="2025-09-30T10:01:00Z",
        )
        assert gen.status == GenerationStatus.COMPLETED
        assert gen.result_count == 4
        assert gen.duration_ms == 60000
        assert gen.estimated_cost == 0.50

    def test_generation_history_prompt_too_long(self):
        """Test GenerationHistory with prompt exceeding max length."""
        with pytest.raises(ValidationError):
            GenerationHistory(
                id="gen-guid-123",
                generation_id="gen-123",
                request_type=RequestType.IMAGE,
                prompt="x" * 4001,  # Exceeds 4000 char limit
                model="flux-1-pro",
                status=GenerationStatus.PENDING,
                started_at="2025-09-30T10:00:00Z",
                created_at="2025-09-30T10:00:00Z",
                updated_at="2025-09-30T10:00:00Z",
            )

    def test_generation_history_invalid_timestamp(self):
        """Test GenerationHistory with invalid timestamp."""
        with pytest.raises(ValidationError):
            GenerationHistory(
                id="gen-guid-123",
                generation_id="gen-123",
                request_type=RequestType.IMAGE,
                prompt="A sunset",
                model="flux-1-pro",
                status=GenerationStatus.PENDING,
                started_at="invalid-timestamp",
                created_at="2025-09-30T10:00:00Z",
                updated_at="2025-09-30T10:00:00Z",
            )

    def test_generation_history_parameters_json_conversion(self):
        """Test GenerationHistory converts dict parameters to JSON string."""
        gen = GenerationHistory(
            id="gen-guid-123",
            generation_id="gen-123",
            request_type=RequestType.IMAGE,
            prompt="A sunset",
            model="flux-1-pro",
            status=GenerationStatus.PENDING,
            parameters_json={"quality": "high"},  # Pass dict, should convert to JSON string
            started_at="2025-09-30T10:00:00Z",
            created_at="2025-09-30T10:00:00Z",
            updated_at="2025-09-30T10:00:00Z",
        )
        assert gen.parameters_json == '{"quality": "high"}'


class TestEnums:
    """Test enumeration classes."""

    def test_tag_category_values(self):
        """Test TagCategory enum values match Dataverse choice."""
        assert TagCategory.STYLE.value == "100000000"
        assert TagCategory.SUBJECT.value == "100000001"
        assert TagCategory.COLOR.value == "100000002"
        assert TagCategory.MOOD.value == "100000003"
        assert TagCategory.BRAND.value == "100000004"
        assert TagCategory.OBJECT.value == "100000005"
        assert TagCategory.LOCATION.value == "100000006"

    def test_media_applicability_values(self):
        """Test MediaApplicability enum values match Dataverse choice."""
        assert MediaApplicability.IMAGE.value == "100000000"
        assert MediaApplicability.VIDEO.value == "100000001"
        assert MediaApplicability.BOTH.value == "100000002"

    def test_request_type_values(self):
        """Test RequestType enum values match Dataverse choice."""
        assert RequestType.IMAGE.value == "100000000"
        assert RequestType.VIDEO.value == "100000001"
        assert RequestType.IMAGE_EDIT.value == "100000002"

    def test_generation_status_values(self):
        """Test GenerationStatus enum values match Dataverse choice."""
        assert GenerationStatus.PENDING.value == "100000000"
        assert GenerationStatus.IN_PROGRESS.value == "100000001"
        assert GenerationStatus.COMPLETED.value == "100000002"
        assert GenerationStatus.FAILED.value == "100000003"
        assert GenerationStatus.CANCELLED.value == "100000004"
