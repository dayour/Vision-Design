# Verification Procedures

## Overview

This document provides comprehensive testing and validation procedures to ensure the Vision Design Dataverse solution is properly configured and functioning correctly.

## Environment Information

Before starting verification, confirm these details:
- **Organization URL**: `https://{org}.crm.dynamics.com`
- **Solution**: Vision-Design (VisionDesign)
- **Solution ID**: `880baf0b-9b9d-f011-bbd2-6045bd02d5d6`
- **Web API**: v9.2

## Pre-Verification Checklist

Ensure the following components are set up before running verification:

- [ ] Dataverse environment is accessible
- [ ] Vision-Design solution exists and is published
- [ ] Required security roles are assigned
- [ ] PowerShell modules are installed (for automated verification)

## Verification Categories

### 1. Solution and Component Verification
### 2. Generation History Table Verification  
### 3. Asset Tag Table Verification
### 4. Relationship and Integration Verification
### 5. Performance and Security Verification

---

## 1. Solution and Component Verification

### 1.1 Solution Existence and Status

**PowerShell Verification**:
```powershell
# Connect to Dataverse
$conn = Get-CrmConnection -InteractiveMode

# Check solution exists
$solution = Get-CrmRecords -conn $conn -EntityLogicalName solution -FilterAttribute uniquename -FilterOperator eq -FilterValue "VisionDesign"

Write-Host "Solution Status: $($solution.CrmRecords[0].friendlyname)"
Write-Host "Version: $($solution.CrmRecords[0].version)"
Write-Host "Publisher: $($solution.CrmRecords[0].publisherid_Property.Value.Name)"
```

**Web API Verification**:
```http
GET https://{org}.crm.dynamics.com/api/data/v9.2/solutions?$filter=uniquename eq 'VisionDesign'&$select=friendlyname,version,publisherid
```

**Expected Results**:
- ✅ Solution exists with name "Vision-Design"
- ✅ Version 1.0.0.0 or higher
- ✅ Publisher is "dystudio"

### 1.2 Component Count Verification

**Query Solution Components**:
```http
GET https://{org}.crm.dynamics.com/api/data/v9.2/solutioncomponents?$filter=_solutionid_value eq '880baf0b-9b9d-f011-bbd2-6045bd02d5d6'&$apply=groupby((componenttype),aggregate($count as count))
```

**Expected Component Types**:
| Component Type | Expected Count | Description |
|---------------|---------------|-------------|
| 1 (Entity) | 2+ | Tables (dystudio_assettag, dystudio_generationhistory) |
| 2 (Attribute) | 15+ | Custom columns across tables |
| 9 (Global OptionSet) | 3+ | Global choices |
| 10 (Relationship) | 2+ | Table relationships |
| 26 (SavedQuery) | 8+ | System views |
| 66 (EntityKey) | 2+ | Alternate keys |

---

## 2. Generation History Table Verification

### 2.1 Table Structure Verification

**Check Table Exists**:
```http
GET https://{org}.crm.dynamics.com/api/data/v9.2/EntityDefinitions(LogicalName='dystudio_generationhistory')?$select=LogicalName,DisplayName,PrimaryNameAttribute,IsAuditEnabled
```

**Expected Results**:
- ✅ LogicalName: `dystudio_generationhistory`
- ✅ DisplayName: "Generation History"  
- ✅ PrimaryNameAttribute: `dystudio_generation_id`
- ✅ IsAuditEnabled: `true`

### 2.2 Column Verification

**Query All Columns**:
```http
GET https://{org}.crm.dynamics.com/api/data/v9.2/EntityDefinitions(LogicalName='dystudio_generationhistory')/Attributes?$filter=IsCustomAttribute eq true&$select=LogicalName,AttributeType,RequiredLevel
```

**Expected Custom Columns** (16 total):
- `dystudio_generation_id` (String, Required)
- `dystudio_request_type` (Picklist, Required) 
- `dystudio_prompt` (Memo, Required)
- `dystudio_enhanced_prompt` (Memo, Optional)
- `dystudio_model` (String, Required)
- `dystudio_parameters_json` (Memo, Optional)
- `dystudio_status` (Picklist, Required)
- `dystudio_result_count` (Integer, Optional)
- `dystudio_started_at` (DateTime, Required)
- `dystudio_completed_at` (DateTime, Optional)
- `dystudio_duration_ms` (Integer, Optional)
- `dystudio_tokens_used` (Integer, Optional)
- `dystudio_input_tokens` (Integer, Optional)
- `dystudio_output_tokens` (Integer, Optional)
- `dystudio_estimated_cost` (Money, Optional)
- `dystudio_error_message` (Memo, Optional)

