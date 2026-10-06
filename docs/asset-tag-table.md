# Asset Tag Table Setup

## Overview

The Asset Tag table (`dystudio_assettag`) manages tags for organizing and categorizing vision assets. It provides a flexible tagging system with category-based organization and media type filtering.

## Table Schema

### Basic Information
- **Table Name**: `dystudio_assettag`
- **Collection Name**: `dystudio_assettags`
- **Primary Key**: `dystudio_assettagid` (GUID)
- **Primary Name Column**: `dystudio_name`

### Columns

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `dystudio_name` | Single Line Text | ✅ | Primary tag name (Max 200 chars) |
| `dystudio_tag_name` | Single Line Text | ✅ | Alternative tag name field |
| `dystudio_category` | Choice | ✅ | Tag category (Global: dystudio_TagCategory) |
| `dystudio_description` | Multiple Lines Text | ❌ | Detailed tag description (Max 1000 chars) |
| `dystudio_usage_count` | Whole Number | ❌ | Number of times tag has been used (Min 0, Default 0) |
| `dystudio_last_used` | Date and Time | ❌ | When tag was last applied to an asset |
| `dystudio_media_applicability` | Choice | ✅ | Which media types this tag applies to (Global: dystudio_MediaApplicability) |

## Global Choices

### dystudio_TagCategory
| Label | Value | Description |
|-------|-------|-------------|
| Style | 100000000 | Visual style and artistic approach |
| Subject | 100000001 | Main subject matter |
| Color | 100000002 | Color themes and palettes |
| Mood | 100000003 | Emotional tone and atmosphere |
| Brand | 100000004 | Brand-related tags |
| Object | 100000005 | Specific objects or items |
| Location | 100000006 | Geographic or setting-based tags |

### dystudio_MediaApplicability  
| Label | Value | Description |
|-------|-------|-------------|
| Image | 100000000 | Applies to image assets only |
| Video | 100000001 | Applies to video assets only |
| Both | 100000002 | Applies to both image and video assets |

## Relationships

### Many-to-Many with Vision Assets
- **Relationship Schema Name**: `dystudio_visionasset_assettags`
- **Intersect Table**: `dystudio_dystudio_visionasset_dystudio_assettag`
- **Navigation Properties**:
  - From Vision Asset: `dystudio_visionasset_assettags`
  - From Asset Tag: `dystudio_assettag_visionassets`

## Key Features

### Alternate Key
- **Key Name**: `dystudio_AssetTag_Name_UniqueKey`
- **Column**: `dystudio_name`
- **Purpose**: Ensures tag name uniqueness and enables efficient lookups

### System Views

#### Popular Tags
Shows tags sorted by usage count (most popular first)
- **Columns**: Name, Category, Usage Count, Last Used, Media Applicability
- **Sort**: Usage Count (DESC)

#### Recent Tags  
Shows tags sorted by last usage date
- **Columns**: Name, Category, Usage Count, Last Used, Media Applicability
- **Sort**: Last Used (DESC)

#### Image Tags
Shows tags applicable to images (Image or Both)
- **Columns**: Name, Category, Description, Usage Count, Last Used
- **Filter**: Media Applicability = Image OR Both
- **Sort**: Name (ASC)

#### Video Tags
Shows tags applicable to videos (Video or Both)  
- **Columns**: Name, Category, Description, Usage Count, Last Used
- **Filter**: Media Applicability = Video OR Both
- **Sort**: Name (ASC)

### Quick Find Configuration
Searches across:
- Tag name (`dystudio_name`)
- Description (`dystudio_description`)

## Setup Instructions

### Automated Setup (PowerShell Script)

The solution includes a PowerShell script for automated setup:

```powershell
.\Setup-AssetTag.ps1 -OrgUrl "https://yourorg.crm.dynamics.com"
```

This script creates:
- Global choices (MediaApplicability, TagCategory)
- Entity and column verification
- Alternate key
- Many-to-many relationship
- System views
- Solution component binding
- Publishes customizations

### Manual Setup (Maker Portal)

#### 1. Create Global Choices

**Media Applicability Choice**:
1. Navigate to Solutions → Vision-Design → + New → Choice
2. Display name: `Media Applicability`
3. Name: `dystudio_MediaApplicability`
4. Add options: Image (100000000), Video (100000001), Both (100000002)

