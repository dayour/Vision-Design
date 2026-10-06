# Dataverse Setup Guide

## Overview

This guide provides the foundational setup procedures for the Vision Design solution in Microsoft Dataverse. It covers environment preparation, solution creation, and general configuration requirements.

## Prerequisites

### Environment Requirements
- **Microsoft Dataverse Environment**: Production or sandbox environment with maker permissions
- **Security Roles**: System Administrator or System Customizer role required
- **PowerShell Modules** (for automated setup):
  - `Microsoft.Xrm.Data.PowerShell`
  - `Microsoft.PowerPlatform.Administration.PowerShell`

### Access Requirements
- **Power Apps Maker Portal**: https://make.powerapps.com
- **Dataverse Web API Access**: For programmatic operations
- **PowerShell Execution Policy**: Set to allow script execution

## Solution Information

### Core Details
- **Solution Display Name**: Vision-Design
- **Solution Unique Name**: VisionDesign
- **Solution ID**: `880baf0b-9b9d-f011-bbd2-6045bd02d5d6`
- **Publisher Prefix**: dystudio
- **Dataverse Web API Version**: v9.2
- **Base URL Pattern**: `https://{org}.crm.dynamics.com/api/data/v9.2`

### Publisher Configuration
- **Display Name**: DYStudio  
- **Name**: dystudio
- **Prefix**: dystudio
- **Option Value Prefix**: 10000

## Initial Environment Setup

### 1. Verify Environment Access

**PowerShell Verification**:
```powershell
# Install required modules
Install-Module Microsoft.Xrm.Data.PowerShell -Force -AllowClobber
Install-Module Microsoft.PowerPlatform.Administration.PowerShell -Force

# Connect to environment
$conn = Get-CrmConnection -InteractiveMode

# Verify connection
Get-CrmOrganization -conn $conn
```

**Web API Verification**:
```http
GET https://{org}.crm.dynamics.com/api/data/v9.2/WhoAmI
Authorization: Bearer {access_token}
```

### 2. Create or Verify Solution

#### Via PowerShell
```powershell
# Check if solution exists
$existingSolution = Get-CrmRecords -conn $conn -EntityLogicalName solution -FilterAttribute uniquename -FilterOperator eq -FilterValue "VisionDesign"

if ($existingSolution.CrmRecords.Count -eq 0) {
    # Create new solution
    $solutionData = @{
        uniquename = "VisionDesign"
        friendlyname = "Vision-Design"
        description = "AI-powered vision and media generation solution"
        version = "1.0.0.0"
        publisherid = @{
            logicalname = "publisher"
            uniquename = "dystudio"
        }
    }
    
    New-CrmRecord -conn $conn -EntityLogicalName solution -Fields $solutionData
}
```

#### Via Maker Portal
1. Navigate to **Solutions** → **+ New solution**
2. Enter details:
   - **Display name**: Vision-Design
   - **Name**: VisionDesign
   - **Publisher**: Create new publisher "DYStudio" with prefix "dystudio"
   - **Version**: 1.0.0.0
3. Click **Create**

### 3. Configure Publisher (if new)

**Publisher Settings**:
```json
{
  "uniquename": "dystudio",
  "friendlyname": "DYStudio",  
  "customizationprefix": "dystudio",
  "customizationoptionvalueprefix": 10000,
  "description": "Publisher for Vision Design AI solutions"
}
```

## Environment Configuration

### 1. Enable Required Features

**Auditing Configuration**:
```powershell
# Enable organization-wide auditing
Set-CrmAuditConfiguration -conn $conn -AuditEnabled $true -UserAccess $true

# Enable audit for custom entities (will be set per table)
```

**Advanced Find Configuration**:
```powershell
# Ensure Advanced Find is enabled for custom entities
# This is typically enabled by default
```

### 2. Security Role Setup

Create custom security role or modify existing ones to include:

**Table Permissions** (for Vision Design tables):
- **dystudio_generationhistory**: Create, Read, Write, Delete, Append, Append To
- **dystudio_assettag**: Create, Read, Write, Delete, Append, Append To  
- **dystudio_visionasset**: Create, Read, Write, Delete, Append, Append To

**System Permissions**:
- **Bulk Delete**: For data management operations
- **View Audit History**: For compliance tracking
- **Create Quick Forms**: For UI customizations

### 3. Environment Variables (Optional)

Define environment-specific configuration:

```powershell
# Create environment variables for API endpoints, keys, etc.
$envVarData = @{
    schemaname = "dystudio_OpenAIApiEndpoint"
    displayname = "OpenAI API Endpoint"
    type = 100000000  # String
    defaultvalue = "https://api.openai.com/v1"
    description = "Base URL for OpenAI API calls"
}

New-CrmRecord -conn $conn -EntityLogicalName environmentvariabledefinition -Fields $envVarData
```

## Data Model Overview

### Core Tables Structure
```
dystudio_visionasset (Vision Asset)
├── 1:N → dystudio_generationhistory (Generation History)  
└── N:N → dystudio_assettag (Asset Tag)
```

### Relationships Summary
- **Generation History** tracks AI generation requests and links to resulting assets
- **Asset Tags** provide flexible categorization and metadata for assets
- **Vision Assets** are the central entity storing generated media files

