import { API_BASE_URL } from './api';

/**
 * Service for managing asset URLs from Dataverse
 * Replaces the Azure SAS token service with direct Dataverse asset access
 */
class AssetService {
  /**
   * Get a direct URL to an asset stored in Dataverse
   * @param assetId Asset ID in Dataverse
   * @param size Optional size parameter (thumbnail, medium, full)
   * @returns URL to access the asset content
   */
  getAssetUrl(assetId: string, size?: 'thumbnail' | 'medium' | 'full'): string {
    const baseUrl = `${API_BASE_URL}/gallery/assets/${assetId}/content`;
    return size ? `${baseUrl}?size=${size}` : baseUrl;
  }

  /**
   * Get a thumbnail URL for an asset
   * @param assetId Asset ID in Dataverse
   * @returns Thumbnail URL
   */
  getThumbnailUrl(assetId: string): string {
    return this.getAssetUrl(assetId, 'thumbnail');
  }

  /**
   * Get a medium-sized URL for an asset
   * @param assetId Asset ID in Dataverse
   * @returns Medium-sized URL
   */
  getMediumUrl(assetId: string): string {
    return this.getAssetUrl(assetId, 'medium');
  }

  /**
   * Get the full-size URL for an asset
   * @param assetId Asset ID in Dataverse
   * @returns Full-size URL
   */
  getFullUrl(assetId: string): string {
    return this.getAssetUrl(assetId, 'full');
  }

  /**
   * Legacy method for compatibility - converts blob name to asset ID access
   * @param blobName Original blob name (will extract asset ID)
   * @param isVideo Whether this is a video (not currently used with Dataverse)
   * @returns Promise resolving to the asset URL
   */
  async getBlobUrl(blobName: string, isVideo: boolean): Promise<string> {
    // Extract asset ID from blob name (assuming format: folder/assetId.ext or assetId.ext)
    const assetId = blobName.split('/').pop()?.split('.')[0] || blobName.split('.')[0];
    return this.getAssetUrl(assetId);
  }
}

// Export singleton instance
export const sasTokenService = new AssetService();
export const assetService = new AssetService();