# Vision Design

**AI-powered visual content creation prototype with GPT-Image-1, Sora, and Flux models—streamlined for rapid prototyping and professional design workflows.**

## Key Features

- **Multi-Model Support**: Generate content with GPT-Image-1, Sora, and Flux models (including Foundry-hosted models)
- **Advanced Authentication**: Integrated Azure CLI, PAC CLI, Connect-MGGraph, and GitHub authentication
- **Dataverse Integration**: Rich metadata storage and indexing with Power Platform integration
- **Streamlined Onboarding**: Simplified authentication flows for rapid setup
- **Professional Workflows**: Generate, edit, and manage visual assets with AI-powered enhancement
- **Brand Protection**: Content guardrails and moderation for professional use cases
- **Asset Management**: Organized gallery with advanced search and filtering capabilities

<img src="ui-sample.png" alt="description" width="800"/>

> You can also get started with our notebooks to explore the models and APIs:
>
> - Image generation: [gpt-image-1.ipynb](notebooks/gpt-image-1.ipynb)
> - Video generation: [sora-api-starter.ipynb](notebooks/sora-api-starter.ipynb)

## Prerequisites

**Azure & Power Platform Resources:**
- Azure OpenAI resource with deployed `gpt-image-1` model
- Azure OpenAI resource with deployed `Sora` model  
- Azure OpenAI `gpt-4o` model deployment (for prompt enhancement and analysis)
- Azure Storage Account with Blob Containers for assets
- Microsoft Dataverse environment for metadata storage
- (Optional) Foundry access for advanced Flux model hosting

**Authentication & CLI Tools:**
- Azure CLI (`az`) for Azure resource authentication
- Power Platform CLI (`pac`) for Dataverse integration
- Microsoft Graph PowerShell (`Connect-MgGraph`) for Microsoft 365 integration
- GitHub CLI (`gh`) for repository integration
- Git for version control

**Development Environment:**
- Python 3.12+
- Node.js 19+ and npm
- uv package manager
- Code editor (VSCode recommended)

## Step 1: Installation (One-time)

### Option A: Quick Start with GitHub Codespaces

The quickest way to get started is using GitHub Codespaces, a hosted environment that is automatically set up for you. Click this button to create a Codespace (4-core machine recommended):

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://github.com/codespaces/new?hide_repo_select=true&ref=main&repo=dayour/Vision-Design)

Wait for the Codespace to initialize. Python 3.12, Node.js 19, and dependencies will be automatically installed.