### Global Choice Sets
- `dystudio_RequestType`: Image, Video, Image Edit
- `dystudio_GenerationStatus`: Pending, In Progress, Completed, Failed, Cancelled  
- `dystudio_TagCategory`: Style, Subject, Color, Mood, Brand, Object, Location
- `dystudio_MediaApplicability`: Image, Video, Both

## Deployment Strategy

### Development → Test → Production

#### 1. Development Environment
- Create and test all components
- Validate functionality with sample data
- Configure and test integrations

#### 2. Test Environment  
- Import managed solution from development
- Run comprehensive testing
- Performance and load testing
- User acceptance testing

#### 3. Production Environment
- Import final managed solution
- Configure environment-specific settings
- Set up monitoring and maintenance
- Deploy user training and documentation

### Solution Export/Import

**Export Managed Solution**:
```powershell
Export-CrmSolution -conn $conn -SolutionName "VisionDesign" -SolutionFilePath "C:\temp\VisionDesign_1_0_0_0_managed.zip" -Managed $true
```

**Import Solution**:
```powershell
Import-CrmSolution -conn $conn -SolutionFilePath "C:\temp\VisionDesign_1_0_0_0_managed.zip"
```

## Post-Setup Configuration

### 1. Model-Driven App Setup
Create or configure model-driven apps to include Vision Design tables:

**App Configuration**:
```json
{
  "name": "Vision Design Studio",
  "description": "AI-powered media generation and management",  
  "tables": [
    "dystudio_visionasset",
    "dystudio_generationhistory", 
    "dystudio_assettag"
  ],
  "sitemap": {
    "areas": [
      {
        "title": "Generation",
        "groups": [
          {
            "title": "AI Generation",
            "subareas": ["dystudio_generationhistory", "dystudio_visionasset"]
          }
        ]
      },
      {
        "title": "Management", 
        "groups": [
          {
            "title": "Organization",
            "subareas": ["dystudio_assettag"]
          }
        ]
      }
    ]
  }
}
```

### 2. Power Automate Integration
Configure flows for:
- **Generation Status Updates**: Update generation history as AI jobs progress
- **Asset Tag Automation**: Auto-tag assets based on content analysis
- **Cost Tracking**: Calculate and update estimated costs
- **Notifications**: Alert users of completed/failed generations

### 3. Canvas App Integration (Optional)
Create canvas apps for:
- **Generation Dashboard**: Visual status tracking and analytics
- **Tag Management**: Bulk tag operations and organization
- **Asset Gallery**: Rich media viewing and management

## Monitoring and Maintenance

### 1. Audit Configuration
```powershell
# Verify audit settings are properly configured
Get-CrmAuditConfiguration -conn $conn

# Check audit log size and retention
Get-CrmAuditLogRecordCount -conn $conn
```

### 2. Performance Monitoring
- **Database Storage**: Monitor table growth and optimize indexes
- **API Usage**: Track Web API calls and rate limiting
- **Integration Performance**: Monitor Power Automate flow execution times

### 3. Security Review
- **Role Assignments**: Regular review of user permissions
- **Field Security**: Protect sensitive data fields
- **Connection Security**: Secure API keys and connection strings

## Troubleshooting

### Common Setup Issues

#### Solution Import Failures
```powershell
# Check solution dependencies
Get-CrmSolutionComponentDependencies -conn $conn -SolutionName "VisionDesign"

# Import with error suppression (use carefully)
Import-CrmSolution -conn $conn -SolutionFilePath $path -OverwriteUnmanagedCustomizations $true
```

#### Publisher Prefix Issues
- Ensure all custom components use consistent "dystudio_" prefix
- Check option value prefixes start with 10000+
- Verify no conflicts with existing publishers

#### Permission Errors
```powershell
# Check user's security roles
Get-CrmUserSecurityRoles -conn $conn -UserId $userId

# Verify table permissions
Get-CrmEntityPrivileges -conn $conn -EntityLogicalName "dystudio_visionasset"
```

### Performance Optimization
- **Indexes**: Ensure proper indexing on frequently queried fields
- **Views**: Optimize FetchXML queries in system views
- **Relationships**: Review cascade settings for performance impact
- **Bulk Operations**: Use bulk APIs for large data operations

## Next Steps

After completing the basic Dataverse setup:

1. [Set up Generation History Table](./generation-history-table.md)
2. [Set up Asset Tag Table](./asset-tag-table.md)  
3. [Run Verification Procedures](./verification-procedures.md)
4. Configure integrations and workflows
5. Deploy to additional environments
6. Set up monitoring and maintenance procedures

## Support and Resources

### Documentation
- [Microsoft Dataverse Developer Guide](https://docs.microsoft.com/power-apps/developer/data-platform/)
- [Power Platform Admin Guide](https://docs.microsoft.com/power-platform/admin/)

### Tools
- **Power Apps Maker Portal**: https://make.powerapps.com
- **Power Platform Admin Center**: https://admin.powerplatform.microsoft.com  
- **Dataverse REST Builder**: For testing Web API calls
- **FetchXML Builder**: For advanced query development

### Community
- **Power Platform Community**: https://powerusers.microsoft.com
- **GitHub Issues**: Report issues with this solution setup
- **Documentation Feedback**: Submit improvements and corrections