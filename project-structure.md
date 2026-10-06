# Vision Design Project Structure

## Overview
Vision Design is a multimodal AI content generation platform supporting both video generation (Azure OpenAI Sora) and image generation (Flux via Foundry, GPT-Image-1). It features a hybrid architecture with a Python FastAPI backend and a Next.js frontend, plus development/management scripts for service orchestration.

## Core Components

### 1. Backend (Python/FastAPI)
- **FastAPI Framework**: Main API server in `backend/main.py`
- **API Endpoints**: Structured in `backend/api/endpoints/` with routes for:
  - **Videos**: Sora video generation and management
  - **Images**: Comprehensive image generation pipeline (generate, edit, save, analyze)
  - **Gallery**: Media asset gallery with Dataverse integration
  - **Flux**: Direct Flux API endpoints for image generation
  - **Metadata**: Asset metadata management
  - **Auth Status**: CLI tool authentication status
  - **Environment**: Configuration validation
  - **Dataverse**: Direct Dataverse operations
- **Core Services**: Consolidated in `backend/core/`:
  - `sora.py`: Azure OpenAI Sora video generation client
  - `flux_client.py`: Flux model client (Foundry/BFL API support)
  - `gpt_image.py`: GPT-Image-1 client for image generation
  - `image_pipeline.py`: Unified pipeline for image generation, editing, saving, and analysis
  - `dataverse_service.py`: Microsoft Dataverse integration for metadata storage
  - `dataverse_client.py`: Low-level Dataverse API client
  - `storage.py`: File storage and management
  - `analyze.py`: Image analysis using LLM
  - `auth_helpers.py`: Authentication utilities
  - `instructions.py`: System prompts for LLM operations
  - `config.py`: Application configuration with environment variables
  - `__init__.py`: Centralized service initialization
- **Models**: Data models in `backend/models/`
  - `videos.py`: Schemas for video generation endpoints
  - `images.py`: Comprehensive schemas for image pipeline (generation, editing, saving, analysis)
  - `gallery.py`: Gallery and asset schemas
  - `metadata_models.py`: Dataverse metadata models
  - `common.py`: Shared schema definitions
- **Static Files**: Served from `static/` directory for:
  - Generated videos
  - Uploaded and generated images
  - Other static assets
- **Tools**: Utility scripts in `backend/tools/`
  - `create_dataverse_tables.py`: Dataverse schema setup
  - `test_dataverse_connection.py`: Connection verification

### 2. Frontend (Next.js)
- **Modern React (v19)**: Latest React framework
- **Next.js 15.2.4**: App router architecture with Turbopack
- **Tailwind CSS**: For styling
- **UI Components**: 
  - Radix UI primitives
  - Shadcn/ui component library
  - Custom components in `frontend/components/`
- **Key Pages**:
  - Home/Dashboard: Landing page
  - New Image: Image generation interface
  - New Video: Video generation interface
  - Edit Image: Image editing tools
  - Analyze: Image analysis tools
  - Gallery: Unified media gallery
  - Jobs: Background job management
  - Settings: Configuration and authentication
  - Test Simple: Testing utilities
- **Context API**: State management in `frontend/context/`
  - `GalleryContext.tsx`: Gallery state management
  - `JobsContext.tsx`: Background jobs tracking
- **API Services**: API integrations in `frontend/services/`
  - `api.ts`: Comprehensive API client
  - `imageService.ts`: Image operations
  - `videoService.ts`: Video operations
  - `authService.ts`: Authentication
- **Utilities**: Helper functions in `frontend/utils/`
- **Hooks**: Custom React hooks in `frontend/hooks/`
- **Types**: TypeScript type definitions in `frontend/types/`

### 3. Management Scripts (vision-design2.0/)
- **Service Management**:
  - `restart-services.ps1`: Stop all running services cleanly
  - `start-backend.ps1`: Start FastAPI backend on port 8000
  - `start-frontend.ps1`: Start Next.js frontend on port 3000
- **Testing Scripts**:
  - `test_flux.py`: Direct Flux API integration test
  - `test-pipeline.ps1`: Image pipeline endpoint test
- **Documentation**:
  - `SESSION_SUMMARY.md`: Complete session summary with fixes and status
  - `README.md`: Script usage guide and workflow

