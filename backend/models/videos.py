from pydantic import BaseModel, Field
from typing import List, Optional, Dict

# Models used by video API endpoints


class VideoPromptEnhancementRequest(BaseModel):
    """Request model for enhancing video generation prompts"""
    original_prompt: str = Field(...,
                                 description="Prompt to enhance for video generation")


class VideoPromptEnhancementResponse(BaseModel):
    """Response model for enhanced video generation prompts"""
    enhanced_prompt: str = Field(...,
                                 description="Enhanced prompt for video generation")


class VideoGenerationRequest(BaseModel):
    """Request model for generating videos using Sora"""
    prompt: str = Field(...,
                        description="Prompt describing the video to generate")
    n_variants: int = Field(
        1, description="Number of video variants to generate")
    n_seconds: int = Field(10, description="Length of the video in seconds")
    height: int = Field(720, description="Height of the video in pixels")
    width: int = Field(1280, description="Width of the video in pixels")
    has_source_images: Optional[bool] = Field(
        False, description="Whether source images are included")
    image_count: Optional[int] = Field(
        None, description="Number of source images")


class VideoGenerationJobResponse(BaseModel):
    """Response model for a video generation job"""
    id: str = Field(..., description="Job ID")
    status: str = Field(..., description="Current status of the job")
    prompt: str = Field(..., description="Original prompt used for generation")
    n_variants: int = Field(...,
                            description="Number of video variants requested")
    n_seconds: int = Field(..., description="Length of the video in seconds")
    height: int = Field(..., description="Height of the video in pixels")
    width: int = Field(..., description="Width of the video in pixels")
    generations: Optional[list] = Field(
        None, description="List of generated videos")
    created_at: Optional[int] = Field(
        None, description="Unix timestamp of creation time")
    finished_at: Optional[int] = Field(
        None, description="Unix timestamp of completion time")
    failure_reason: Optional[str] = Field(
        None, description="Reason for failure if job failed")


class VideoAnalyzeRequest(BaseModel):
    """Request model for analyzing video content"""
    video_path: str = Field(...,
                            description="Path to the video file on Azure Blob Storage. Supports a full URL with or without a SAS token.")


class VideoAnalyzeResponse(BaseModel):
    """Response model for video analysis results"""
    summary: str = Field(..., description="Summary of the video content")
    products: str = Field(..., description="Products identified in the video")
    tags: List[str] = Field(...,
                            description="List of metadata tags for the video")
    feedback: str = Field(...,
                          description="Feedback on the video quality/content")


class VideoFilenameGenerateRequest(BaseModel):
    """Request model for generating a filename based on content"""
    prompt: str = Field(...,
                        description="Prompt describing the content to name")
    gen_id: Optional[str] = Field(
        None, description="Video generation id for unique naming"
    )
    extension: Optional[str] = Field(
        None, description="File extension for the generated filename, e.g., .mp4"
    )


class VideoFilenameGenerateResponse(BaseModel):
    """Response model for filename generation"""
    filename: str = Field(..., description="Generated filename")


class VideoGenerationWithAnalysisRequest(BaseModel):
    """Request model for generating videos with optional analysis"""
    prompt: str = Field(...,
                        description="Prompt describing the video to generate")
    n_variants: int = Field(
        1, description="Number of video variants to generate")
    n_seconds: int = Field(10, description="Length of the video in seconds")
    height: int = Field(720, description="Height of the video in pixels")
    width: int = Field(1280, description="Width of the video in pixels")
    analyze_video: bool = Field(
        False, description="Whether to analyze the generated videos")
    metadata: Optional[Dict[str, str]] = Field(
        None, description="Additional metadata for the job")


class VideoGenerationWithAnalysisResponse(BaseModel):
    """Response model for video generation with analysis"""
    job: VideoGenerationJobResponse = Field(...,
                                            description="Video generation job details")
    analysis_results: Optional[List[VideoAnalyzeResponse]] = Field(
        None, description="Analysis results for each generated video (if analysis was requested)")
    upload_results: Optional[List[Dict[str, str]]] = Field(
        None, description="Upload results for each video to gallery")