### 2.3 Global Choices Verification

**Request Type Choice**:
```http
GET https://{org}.crm.dynamics.com/api/data/v9.2/GlobalOptionSetDefinitions(Name='dystudio_RequestType')?$select=Options
```

**Expected Options**:
- Image (100000000)
- Video (100000001)  
- Image Edit (100000002)

**Generation Status Choice**:
```http
GET https://{org}.crm.dynamics.com/api/data/v9.2/GlobalOptionSetDefinitions(Name='dystudio_GenerationStatus')?$select=Options
```

**Expected Options**:
- Pending (100000000)
- In Progress (100000001)
- Completed (100000002)  
- Failed (100000003)
- Cancelled (100000004)

### 2.4 Functional Testing

**Create Test Record**:
```http
POST https://{org}.crm.dynamics.com/api/data/v9.2/dystudio_generationhistories
Content-Type: application/json

{
  "dystudio_generation_id": "test_gen_001",
  "dystudio_request_type": 100000000,
  "dystudio_prompt": "Test prompt for verification",
  "dystudio_model": "test-model-v1",
  "dystudio_status": 100000000,
  "dystudio_started_at": "2024-01-01T12:00:00Z"
}
```

**Test Alternate Key Retrieval**:
```http
GET https://{org}.crm.dynamics.com/api/data/v9.2/dystudio_generationhistories(dystudio_generation_id='test_gen_001')
```

**Update Record**:
```http
PATCH https://{org}.crm.dynamics.com/api/data/v9.2/dystudio_generationhistories({id})
Content-Type: application/json

{
  "dystudio_status": 100000002,
  "dystudio_completed_at": "2024-01-01T12:01:30Z",
  "dystudio_duration_ms": 90000
}
```

**Expected Results**:
- ✅ Record created successfully
- ✅ Alternate key lookup works
- ✅ Updates save correctly
- ✅ Audit records generated (check audit history)

---

## 3. Asset Tag Table Verification

### 3.1 Table Structure Verification

**Check Table Exists**:
```http
GET https://{org}.crm.dynamics.com/api/data/v9.2/EntityDefinitions(LogicalName='dystudio_assettag')?$select=LogicalName,DisplayName,PrimaryNameAttribute,IsAuditEnabled
```

**Expected Results**:
- ✅ LogicalName: `dystudio_assettag`
- ✅ DisplayName: "Asset Tag"
- ✅ PrimaryNameAttribute: `dystudio_name`
- ✅ IsAuditEnabled: `true`

### 3.2 Column Verification

**Query Columns**:
```http
GET https://{org}.crm.dynamics.com/api/data/v9.2/EntityDefinitions(LogicalName='dystudio_assettag')/Attributes?$filter=IsCustomAttribute eq true&$select=LogicalName,AttributeType,RequiredLevel
```

**Expected Custom Columns** (6 total):
- `dystudio_name` (String, Required)
- `dystudio_category` (Picklist, Required)
- `dystudio_description` (Memo, Optional)
- `dystudio_usage_count` (Integer, Optional)
- `dystudio_last_used` (DateTime, Optional)
- `dystudio_media_applicability` (Picklist, Required)

### 3.3 Global Choices Verification

**Tag Category Choice**:
```http
GET https://{org}.crm.dynamics.com/api/data/v9.2/GlobalOptionSetDefinitions(Name='dystudio_TagCategory')?$select=Options
```

**Expected Options** (7 total):
- Style (100000000)
- Subject (100000001)
- Color (100000002)
- Mood (100000003)
- Brand (100000004)
- Object (100000005)
- Location (100000006)

**Media Applicability Choice**:
```http
GET https://{org}.crm.dynamics.com/api/data/v9.2/GlobalOptionSetDefinitions(Name='dystudio_MediaApplicability')?$select=Options
```

**Expected Options** (3 total):
- Image (100000000)
- Video (100000001)
- Both (100000002)

### 3.4 Alternate Key Verification

**Check Alternate Key Exists**:
```http
GET https://{org}.crm.dynamics.com/api/data/v9.2/EntityDefinitions(LogicalName='dystudio_assettag')/Keys?$select=SchemaName,KeyAttributes,EntityKeyIndexStatus
```