**Tag Category Choice**:
1. Create new choice: `Tag Category` (`dystudio_TagCategory`)  
2. Add 7 options: Style, Subject, Color, Mood, Brand, Object, Location

#### 2. Verify/Create Table
Ensure Asset Tag table exists with all required columns as specified in schema above.

#### 3. Create Alternate Key
1. Open Asset Tag table → Keys tab → + New key
2. Name: `dystudio_AssetTag_Name_UniqueKey`
3. Columns: Select `dystudio_name`

#### 4. Create Many-to-Many Relationship
1. Asset Tag table → Relationships → + New relationship → Many-to-many
2. Related table: Vision Asset
3. Configure navigation properties and associated menus

#### 5. Create System Views
Create all four views as specified above with proper columns, filters, and sorting.

#### 6. Enable Auditing
Enable auditing on the table and all custom columns.

## Usage Examples

### Create Asset Tag
```http
POST /api/data/v9.2/dystudio_assettags
Content-Type: application/json

{
  "dystudio_name": "Landscape Photography",
  "dystudio_category": 100000000,
  "dystudio_description": "Natural landscape and scenery photography",
  "dystudio_usage_count": 0,
  "dystudio_media_applicability": 100000000
}
```

### Associate Tag with Vision Asset
```http
POST /api/data/v9.2/dystudio_assettags({tagid})/dystudio_assettag_visionassets/$ref
Content-Type: application/json

{
  "@odata.id": "/api/data/v9.2/dystudio_visionassets({assetid})"
}
```

### Query Tags by Category
```http
GET /api/data/v9.2/dystudio_assettags?$filter=dystudio_category eq 100000000&$select=dystudio_name,dystudio_description
```

### Find Assets by Tag
```http
GET /api/data/v9.2/dystudio_visionassets?$filter=dystudio_visionasset_assettags/any(t: t/dystudio_name eq 'Landscape Photography')
```

### Update Usage Count
```http
PATCH /api/data/v9.2/dystudio_assettags({tagid})
Content-Type: application/json

{
  "dystudio_usage_count": 15,
  "dystudio_last_used": "2024-01-01T12:00:00Z"
}
```

## Sample Data

### Style Tags
```json
[
  {
    "dystudio_name": "Minimalist",
    "dystudio_category": 100000000,
    "dystudio_description": "Clean, simple design with minimal elements",
    "dystudio_media_applicability": 100000002
  },
  {
    "dystudio_name": "Vintage",
    "dystudio_category": 100000000,
    "dystudio_description": "Retro styling with aged appearance",
    "dystudio_media_applicability": 100000000
  }
]
```

### Subject Tags
```json
[
  {
    "dystudio_name": "Portrait",
    "dystudio_category": 100000001,
    "dystudio_description": "Human portraits and headshots",
    "dystudio_media_applicability": 100000000
  },
  {
    "dystudio_name": "Architecture",
    "dystudio_category": 100000001,
    "dystudio_description": "Buildings and architectural structures",
    "dystudio_media_applicability": 100000002
  }
]
```

## Verification

### Basic Functionality Tests
1. Create tags with different categories
2. Associate tags with vision assets
3. Test all system views
4. Verify quick find searches
5. Test alternate key uniqueness constraint

### Performance Tests  
1. Test with large number of tags (1000+)
2. Verify many-to-many relationship performance
3. Test view filtering and sorting with large datasets

### Integration Tests
1. Verify Power Automate flow access
2. Test with model-driven apps
3. Validate security role permissions

## Troubleshooting

### Common Issues
- **Alternate Key Not Activating**: Wait 10-15 minutes after publishing; check for duplicate names
- **Global Choice Not Available**: Verify choice is in solution; refresh browser cache
- **Relationship Not Showing**: Verify both tables in solution; check associated menu config
- **Quick Find Not Working**: Ensure columns marked as Searchable; republish customizations

## Next Steps

1. Complete setup verification using the verification checklist
2. Create sample tags for each category
3. Configure security roles and field-level permissions  
4. Add tag management to model-driven apps
5. Set up automated tag suggestion workflows
6. Implement tag usage analytics and reporting