### 4. Core Image Generation Functionality
- **Multiple Provider Support**:
  - **Flux Models** (via Foundry or BFL):
    - FLUX-1.1-pro: High-quality image generation
    - FLUX.1-pro-ultra: Ultra-high-quality with aspect ratio control
    - FLUX.1-Kontext-pro: Context-aware image editing
  - **GPT-Image-1** (via OpenAI):
    - Direct OpenAI API integration
    - Quality, format, and compression controls
- **Unified Image Pipeline**:
  - Generate: Create new images from prompts
  - Edit: Modify existing images
  - Save: Store images with metadata in Dataverse
  - Analyze: LLM-powered image analysis
- **Features**:
  - Width/height parsing from size parameter for Flux
  - Async generation with polling
  - Base64 and URL response formats
  - Prompt enhancement and brand protection
  - Filename generation based on content
### 5. Core Video Functionality
- **Sora Integration**: Client for Azure OpenAI's Sora in `backend/core/sora.py`
  - Centralized client initialization in `backend/core/__init__.py`
  - API connection handled using settings from `backend/core/config.py`
- **Video Processing**:
  - Download/export of generated videos
  - File management with proper error handling
  - Job status tracking and polling
- **Storage**: Local file storage with organized directories

### 6. External Dependencies
- **Azure Services**:
  - Azure OpenAI (Sora model for video generation)
  - Azure OpenAI (LLM for analysis and prompt enhancement)
  - Azure AI Foundry (Flux models for image generation)
- **Microsoft Dataverse**:
  - Metadata storage for images and videos
  - Asset management and tagging
  - Generation history tracking
- **OpenAI API**:
  - GPT-Image-1 for image generation (optional)
  - Direct API integration
- **Black Forest Labs (BFL)**:
  - Alternative Flux model provider (optional)

### 7. Configuration
- **Environment Variables**: Comprehensive configuration in `.env` file:
  - **Sora (Video)**:
    - `SORA_AOAI_RESOURCE`: Azure OpenAI resource for Sora
    - `SORA_DEPLOYMENT`: Sora deployment name
    - `SORA_AOAI_API_KEY`: API key for Sora
  - **Flux (Image - Foundry)**:
    - `FLUX_MODEL_PROVIDER`: "foundry" or "bfl"
    - `FOUNDRY_API_KEY`: Azure AI Foundry API key
    - `FOUNDRY_ENDPOINT`: Foundry service endpoint
    - `FOUNDRY_DEPLOYMENT_FLUX_PRO`: Deployment name
    - `FOUNDRY_FLUX_PRO_ENDPOINT`: Full generation endpoint URL
  - **GPT-Image-1** (optional):
    - `OPENAI_API_KEY`: OpenAI API key
    - `OPENAI_ORG_ID`: Organization ID
  - **LLM (Analysis)**:
    - `LLM_AOAI_RESOURCE`: Azure OpenAI resource
    - `LLM_DEPLOYMENT`: Deployment name (GPT-4o recommended)
    - `LLM_AOAI_API_KEY`: API key
  - **Dataverse**:
    - `DATAVERSE_ENVIRONMENT_URL`: Environment URL
    - `DATAVERSE_CLIENT_ID`: Azure AD app ID
    - `DATAVERSE_CLIENT_SECRET`: Client secret
    - `DATAVERSE_USE_MANAGED_IDENTITY`: Use managed identity (true/false)
    - Table and field configuration
- **Frontend Environment** (`frontend/.env.local`):
  - `NEXT_PUBLIC_API_URL`: Backend API URL
  - `NEXT_PUBLIC_FLUX_MODEL_PROVIDER`: Model provider
  - `NEXT_PUBLIC_DEFAULT_IMAGE_MODEL`: Default model
  - `NEXT_PUBLIC_DEBUG_MODE`: Enable debug logging
- **API Configuration**: Settings in `backend/core/config.py`
- **Environment Validation**: Status check via `/api/v1/auth/status` endpoint

### 8. Development Tools
- **Python 3.13**: Modern Python with type hints
- **Package Management**:
  - `pyproject.toml`: Python project configuration
  - `requirements.txt`: Python dependencies
  - `package.json`: JavaScript/TypeScript dependencies
- **Development Scripts**:
  - `vision-design2.0/`: Clean working scripts collection
  - `restart-services.ps1`: Service management
  - `start-backend.ps1`: Backend launcher
  - `start-frontend.ps1`: Frontend launcher