**Expected Key**:
- ✅ SchemaName: `dystudio_AssetTag_Name_UniqueKey`
- ✅ KeyAttributes: [`dystudio_name`]
- ✅ EntityKeyIndexStatus: `Active`

### 3.5 Functional Testing

**Create Test Tag**:
```http
POST https://{org}.crm.dynamics.com/api/data/v9.2/dystudio_assettags
Content-Type: application/json

{
  "dystudio_name": "Test Landscape Tag",
  "dystudio_category": 100000000,
  "dystudio_description": "Test tag for verification",
  "dystudio_usage_count": 0,
  "dystudio_media_applicability": 100000000
}
```

**Test Duplicate Name (Should Fail)**:
```http
POST https://{org}.crm.dynamics.com/api/data/v9.2/dystudio_assettags
Content-Type: application/json

{
  "dystudio_name": "Test Landscape Tag",
  "dystudio_category": 100000001
}
```

**Expected Results**:
- ✅ First record created successfully
- ✅ Duplicate name rejected (alternate key violation)
- ✅ Can retrieve by alternate key: `/dystudio_assettags(dystudio_name='Test Landscape Tag')`

### 3.6 System Views Verification

**Query Asset Tag Views**:
```http
GET https://{org}.crm.dynamics.com/api/data/v9.2/savedqueries?$filter=returnedtypecode eq 'dystudio_assettag'&$select=name,fetchxml
```

**Expected Views** (4 total):
- ✅ Popular Tags (sorted by usage count DESC)
- ✅ Recent Tags (sorted by last used DESC)  
- ✅ Image Tags (filtered: media applicability = Image OR Both)
- ✅ Video Tags (filtered: media applicability = Video OR Both)

---

## 4. Relationship and Integration Verification

### 4.1 Many-to-Many Relationship Verification

**Check Relationship Exists**:
```http
GET https://{org}.crm.dynamics.com/api/data/v9.2/RelationshipDefinitions(SchemaName='dystudio_visionasset_assettags')
```

**Expected Configuration**:
- ✅ SchemaName: `dystudio_visionasset_assettags`
- ✅ Entity1: `dystudio_visionasset`
- ✅ Entity2: `dystudio_assettag`
- ✅ IntersectEntity: `dystudio_dystudio_visionasset_dystudio_assettag`

### 4.2 Relationship Navigation Testing

Assuming you have test records for both entities:

**Associate Tag with Asset**:
```http
POST https://{org}.crm.dynamics.com/api/data/v9.2/dystudio_assettags({tagid})/dystudio_assettag_visionassets/$ref
Content-Type: application/json

{
  "@odata.id": "/api/data/v9.2/dystudio_visionassets({assetid})"
}
```

**Navigate from Tag to Assets**:
```http
GET https://{org}.crm.dynamics.com/api/data/v9.2/dystudio_assettags({tagid})?$expand=dystudio_assettag_visionassets($select=dystudio_visionassetid,dystudio_name)
```

**Navigate from Asset to Tags**:
```http
GET https://{org}.crm.dynamics.com/api/data/v9.2/dystudio_visionassets({assetid})?$expand=dystudio_visionasset_assettags($select=dystudio_assettagid,dystudio_name)
```

**Expected Results**:
- ✅ Association created successfully
- ✅ Navigation works in both directions
- ✅ Proper data returned in expand queries

### 4.3 One-to-Many Relationship (Generation History to Vision Assets)

**Check Lookup Column Exists on Vision Asset**:
```http
GET https://{org}.crm.dynamics.com/api/data/v9.2/EntityDefinitions(LogicalName='dystudio_visionasset')/Attributes?$filter=LogicalName eq 'dystudio_generationhistoryid'
```

**Test Relationship Navigation**:
```http
GET https://{org}.crm.dynamics.com/api/data/v9.2/dystudio_generationhistories({genid})?$expand=dystudio_generationhistory_visionassets($select=dystudio_visionassetid,dystudio_name)
```

---

## 5. Performance and Security Verification

### 5.1 Audit Configuration Verification

**Check Table-Level Auditing**:
```http
GET https://{org}.crm.dynamics.com/api/data/v9.2/EntityDefinitions(LogicalName='dystudio_assettag')?$select=IsAuditEnabled
GET https://{org}.crm.dynamics.com/api/data/v9.2/EntityDefinitions(LogicalName='dystudio_generationhistory')?$select=IsAuditEnabled
```

