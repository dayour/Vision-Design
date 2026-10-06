# Generation History Table Setup

## Overview

The Generation History table (`dystudio_generationhistory`) tracks AI generation requests and their outcomes, providing comprehensive logging and analytics capabilities for the Vision Design solution.

## Table Schema

### Basic Information
- **Table Name**: `dystudio_generationhistory`
- **Collection Name**: `dystudio_generationhistories`
- **Primary Key**: `dystudio_generationhistoryid` (GUID)
- **Primary Name Column**: `dystudio_generation_id`

### Columns

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `dystudio_generation_id` | Single Line Text | ✅ | Unique identifier for the generation request |
| `dystudio_request_type` | Choice | ✅ | Type of generation request (Global: dystudio_RequestType) |
| `dystudio_prompt` | Multiple Lines | ✅ | User's original prompt (Max 4000 chars) |
| `dystudio_enhanced_prompt` | Multiple Lines | ❌ | AI-enhanced version of the prompt |
| `dystudio_model` | Single Line Text | ✅ | Model used for generation |
| `dystudio_parameters_json` | Multiple Lines | ❌ | JSON parameters for the request |
| `dystudio_status` | Choice | ✅ | Current status (Global: dystudio_GenerationStatus) |
| `dystudio_result_count` | Whole Number | ❌ | Number of assets generated |
| `dystudio_started_at` | Date and Time | ✅ | When generation started |
| `dystudio_completed_at` | Date and Time | ❌ | When generation completed |
| `dystudio_duration_ms` | Whole Number | ❌ | Duration in milliseconds |
| `dystudio_tokens_used` | Whole Number | ❌ | Total tokens consumed |
| `dystudio_input_tokens` | Whole Number | ❌ | Input tokens used |
| `dystudio_output_tokens` | Whole Number | ❌ | Output tokens generated |
| `dystudio_estimated_cost` | Currency | ❌ | Estimated cost in USD |
| `dystudio_error_message` | Multiple Lines | ❌ | Error details if generation failed |

## Global Choices

### dystudio_RequestType
| Label | Value |
|-------|-------|
| Image | 100000000 |
| Video | 100000001 |
| Image Edit | 100000002 |

### dystudio_GenerationStatus
| Label | Value |
|-------|-------|
| Pending | 100000000 |
| In Progress | 100000001 |
| Completed | 100000002 |
| Failed | 100000003 |
| Cancelled | 100000004 |

## Relationships

### 1-to-Many with Vision Assets
- **Parent**: `dystudio_generationhistory`
- **Child**: `dystudio_visionasset`
- **Lookup Column**: `dystudio_generationhistoryid`
- **Relationship Schema Name**: `dystudio_generationhistory_visionassets`

## Required Manual Setup Steps

### 1. Primary Name Column Correction
The table currently uses `dystudio_name` as primary name instead of `dystudio_generation_id`.

**Action Required**: Via Web API or Maker Portal, update table metadata to set Primary Name Attribute = `dystudio_generation_id`

### 2. Create Alternate Key
Create unique key on `dystudio_generation_id` for efficient lookups.

**Key Configuration**:
- **Key Name**: `dystudio_GenerationHistory_GenerationId_Key`
- **Column**: `dystudio_generation_id`

### 3. System Views

Create the following standard views:

#### Recent Generations
- **Columns**: Generation ID, Request Type, Model, Status, Started At, Duration (ms), Estimated Cost
- **Sort**: Created On (DESC)
- **Filter**: None

#### Active Jobs  
- **Columns**: Generation ID, Request Type, Model, Status, Started At, Prompt (truncated)
- **Sort**: Started At (ASC)
- **Filter**: Status IN (Pending, In Progress)

#### Failed Jobs
- **Columns**: Generation ID, Request Type, Model, Error Message, Started At, Completed At
- **Sort**: Started At (DESC)  
- **Filter**: Status = Failed

#### My Generations
- **Columns**: Generation ID, Request Type, Status, Started At, Result Count, Estimated Cost
- **Sort**: Created On (DESC)
- **Filter**: Created By = Current User

### 4. Quick Find Configuration
Enable Quick Find on:
- `dystudio_generation_id` (Primary)
- `dystudio_prompt`
- `dystudio_enhanced_prompt`
- `dystudio_model`

### 5. Enable Auditing
Enable auditing on the table and all custom columns for compliance and troubleshooting.

## Sample Data

### Completed Image Generation
```json
{
  "dystudio_generation_id": "img_abc123xyz",
  "dystudio_request_type": 100000000,
  "dystudio_prompt": "A futuristic cityscape at sunset",
  "dystudio_model": "flux-1-pro",
  "dystudio_status": 100000002,
  "dystudio_started_at": "2025-09-29T10:00:00Z",
  "dystudio_completed_at": "2025-09-29T10:00:15Z",
  "dystudio_duration_ms": 15000,
  "dystudio_result_count": 4,
  "dystudio_tokens_used": 0,
  "dystudio_estimated_cost": 0.50
}
```

### Failed Video Generation
```json
{
  "dystudio_generation_id": "vid_fail_789",
  "dystudio_request_type": 100000001,
  "dystudio_prompt": "Flying through clouds",
  "dystudio_model": "sora-v1",
  "dystudio_status": 100000003,
  "dystudio_started_at": "2025-09-29T11:30:00Z",
  "dystudio_completed_at": "2025-09-29T11:30:45Z",
  "dystudio_duration_ms": 45000,
  "dystudio_error_message": "Rate limit exceeded. Retry after 60 seconds.",
  "dystudio_result_count": 0,
  "dystudio_estimated_cost": 0.00
}
```

## Web API Examples

### Create Generation History Record
```http
POST /api/data/v9.2/dystudio_generationhistories
Content-Type: application/json

{
  "dystudio_generation_id": "unique_gen_id",
  "dystudio_request_type": 100000000,
  "dystudio_prompt": "Your prompt here",
  "dystudio_model": "model_name",
  "dystudio_status": 100000000,
  "dystudio_started_at": "2024-01-01T12:00:00Z"
}
```

### Query by Generation ID (Alternate Key)
```http
GET /api/data/v9.2/dystudio_generationhistories(dystudio_generation_id='unique_gen_id')
```

### Update Status
```http
PATCH /api/data/v9.2/dystudio_generationhistories({id})
Content-Type: application/json

{
  "dystudio_status": 100000002,
  "dystudio_completed_at": "2024-01-01T12:01:30Z",
  "dystudio_duration_ms": 90000
}
```

## Next Steps

1. Complete the manual setup steps above
2. Test the table functionality with sample data
3. Configure security roles and permissions
4. Set up any required business rules or workflows
5. Add the table to relevant model-driven apps