- **Testing Tools**:
  - `test_flux.py`: Direct API testing
  - `test-pipeline.ps1`: Endpoint testing
  - Vitest for frontend testing
- **Development Servers**:
  - Backend: uvicorn with hot reload (port 8000)
  - Frontend: Next.js dev server with Turbopack (port 3000)

## API Endpoints

### Images Endpoints (`/api/v1/images`)
- **GET /test**: Test endpoint for API verification
- **POST /generate**: Generate images using Flux or GPT-Image-1
- **POST /edit**: Edit existing images
- **POST /pipeline**: Unified pipeline for generate/edit/save/analyze workflow
- **POST /generate-with-analysis**: Generate, save, and analyze in one call
- **POST /save**: Save generated images to Dataverse with metadata
- **POST /analyze**: Analyze image content using LLM
- **POST /analyze/custom**: Custom image analysis with specific instructions
- **POST /prompt/enhance**: Enhance prompts for better results
- **POST /prompt/brand-protect**: Neutralize or replace brand references
- **POST /filename/generate**: Generate semantic filename from image content
- **POST /list**: List available images
- **POST /delete**: Delete images

### Videos Endpoints (`/api/v1/videos`)
- **POST /jobs**: Create a video generation job with Sora
- **GET /jobs/{job_id}**: Get status of a specific generation job
- **GET /jobs**: List all video generation jobs
- **DELETE /jobs/{job_id}**: Delete a specific job
- **DELETE /jobs/failed**: Clean up failed jobs
- **GET /generations/{generation_id}/content**: Download generated video or GIF
- **POST /analyze**: Video content analysis
- **POST /filename/generate**: Generate filename based on video content

### Flux Endpoints (`/api/v1/flux`)
- **POST /generate**: Direct Flux image generation
- **GET /job/{job_id}**: Get Flux generation job status
- **GET /health**: Check Flux client health

### Gallery Endpoints (`/api/v1/gallery`)
- **GET /health**: Gallery service health check
- **GET /images**: List image assets from Dataverse
- **GET /videos**: List video assets from Dataverse
- **GET /assets/{asset_id}**: Get specific asset metadata
- **DELETE /assets/{asset_id}**: Delete asset
- **GET /assets/{asset_id}/content**: Download asset content
- **GET /folders**: List available folders/albums
- **POST /assets/{asset_id}/tags**: Add tags to asset
- **DELETE /assets/{asset_id}/tags**: Remove tags from asset

### Metadata Endpoints (`/api/v1/metadata`)
- **POST /assets**: Create new asset metadata
- **GET /assets/{asset_id}**: Retrieve asset metadata
- **PUT /assets/{asset_id}**: Update asset metadata
- **DELETE /assets/{asset_id}**: Delete asset metadata
- **GET /assets**: List all assets with filtering
- **POST /tags**: Create new tag
- **GET /tags**: List all tags

### Dataverse Endpoints (`/api/v1/dataverse`)
- **GET /status**: Check Dataverse connection status
- **GET /tables**: List configured Dataverse tables

### Auth Status Endpoints (`/api/v1/auth`)
- **GET /status**: Check authentication status for CLI tools (pac, az, gh, dataverse)

### Environment Endpoints (`/api/v1/env`)
- **GET /status**: Check the status of required environment variables

## Data Flow

### Image Generation Flow
1. User submits prompt via frontend (New Image page)
2. Frontend sends request to `/api/v1/images/pipeline`
3. Backend parses size string to width/height for Flux models
4. ImagePipelineService coordinates:
   - **Generate**: Flux/GPT-Image-1 creates images
   - **Save** (optional): Stores metadata in Dataverse
   - **Analyze** (optional): LLM analyzes image content
5. Images returned as base64 or URLs
6. Frontend displays results in gallery

### Video Generation Flow
1. User submits prompt via frontend (New Video page)
2. Request sent to `/api/v1/videos/jobs`
3. Backend initiates Sora generation job
4. Job ID returned immediately
5. Frontend polls job status
6. Video downloaded when ready
7. Stored in static directory and served