**Check Column-Level Auditing**:
```http
GET https://{org}.crm.dynamics.com/api/data/v9.2/EntityDefinitions(LogicalName='dystudio_assettag')/Attributes?$filter=IsCustomAttribute eq true&$select=LogicalName,IsAuditEnabled
```

**Expected Results**:
- ✅ All custom tables have IsAuditEnabled = true
- ✅ All custom columns have IsAuditEnabled = true

### 5.2 Security Role Verification

**Test Basic CRUD Operations**:
For each table, verify the current user can:
- ✅ Create records
- ✅ Read records  
- ✅ Update records
- ✅ Delete records
- ✅ View audit history

**PowerShell Security Check**:
```powershell
# Check user's privileges on custom tables
$tables = @("dystudio_assettag", "dystudio_generationhistory", "dystudio_visionasset")

foreach ($table in $tables) {
    $privileges = Get-CrmEntityPrivileges -conn $conn -EntityLogicalName $table
    Write-Host "Privileges for $table : $($privileges -join ', ')"
}
```

### 5.3 Performance Testing

**Large Dataset Creation** (Optional):
```powershell
# Create 100 test asset tags for performance testing
for ($i = 1; $i -le 100; $i++) {
    $tagData = @{
        dystudio_name = "Performance Test Tag $i"
        dystudio_category = 100000000
        dystudio_description = "Performance testing tag number $i"
        dystudio_usage_count = $i
        dystudio_media_applicability = 100000000
    }
    
    New-CrmRecord -conn $conn -EntityLogicalName dystudio_assettag -Fields $tagData
}
```

**Query Performance Testing**:
```http
# Test view performance with large dataset
GET https://{org}.crm.dynamics.com/api/data/v9.2/dystudio_assettags?$orderby=dystudio_usage_count desc&$top=50

# Test filtered queries
GET https://{org}.crm.dynamics.com/api/data/v9.2/dystudio_assettags?$filter=dystudio_category eq 100000000&$top=50

# Test search queries
GET https://{org}.crm.dynamics.com/api/data/v9.2/dystudio_assettags?$filter=contains(dystudio_name,'test')
```

**Expected Performance**:
- ✅ Queries complete within 2-3 seconds
- ✅ Views load without timeout
- ✅ Alternate key lookups are fast (<1 second)

## Verification Completion Checklist

Use this final checklist to confirm all verification is complete:

### Core Infrastructure
- [ ] Vision-Design solution exists and is published
- [ ] All required security roles assigned
- [ ] Environment connectivity working

### Generation History Table  
- [ ] Table structure verified (16 columns)
- [ ] Global choices verified (RequestType, GenerationStatus)
- [ ] Alternate key on generation_id working
- [ ] System views created and functional
- [ ] CRUD operations working
- [ ] Auditing enabled and working

### Asset Tag Table
- [ ] Table structure verified (6 columns)  
- [ ] Global choices verified (TagCategory, MediaApplicability)
- [ ] Alternate key on name working and enforced
- [ ] System views created and functional
- [ ] CRUD operations working
- [ ] Auditing enabled and working

### Relationships
- [ ] M:N relationship between Asset Tags and Vision Assets working
- [ ] 1:N relationship from Generation History to Vision Assets working
- [ ] Navigation properties working in both directions
- [ ] Associated menus configured properly

### Integration and Performance
- [ ] Web API calls working for all tables
- [ ] PowerShell module connectivity working
- [ ] Query performance acceptable
- [ ] No security or permission errors

### UI and User Experience
- [ ] Tables accessible in model-driven apps
- [ ] Views display correctly
- [ ] Quick Find searches working
- [ ] Advanced Find queries working
- [ ] Form functionality working

## Status: ✅ VERIFICATION COMPLETE

When all checklist items are marked complete, the Vision Design Dataverse solution is fully verified and ready for production use.

## Next Steps After Verification

1. **Deploy to Additional Environments**: Export and import solution to test/production
2. **Configure Integrations**: Set up Power Automate flows, Canvas apps, etc.
3. **User Training**: Provide training on the new tables and functionality  
4. **Monitoring Setup**: Configure ongoing monitoring and maintenance procedures
5. **Documentation**: Update any additional user or admin documentation needed