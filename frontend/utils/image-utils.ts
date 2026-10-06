/**
 * Utility functions for handling image URLs and optimization
 */

/**
 * Check if an image URL is from an external source
 */
export function isExternalImageUrl(url: string): boolean {
  // Check if it's a full URL (starts with http/https)
  return url.startsWith('http://') || url.startsWith('https://');
}

/**
 * Check if URL is from our API (Dataverse content endpoint)
 */
export function isDataverseContentUrl(url: string): boolean {
  return url.includes('/api/v1/gallery/assets/') && url.includes('/content');
}



/**
 * Get optimal image sizes based on the container and device
 */
export function getOptimalImageSizes(containerWidth?: number): string {
  if (containerWidth) {
    return `(max-width: 640px) ${Math.min(containerWidth, 640)}px, (max-width: 1024px) ${Math.min(containerWidth, 512)}px, ${Math.min(containerWidth, 384)}px`;
  }
  
  // Default responsive sizes
  return "(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw";
}

/**
 * Determine if an image should be loaded with priority
 */
export function shouldLoadWithPriority(index: number, isAboveFold: boolean = false): boolean {
  // Load first 6 images with priority, or if explicitly above the fold
  return index < 6 || isAboveFold;
}

/**
 * Generate a fallback image URL for broken images
 */
export function getFallbackImageUrl(width: number = 400, height: number = 300): string {
  return `data:image/svg+xml;base64,${btoa(`
    <svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">
      <rect width="100%" height="100%" fill="#f3f4f6"/>
      <text x="50%" y="50%" font-family="Arial, sans-serif" font-size="14" fill="#9ca3af" text-anchor="middle" dy=".3em">
        Image not available
      </text>
    </svg>
  `)}`;
}

/**
 * Image loading configuration for different scenarios
 */
export const IMAGE_LOADING_CONFIG = {
  // For gallery images
  gallery: {
    sizes: "(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw",
    quality: 85,
    priority: false,
  },
  
  // For hero/featured images
  hero: {
    sizes: "(max-width: 640px) 100vw, (max-width: 1024px) 80vw, 60vw",
    quality: 90,
    priority: true,
  },
  
  // For thumbnails
  thumbnail: {
    sizes: "(max-width: 640px) 50vw, (max-width: 1024px) 25vw, 200px",
    quality: 75,
    priority: false,
  },
  
  // For full-screen images
  fullscreen: {
    sizes: "100vw",
    quality: 95,
    priority: true,
  },
} as const;

export type ImageLoadingType = keyof typeof IMAGE_LOADING_CONFIG; 