import { useState, useRef } from "react";
import Image from "next/image";
import { Card } from "@/components/ui/card";
import { AspectRatio } from "@/components/ui/aspect-ratio";
import { cn } from "@/utils/utils";
import { MoreVertical, Trash, FolderUp, Download, Loader2, ImageIcon } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubTrigger,
  DropdownMenuSubContent,
} from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { MediaType, deleteGalleryAsset, fetchFolders, moveAsset } from "@/services/api";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";

interface ImageCardProps {
  src: string;
  title?: string;
  description?: string;
  size?: "small" | "medium" | "large";
  aspectRatio?: "16:9" | "4:3" | "1:1" | "9:16";
  className?: string;
  tags?: string[];
  assetId?: string;
  blobName?: string;
  onDelete?: () => void;
  onMove?: () => void;
  onClick?: () => void;
  width?: number;
  height?: number;
}

export function ImageCard({
  src,
  description,
  aspectRatio = "1:1",
  className,
  tags,
  blobName,
  assetId,
  onDelete,
  onClick,
  width,
  height,
}: ImageCardProps) {
  const imgRef = useRef<HTMLImageElement>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isMoving, setIsMoving] = useState(false);
  const [folders, setFolders] = useState<string[]>([]);
  const [loadingFolders, setLoadingFolders] = useState(false);
  const [actualRatio, setActualRatio] = useState<number | null>(null);
  const [imageError, setImageError] = useState(false);

  // Handle image loading with Next.js Image component
  const handleImageLoad = () => {
    setIsLoading(false);
    setImageError(false);
  };

  const handleImageError = () => {
    setIsLoading(false);
    setImageError(true);
  };

  // Handle delete action
  const handleDelete = async () => {
    if (!assetId) {
      toast.error("Cannot delete image", {
        description: "Missing asset identifier for the image"
      });
      return;
    }

    try {
      setIsDeleting(true);
      const result = await deleteGalleryAsset(assetId);
      
      if (result.success) {
        toast.success("Image deleted", {
          description: "The image was successfully deleted"
        });
        
        // Call the onDelete callback if provided
        if (onDelete) {
          onDelete();
        }
      } else {
        throw new Error(result.message || "Failed to delete image");
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "An unknown error occurred";
      toast.error("Error deleting image", {
        description: errorMessage
      });
    } finally {
      setIsDeleting(false);
    }
  };

  // Handle download action
  const handleDownload = () => {
    if (!src) {
      toast.error("Cannot download image", {
        description: "Missing image source URL"
      });
      return;
    }

    try {
      // Create an invisible anchor element to trigger the download
      const a = document.createElement('a');
      a.href = src;
      a.download = blobName || 'image-download.jpg';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      
      toast.success("Image download started", {
        description: "Your image is being downloaded"
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "An unknown error occurred";
      toast.error("Error downloading image", {
        description: errorMessage
      });
    }
  };

  // Determine the actual aspect ratio from image dimensions or props
  const getActualAspectRatio = () => {
    // If we have the actual ratio from the image itself, use that
    if (actualRatio) return actualRatio;
    
    // If we have actual dimensions from props, calculate the ratio
    if (width && height) return width / height;
    
    // Check if there's an aspect ratio in the metadata
    if (aspectRatio) {
      // If it's a string like "16:9", convert it to a number
      if (typeof aspectRatio === 'string' && aspectRatio.includes(':')) {
        return getRatioFromString(aspectRatio);
      }
      // If it's already a number, just use it
      if (typeof aspectRatio === 'number') {
        return aspectRatio;
      }
    }
    
    // Default to square if nothing else is available
    return 1;
  };

  const getRatioFromString = (ratio: string): number => {
    switch (ratio) {
      case "16:9": return 16/9;
      case "4:3": return 4/3;
      case "1:1": return 1;
      case "9:16": return 9/16;
      default: return 1;
    }
  };

  // Helper function to get a variant for a tag
  const getTagVariant = (tag: string): "default" | "secondary" | "outline" | "destructive" => {
    // Map specific tags to specific variants or use a simple rotation
    const tagVariants: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
      "AI Generated": "default",
      "Landscape": "secondary",
      "Portrait": "secondary",
      "Nature": "outline",
      "Urban": "outline",
      "Abstract": "default",
      "People": "secondary",
      "Architecture": "outline",
      "Animals": "destructive",
      "Technology": "default",
    };
    
    return tagVariants[tag] || "outline";
  };

  // Skeleton loader for image content
  const renderSkeleton = () => (
    <div className="absolute inset-0">
      <Skeleton className="h-full w-full" />
    </div>
  );

  // Error placeholder for failed images
  const renderError = () => (
    <div className="absolute inset-0 flex items-center justify-center bg-muted text-muted-foreground">
      <div className="text-center">
        <ImageIcon className="h-8 w-8 mx-auto mb-2" />
        <p className="text-sm">Failed to load image</p>
      </div>
    </div>
  );

  // Fetch folders when dropdown is opened
  const handleDropdownOpen = async (open: boolean) => {
    if (open && folders.length === 0 && !loadingFolders) {
      try {
        setLoadingFolders(true);
        const result = await fetchFolders(MediaType.IMAGE);
        setFolders(result.folders);
      } catch (error) {
        console.error("Failed to fetch folders:", error);
      } finally {
        setLoadingFolders(false);
      }
    }
  };

  // Handle moving an image to a folder
  const handleMove = async (folderPath: string) => {
    if (!assetId) {
      toast.error("Cannot move image", {
        description: "Missing asset identifier for the image"
      });
      return;
    }

    try {
      setIsMoving(true);
      const result = await moveAsset(assetId, folderPath);
      
      if (result.success) {
        toast.success("Image moved", {
          description: `The image was successfully moved to "${folderPath}"`
        });
        
        // Call the onDelete callback to refresh the gallery
        if (onDelete) {
          onDelete();
        }
      } else {
        throw new Error(result.message || "Failed to move image");
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "An unknown error occurred";
      toast.error("Error moving image", {
        description: errorMessage
      });
    } finally {
      setIsMoving(false);
    }
  };

  return (
    <div 
      ref={cardRef}
      className="relative w-full mb-0"
    >
      <Card 
        className={cn(
          "overflow-hidden border rounded-xl group hover:shadow-md transition-all duration-200 h-full p-0 w-full bg-card",
          className,
          onClick && "cursor-pointer"
        )}
      >
        {/* Add dropdown menu - only visible on hover */}
        <div className="absolute top-2 right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
          <DropdownMenu onOpenChange={handleDropdownOpen}>
            <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
              <Button variant="ghost" size="icon" className="h-8 w-8 bg-black/30 hover:bg-black/40 text-white">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuSub>
                <DropdownMenuSubTrigger disabled={isMoving || loadingFolders}>
                  {isMoving ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Moving...
                    </>
                  ) : (
                    <>
                      <FolderUp className="h-4 w-4 mr-2" />
                      Move to folder
                    </>
                  )}
                </DropdownMenuSubTrigger>
                <DropdownMenuSubContent>
                  {loadingFolders ? (
                    <DropdownMenuItem disabled>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Loading folders...
                    </DropdownMenuItem>
                  ) : folders.length > 0 ? (
                    folders.map((folder) => (
                      <DropdownMenuItem
                        key={folder}
                        onClick={() => handleMove(folder)}
                      >
                        {folder || "Root"}
                      </DropdownMenuItem>
                    ))
                  ) : (
                    <DropdownMenuItem disabled>
                      No folders available
                    </DropdownMenuItem>
                  )}
                </DropdownMenuSubContent>
              </DropdownMenuSub>
              
              <DropdownMenuItem onClick={handleDownload}>
                <Download className="h-4 w-4 mr-2" />
                Download
              </DropdownMenuItem>
              
              <DropdownMenuSeparator />
              
              <DropdownMenuItem 
                variant="destructive" 
                className="text-destructive cursor-pointer"
                disabled={isDeleting}
                onClick={handleDelete}
              >
                {isDeleting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Deleting...
                  </>
                ) : (
                  <>
                    <Trash className="h-4 w-4 mr-2" />
                    Delete
                  </>
                )}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        
        <div 
          onClick={() => {
            // Call onClick if provided
            if (onClick) {
              onClick();
            }
          }} 
          className="w-full h-full"
        >
          <AspectRatio ratio={getActualAspectRatio()} className="bg-muted w-full h-full">
            {/* Image container */}
            <div className="absolute inset-0 flex items-center justify-center w-full h-full">
              {isLoading && renderSkeleton()}
              {imageError && renderError()}
              
              {!imageError && (
                <Image
                  ref={imgRef}
                  src={src}
                  alt={description || "Gallery image"}
                  fill
                  className={cn(
                    "object-cover transition-opacity duration-200",
                    isLoading ? "opacity-0" : "opacity-100"
                  )}
                  sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                  onLoad={handleImageLoad}
                  onError={handleImageError}
                />
              )}
            </div>
            
            {/* Image details overlay */}
            <div className="absolute inset-0 bg-gradient-to-t from-black/70 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200">
              <div className="absolute bottom-0 left-0 right-0 p-3 text-white">
                {description && (
                  <p className="text-xs text-white/90 line-clamp-2 mb-1">{description}</p>
                )}
                
                {/* Display tags */}
                {tags && tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {tags.slice(0, 3).map((tag, index) => (
                      <Badge 
                        key={index} 
                        variant={getTagVariant(tag)} 
                        className="bg-black/40 text-white text-xs py-0 h-5"
                      >
                        {tag}
                      </Badge>
                    ))}
                    {tags.length > 3 && (
                      <Badge variant="secondary" className="bg-black/40 text-white text-xs py-0 h-5">
                        +{tags.length - 3}
                      </Badge>
                    )}
                  </div>
                )}
              </div>
            </div>
          </AspectRatio>
        </div>
      </Card>
    </div>
  );
}