### Gallery Flow
1. Frontend requests assets from `/api/v1/gallery/images` or `/videos`
2. Backend queries Dataverse for metadata
3. Asset content served from Dataverse or local storage
4. Frontend displays in unified gallery view
5. User can view, download, or delete assets

## Development Workflow

### Quick Start
```powershell
# 1. Stop all services
.\vision-design2.0\restart-services.ps1

# 2. Start backend (separate terminal)
.\vision-design2.0\start-backend.ps1

# 3. Start frontend (separate terminal)
cd frontend
npm run dev
```

### Testing
```powershell
# Test backend health
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health"

# Test images endpoint
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/images/test"

# Test Flux directly
C:/Python313/python.exe vision-design2.0/test_flux.py

# Test pipeline endpoint
.\vision-design2.0\test-pipeline.ps1
```

### Debugging
- Backend logs visible in terminal running `start-backend.ps1`
- Frontend logs in browser console and terminal
- API documentation at http://localhost:8000/docs
- Enhanced logging in pipeline endpoint for troubleshooting

## Environment Setup

### Prerequisites
- Python 3.13 or higher
- Node.js 18 or higher
- Azure OpenAI access (Sora model)
- Azure AI Foundry access (Flux models)
- Microsoft Dataverse environment (optional but recommended)

### Backend Setup
1. Copy `.env.example` to `.env` in project root
2. Configure required services:
   ```env
   # Sora (Required for video)
   SORA_AOAI_RESOURCE=your-resource
   SORA_DEPLOYMENT=your-deployment
   SORA_AOAI_API_KEY=your-key
   
   # Flux via Foundry (Required for image)
   FLUX_MODEL_PROVIDER=foundry
   FOUNDRY_API_KEY=your-key
   FOUNDRY_ENDPOINT=https://your-endpoint.ai.azure.com
   FOUNDRY_DEPLOYMENT_FLUX_PRO=FLUX-1.1-pro
   
   # LLM (Required for analysis)
   LLM_AOAI_RESOURCE=your-resource
   LLM_DEPLOYMENT=gpt-4o
   LLM_AOAI_API_KEY=your-key
   
   # Dataverse (Optional)
   DATAVERSE_ENVIRONMENT_URL=https://yourorg.crm.dynamics.com/
   DATAVERSE_CLIENT_ID=your-app-id
   DATAVERSE_CLIENT_SECRET=your-secret
   ```
3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Frontend Setup
1. Navigate to frontend directory: `cd frontend`
2. Create `.env.local`:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
   NEXT_PUBLIC_FLUX_MODEL_PROVIDER=foundry
   NEXT_PUBLIC_DEFAULT_IMAGE_MODEL=flux-pro
   NEXT_PUBLIC_DEBUG_MODE=true
   ```
3. Install dependencies:
   ```bash
   npm install
   ```

### Dataverse Setup (Optional)
1. Run table creation script:
   ```bash
   python backend/tools/create_dataverse_tables.py
   ```
2. Verify connection:
   ```bash
   python backend/tools/test_dataverse_connection.py
   ```
3. Tables created:
   - `dystudio_visionassets`: Main asset storage
   - `dystudio_assettags`: Tagging system
   - `dystudio_generationhistories`: Generation tracking

## Recent Improvements

### Fixed Issues
- ✅ Width/height parsing for Flux models from size parameter
- ✅ Removed undefined `image_sas_token` variable references
- ✅ Added comprehensive logging to image pipeline
- ✅ Created test endpoint for API verification
- ✅ Fixed syntax errors in videos.py
- ✅ Service management scripts for clean restart

### Known Issues
- ⚠️ Image generation returns 500 error from UI (under investigation)
- ⚠️ Gallery returns 503 when Dataverse not configured
- ⚠️ Folders endpoint returns 404 (not implemented)
- ⚠️ Authentication status shows 0/4 (CLI tools not installed)

### In Progress
- 🔄 Debugging image generation 500 error
- 🔄 Making Dataverse optional for basic operation
- 🔄 Comprehensive UI testing with automated tools
- 🔄 Error handling improvements

## Additional Resources
- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Session Summary**: `vision-design2.0/SESSION_SUMMARY.md`
- **Script Guide**: `vision-design2.0/README.md`
- **Dataverse Setup**: `docs/dataverse-setup.md`
- **Backend Guide**: `START_BACKEND.md`
- **Docker Guide**: `DOCKER.md` 