Now you can continue with [Step 2: Configure Resources.](#step-2-configure-resources)

### Option B: Local Installation on your device

#### 1. Clone the Repository

```bash
git clone https://github.com/dayour/Vision-Design
cd Vision-Design
```

#### 2. Backend Setup

##### 2.1 Install UV Package Manager

UV is a fast Python package installer and resolver that we use for managing dependencies.

Mac/Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows (using PowerShell):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

##### 2.2 Copy environment file template

```bash
cp .env.example .env
```

The environment variables will be defined below.

#### 3. Frontend Setup

```bash
cd frontend
npm install --legacy-peer-deps
```

## Step 2: Configure Resources

1. Configure Azure credentials using a code or text editor:

   ```bash
   code .env
   ```

   Replace the placeholders with your actual Azure values:

   | Service / Model   | Variables                                                                                                                                                                                                                                                                                                                                                                      |
   | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
   | **Sora**          | - `SORA_AOAI_RESOURCE`: name of the Azure OpenAI resource used for Sora <br> - `SORA_DEPLOYMENT`: deployment name for the Sora model <br> - `SORA_AOAI_API_KEY`: API key for the Azure OpenAI Sora resource                                                                                                                                                                    |
   | **GPT-Image-1**   | - `IMAGEGEN_AOAI_RESOURCE`: name of the Azure OpenAI resource used for gpt-image-1 <br> - `IMAGEGEN_DEPLOYMENT`: deployment name for the gpt-image-1 model <br> - `IMAGEGEN_AOAI_API_KEY`: API key for the gpt-image-1 resource                                                                                                                                                |
   | **GPT-4o**        | - `LLM_AOAI_RESOURCE`: name of the Azure OpenAI resource used for GPT-4o <br> - `LLM_DEPLOYMENT`: deployment name for the GPT-4o model <br> - `LLM_AOAI_API_KEY`: API key for the GPT-4o resource                                                                                                                                                                           |
   | **Flux Models**   | - `BFL_API_KEY`: Black Forest Labs API key for standard Flux models <br> - `FOUNDRY_API_KEY`: API key for Foundry-hosted Flux models <br> - `FOUNDRY_ENDPOINT`: Foundry API endpoint (e.g., `https://your-foundry.api.com`) <br> - `FLUX_MODEL_PROVIDER`: Model provider (`bfl` or `foundry`) |
   | **Azure Storage** | - `AZURE_BLOB_SERVICE_URL`: URL to your Azure Blob Storage service <br> - `AZURE_STORAGE_ACCOUNT_NAME`: name of your Azure Storage Account <br> - `AZURE_STORAGE_ACCOUNT_KEY`: access key for your Azure Storage Account <br> - `AZURE_BLOB_IMAGE_CONTAINER`: name of the Blob Container for images <br> - `AZURE_BLOB_VIDEO_CONTAINER`: name of the Blob Container for videos |
   | **Dataverse** | - `DATAVERSE_ENVIRONMENT_URL`: Your Dataverse environment URL (e.g., `https://your-env.crm.dynamics.com/`) <br> - `DATAVERSE_CLIENT_ID`: Azure AD app registration client ID <br> - `DATAVERSE_CLIENT_SECRET`: Azure AD app registration client secret <br> - `DATAVERSE_TABLE_NAME`: Custom table name for image metadata (default: `cr6f1_visionassets`) |
   | **Azure Cosmos DB** | - `AZURE_COSMOS_DB_ENDPOINT`: URL to your Azure Cosmos DB account (e.g., `https://your-account.documents.azure.com:443/`) <br> - `AZURE_COSMOS_DB_KEY`: Primary or secondary key for your Cosmos DB account <br> - `AZURE_COSMOS_DB_ID`: Database name (default: `visiondesign`) <br> - `AZURE_COSMOS_CONTAINER_ID`: Container name for metadata (default: `metadata`) <br> - `USE_MANAGED_IDENTITY`: Set to `false` for key-based auth or `true` for managed identity (default: `true`) |

> Note: For the best experience, use both Sora and GPT-Image-1. However, the app also works if you use only one of these models.

### Setting Up Dataverse Integration

Microsoft Dataverse provides rich relational data storage for image metadata, tags, and indexing capabilities:

#### Step 1: Create a Dataverse Environment
1. Go to [Power Platform Admin Center](https://admin.powerplatform.microsoft.com/)
2. Create a new environment or use an existing one
3. Ensure the environment has a Dataverse database

#### Step 2: Set Up Authentication
```bash
# Install Power Platform CLI
pac install latest

# Authenticate to your environment  
pac auth create --url https://your-env.crm.dynamics.com/

# Verify connection
pac org who
```

#### Step 3: Create Custom Tables (Optional)
The application will automatically create the required tables, or you can create them manually:
- **Vision Assets** (`cr6f1_visionassets`): Main table for image metadata
- **Asset Tags** (`cr6f1_assettags`): Tags and categories
- **Generation History** (`cr6f1_generationhistory`): AI generation audit trail

### Setting Up Azure Cosmos DB

Azure Cosmos DB is used to store metadata for your generated images and videos, enabling advanced features like:
- Asset organization and tagging
- Search and filtering capabilities  
- Analysis results storage
- Gallery management

#### Option 1: Using Managed Identity (Recommended for Azure deployments)

When deploying to Azure Container Apps or other Azure services, managed identity provides the most secure authentication method:

1. **Set environment variables:**
   ```bash
   USE_MANAGED_IDENTITY=true
   AZURE_COSMOS_DB_ENDPOINT=https://your-cosmos-account.documents.azure.com:443/
   AZURE_COSMOS_DB_ID=visionarylab
   AZURE_COSMOS_CONTAINER_ID=metadata
   ```

2. **Configure managed identity access:**
   - In the Azure portal, go to your Cosmos DB account
   - Navigate to **Access control (IAM)**
   - Add role assignment: **Cosmos DB Built-in Data Contributor** to your managed identity

#### Option 2: Using Access Keys (For local development)

For local development or when managed identity isn't available:

1. **Get your Cosmos DB connection details:**
   - In the Azure portal, go to your Cosmos DB account
   - Navigate to **Keys** under Settings
   - Copy the **URI** and **Primary Key**

2. **Set environment variables:**
   ```bash
   USE_MANAGED_IDENTITY=false
   AZURE_COSMOS_DB_ENDPOINT=https://your-cosmos-account.documents.azure.com:443/
   AZURE_COSMOS_DB_KEY=your-primary-key-here
   AZURE_COSMOS_DB_ID=visionarylab
   AZURE_COSMOS_CONTAINER_ID=metadata
   ```

#### Creating the Database and Container

The application will automatically create the database and container if they don't exist. However, you can create them manually:

1. **Create Database:**
   - Database ID: `visiondesign` (updated from visionarylab)
   - Throughput: Shared (400 RU/s minimum)

2. **Create Container:**
   - Container ID: `metadata` (or your custom name)
   - Partition key: `/media_type`
   - Throughput: Use database shared throughput

> **Note:** Cosmos DB is **required** for the gallery and asset management features to work properly.

## Step 3: Running the Application

Once everything is set up:

1. Start the backend:

   ```bash
   cd backend
   uv run fastapi dev
   ```

   The backend server will start on http://localhost:8000. You can verify it's running by visiting http://localhost:8000/api/v1/health in your browser.

   **Note:**  
   If you encounter the error: `ImportError: libGL.so.1: cannot open shared object file: No such file or directory`, install the missing OpenCV library:

   ```bash
   sudo apt update
   sudo apt install libgl1-mesa-glx
   ```

   This step is not needed in Codespaces as it's automatically installed

2. Open a new terminal to start the frontend:

   ```bash
   cd frontend
   npm run build
   npm start
   ```

   The frontend will be available at http://localhost:3000.

## 🚀 Deploy to Azure

For production deployment, use Azure Developer CLI to deploy the entire application to Azure with one command:

**Prerequisites**: [Azure Developer CLI (azd)](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd) installed

```bash
# Clone and deploy
git clone https://github.com/Azure-Samples/visionary-lab
cd visionary-lab

# Authenticate and deploy everything in one command
azd auth login
azd up
```

During `azd up`, you'll be prompted to configure your Azure OpenAI resources:
- **LLM Configuration**: Resource name, deployment name (e.g., "gpt-4.1"), and API key
- **Image Generation Configuration**: Resource name, deployment name (e.g., "gpt-image-1"), and API key
- **Sora Configuration**: Resource name, deployment name (e.g., "sora"), and API key

✨ That's it! Your Visionary Lab will be running on Azure Container Apps with:
- Azure Container Registry for Docker images
- Azure Storage for generated content
- Automatic scaling and monitoring

📖 For detailed deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md)
