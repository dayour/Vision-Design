/**
 * Compatibility wrapper for gradual migration to new error handling
 * 
 * This file provides wrapper functions that use the new apiClient but maintain
 * backward compatibility with existing code by throwing errors on failure.
 */

import { API_BASE_URL } from './api';
import { apiClient } from './api-client';
import { unwrapResult, type ApiResult } from './api-error';
import type { GalleryResponse, FolderHierarchy, MediaType } from './api';

/**
 * Fetch folders with enhanced error handling
 * Maintains backward compatibility by throwing on error
 */
export async function fetchFolders(
  mediaType?: MediaType
): Promise<{ folders: string[]; folder_hierarchy: FolderHierarchy }> {
  let url = `${API_BASE_URL}/gallery/folders`;
  
  if (mediaType) {
    url += `?media_type=${mediaType}`;
  }
  
  const result = await apiClient.get<{
    folders: string[];
    folder_hierarchy: FolderHierarchy;
  }>(url);
  
  return unwrapResult(result);
}

/**
 * Fetch folders with ApiResult pattern (doesn't throw)
 */
export async function fetchFoldersSafe(
  mediaType?: MediaType
): Promise<ApiResult<{ folders: string[]; folder_hierarchy: FolderHierarchy }>> {
  let url = `${API_BASE_URL}/gallery/folders`;
  
  if (mediaType) {
    url += `?media_type=${mediaType}`;
  }
  
  return apiClient.get(url);
}

/**
 * Fetch gallery images with enhanced error handling
 */
export async function fetchGalleryImages(
  limit: number = 50,
  offset: number = 0,
  continuationToken?: string,
  prefix?: string,
  folderPath?: string
): Promise<GalleryResponse> {
  const params = new URLSearchParams();
  params.append('limit', String(limit));
  params.append('offset', String(offset));
  if (continuationToken) {
    params.append('continuation_token', continuationToken);
  }
  if (prefix) {
    params.append('prefix', prefix);
  }
  if (folderPath) {
    params.append('folder_path', folderPath);
  }
  
  const url = `${API_BASE_URL}/gallery/images?${params.toString()}`;
  const result = await apiClient.get<GalleryResponse>(url);
  
  return unwrapResult(result);
}

/**
 * Fetch gallery images with ApiResult pattern (doesn't throw)
 */
export async function fetchGalleryImagesSafe(
  limit: number = 50,
  offset: number = 0,
  continuationToken?: string,
  prefix?: string,
  folderPath?: string
): Promise<ApiResult<GalleryResponse>> {
  const params = new URLSearchParams();
  params.append('limit', String(limit));
  params.append('offset', String(offset));
  if (continuationToken) {
    params.append('continuation_token', continuationToken);
  }
  if (prefix) {
    params.append('prefix', prefix);
  }
  if (folderPath) {
    params.append('folder_path', folderPath);
  }
  
  const url = `${API_BASE_URL}/gallery/images?${params.toString()}`;
  return apiClient.get<GalleryResponse>(url);
}

/**
 * Fetch gallery videos with enhanced error handling
 */
export async function fetchGalleryVideos(
  limit: number = 50,
  offset: number = 0,
  continuationToken?: string,
  prefix?: string,
  folderPath?: string
): Promise<GalleryResponse> {
  const params = new URLSearchParams();
  params.append('limit', String(limit));
  params.append('offset', String(offset));
  if (continuationToken) {
    params.append('continuation_token', continuationToken);
  }
  if (prefix) {
    params.append('prefix', prefix);
  }
  if (folderPath) {
    params.append('folder_path', folderPath);
  }
  
  const url = `${API_BASE_URL}/gallery/videos?${params.toString()}`;
  const result = await apiClient.get<GalleryResponse>(url);
  
  return unwrapResult(result);
}

/**
 * Fetch gallery videos with ApiResult pattern (doesn't throw)
 */
export async function fetchGalleryVideosSafe(
  limit: number = 50,
  offset: number = 0,
  continuationToken?: string,
  prefix?: string,
  folderPath?: string
): Promise<ApiResult<GalleryResponse>> {
  const params = new URLSearchParams();
  params.append('limit', String(limit));
  params.append('offset', String(offset));
  if (continuationToken) {
    params.append('continuation_token', continuationToken);
  }
  if (prefix) {
    params.append('prefix', prefix);
  }
  if (folderPath) {
    params.append('folder_path', folderPath);
  }
  
  const url = `${API_BASE_URL}/gallery/videos?${params.toString()}`;
  return apiClient.get<GalleryResponse>(url);
}

/**
 * Health check endpoint with enhanced error handling
 */
export async function checkHealth(): Promise<{ status: string; timestamp: string }> {
  const url = `${API_BASE_URL}/health`;
  const result = await apiClient.get<{ status: string; timestamp: string }>(url);
  
  return unwrapResult(result);
}

/**
 * Health check with ApiResult pattern (doesn't throw)
 */
export async function checkHealthSafe(): Promise<ApiResult<{ status: string; timestamp: string }>> {
  const url = `${API_BASE_URL}/health`;
  return apiClient.get(url);
}
