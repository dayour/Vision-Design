# Copilot Instructions for Vision-Design

## Project Overview
AI visual content creation platform with GPT-Image-1, Sora, and Flux models. Fork of Azure-Samples/visionary-lab with Dataverse integration.

## Architecture
- `backend/` - Python FastAPI backend (uv package manager)
- `frontend/` - Next.js/React frontend
- `notebooks/` - Jupyter model exploration
- `infra/` - Azure Bicep (azd deployable)

## Code Style
- Python backend: FastAPI, uv, pyproject.toml
- TypeScript frontend: Next.js, npm
- Azure Cosmos DB for metadata, Blob Storage for assets
- Docker Compose for local dev, azd for deployment
