// Image service - handles all image-related API calls
import { API_BASE_URL, ImageSaveResponse as ApiImageSaveResponse } from './api';
import type { ImageGenerationResponse } from './api';

export type { ImageGenerationResponse } from './api';

interface PromptEnhancementResponse {
  enhanced_prompt: string;
}

/**
 * Edit an image with a mask using OpenAI's GPT-4 Vision API
 */
export async function editImage(formData: FormData): Promise<ImageGenerationResponse> {
  console.log(`Making request to ${API_BASE_URL}/images/edit/upload`);
  
  try {
    // Call the backend API directly
    const response = await fetch(`${API_BASE_URL}/images/edit/upload`, {
      method: 'POST',
      headers: {
        // No Content-Type header as the browser sets it automatically with the correct boundary for FormData
      },
      // Don't include credentials for '*' origin setting
      // credentials: 'include',
      body: formData,
      mode: 'cors',  // Explicitly set CORS mode
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Error from backend API: ${response.status} - ${errorText}`);
      throw new Error(`Failed to edit image: ${response.status} - ${errorText}`);
    }
    
    return response.json();
  } catch (error) {
    console.error('Fetch error in editImage:', error);
    throw error;
  }
}

/**
 * Save a generated image to the gallery
 */
export async function saveGeneratedImage(
  generationResponse: ImageGenerationResponse,
  options: {
    prompt?: string;
    model?: string;
    size?: string;
    background?: string;
    output_format?: string;
    save_all?: boolean;
    folder_path?: string;
    analyze?: boolean; // NEW: request backend analysis
  }
): Promise<ApiImageSaveResponse> {
  // Import the saveGeneratedImages function from api.ts
  const { saveGeneratedImages } = await import('./api');
  
  try {
    if (!generationResponse?.imgen_model_response?.data ||
        generationResponse.imgen_model_response.data.length === 0) {
      throw new Error('No image data found in generation response');
    }

    // Call the saveGeneratedImages function with the full generation response
    return await saveGeneratedImages(
      generationResponse,
      options.prompt || '',
      options.save_all || false,
      options.folder_path || '',
      options.output_format || 'png',
      options.model || 'gpt-image-1',
      options.background || 'auto',
      options.size || '1024x1024',
      options.analyze ?? true // default to true to match older behavior
    );
  } catch (error: unknown) {
    console.error('Error saving image:', error);
    throw new Error(`Failed to save image: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * Enhance a prompt for better image generation results
 */
export async function enhancePrompt(originalPrompt: string): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/images/prompt/enhance`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      original_prompt: originalPrompt,
    }),
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to enhance prompt: ${response.status} - ${errorText}`);
  }
  
  const data: PromptEnhancementResponse = await response.json();
  return data.enhanced_prompt;
}

/**
 * Extract base64 image data from a response
 */
export function getImageFromResponse(response: ImageGenerationResponse): string {
  if (!response.success || !response.imgen_model_response || !response.imgen_model_response.data || response.imgen_model_response.data.length === 0) {
    throw new Error('Invalid response from image generation API');
  }
  
  const imageData = response.imgen_model_response.data[0];
  
  if (imageData.b64_json) {
    return `data:image/png;base64,${imageData.b64_json}`;
  } else if (imageData.url) {
    return imageData.url;
  } else {
    throw new Error('No image data found in response');
  }
}

/**
 * Get token usage statistics from a response
 */
export function getTokenUsage(response: ImageGenerationResponse) {
  if (!response.token_usage) return null;
  
  return {
    total: response.token_usage.total_tokens,
    input: response.token_usage.input_tokens,
    output: response.token_usage.output_tokens,
  };
} 
