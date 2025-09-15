import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { X, ArrowUp, Settings, Eye, Loader2, Wand2, RectangleHorizontal, Square, RectangleVertical, SignalLow, SignalMedium, SignalHigh, Timer, Copy, FolderTree, Plus, RefreshCw, PlusCircle } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/utils/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { enhancePrompt, createFolder, MediaType, fetchFolders } from "@/services/api";
import { toast } from "sonner";
import { useTheme } from "next-themes";
import { useFolderContext } from "@/context/folder-context";
import { Input } from "@/components/ui/input";

interface VideoOverlayProps {
  onGenerate: (settings: {
    prompt: string;
    aspectRatio: string;
    resolution: string;
    duration: string;
    variants: string;
    modality: string;
    analyzeVideo: boolean;
    brandsProtection: string;
    imageModel: string;
    hd: boolean;
    vivid: boolean;
    imageSize: string;
    brandProtectionModel: string;
    moderationThresholds: {
      hate: string;
      selfHarm: string;
      sexual: string;
      violence: string;
    };
    saveImages: boolean;
    imageCache: boolean;
    folder?: string;
    brandsList?: string[];
    // NEW: Image-to-Video settings
    sourceImages?: File[];
    hasSourceImages?: boolean;
  }) => void;
  isGenerating?: boolean;
  onPromptChange?: (newPrompt: string, isEnhanced: boolean) => void;
  folders?: string[];
  selectedFolder?: string;
  onFolderCreated?: (newFolder: string | string[]) => void;
}

export function VideoOverlay({ 
  onGenerate, 
  isGenerating = false, 
  onPromptChange,
  folders = [],
  selectedFolder = "",
  onFolderCreated
}: VideoOverlayProps) {
  // Add theme context
  const { theme, resolvedTheme } = useTheme();
  const [isDarkTheme, setIsDarkTheme] = useState(false);
  const { refreshFolders } = useFolderContext();
  
  // Move theme detection to useEffect to prevent hydration mismatch
  useEffect(() => {
    // Only run on client-side
    setIsDarkTheme(
      resolvedTheme === 'dark' || 
      theme === 'dark' || 
      (!theme && !resolvedTheme && window.matchMedia('(prefers-color-scheme: dark)').matches)
    );
  }, [theme, resolvedTheme]);
  
  // Image settings states
  const [prompt, setPrompt] = useState("");
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [modality, setModality] = useState("text-to-video");

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [model, setModel] = useState("sora-v1.1");
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [brandsProtection, setBrandsProtection] = useState("off");
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [imageModel, setImageModel] = useState("dalle3");
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [hd, setHd] = useState(true);
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [vivid, setVivid] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [imageSize, setImageSize] = useState("1792x1024");
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [brandProtectionModel, setBrandProtectionModel] = useState("default");
  
  // Add missing video settings states
  const [aspectRatio, setAspectRatio] = useState("16:9");
  const [resolution, setResolution] = useState("480p");
  const [duration, setDuration] = useState("5s");
  const [variants, setVariants] = useState("2");
  const [analyzeVideo, setAnalyzeVideo] = useState(true);
  const [isWizardEnhancing, setIsWizardEnhancing] = useState(false);
  const [moderationThresholds] = useState({
    hate: "medium",
    selfHarm: "medium",
    sexual: "medium",
    violence: "medium"
  });
  
  // Settings states
  const [expanded, setExpanded] = useState(true);
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [negativePrompt, setNegativePrompt] = useState("");
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [saveImages, setSaveImages] = useState(true);
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [imageCache, setImageCache] = useState(true);
  
  // Folder-related state
  const [folder, setFolder] = useState(selectedFolder || "root");
  const [isCreatingFolder, setIsCreatingFolder] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");
  const [isCreatingFolderLoading, setIsCreatingFolderLoading] = useState(false);
  const [isRefreshingFolders, setIsRefreshingFolders] = useState(false);
  
  // NEW: Image-to-Video state (mirroring ImageOverlay)
  const [sourceImages, setSourceImages] = useState<File[]>([]);
  const [isClient, setIsClient] = useState(false);
  // Derived: are we in image+text mode
  const isImageToVideo = isClient && sourceImages.length > 0;

  // References
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const newFolderInputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Client-side detection (same as ImageOverlay)
  useEffect(() => {
    setIsClient(true);
  }, []);

  // Force variants to 1 when images are attached
  useEffect(() => {
    if (sourceImages.length > 0 && variants !== "1") {
      setVariants("1");
    }
  }, [sourceImages.length]);

  // Update folder when selectedFolder prop changes
  useEffect(() => {
    setFolder(selectedFolder || "root");
  }, [selectedFolder]);

  // Focus the new folder input when creating folder
  useEffect(() => {
    if (isCreatingFolder && newFolderInputRef.current) {
      newFolderInputRef.current.focus();
    }
  }, [isCreatingFolder]);
  
  // Get overlay background color based on theme
  const getOverlayBgColor = () => {
    return isDarkTheme 
      ? 'backdrop-blur-md bg-black/70 border-white/10' 
      : 'backdrop-blur-md bg-white/90 border-black/10 shadow-lg';
  };
  
  // Get input and control background color based on theme
  const getControlBgColor = () => {
    return isDarkTheme
      ? 'bg-black/30 border-0 text-white focus:ring-white/20'
      : 'bg-white/50 border-gray-200 text-gray-900 focus:ring-gray-200';
  };
  
  // Get text color based on theme
  const getTextColor = () => {
    return isDarkTheme ? 'text-white' : 'text-gray-900';
  };
  
  // Get muted text color based on theme
  const getMutedTextColor = () => {
    return isDarkTheme ? 'text-white/70' : 'text-gray-500';
  };

  // Get hover background color based on theme
  const getHoverBgColor = () => {
    return isDarkTheme ? 'hover:bg-white/10' : 'hover:bg-gray-200/50';
  };

  // Get toggle style based on theme and active state
  const getToggleStyle = (isActive: boolean) => {
    return {
      backgroundColor: isActive 
        ? (isDarkTheme ? "rgba(255, 255, 255, 0.15)" : "rgba(209, 213, 219, 0.5)") 
        : (isDarkTheme ? "rgba(0, 0, 0, 0.3)" : "rgba(255, 255, 255, 0.5)"),
      border: isActive 
        ? (isDarkTheme ? "1px solid rgba(255, 255, 255, 0.4)" : "1px solid rgba(209, 213, 219, 0.5)") 
        : (isDarkTheme ? "1px solid rgba(255, 255, 255, 0.1)" : "1px solid rgba(229, 231, 235, 0.5)"),
      color: isActive 
        ? (isDarkTheme ? "white" : "rgb(17, 24, 39)") 
        : (isDarkTheme ? "rgba(255, 255, 255, 0.6)" : "rgb(107, 114, 128)"),
      borderRadius: "0.375rem",
    };
  };

  // Folder-related functions
  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) return;
    
    try {
      setIsCreatingFolderLoading(true);
      
      // Call the API to create the folder
      const result = await createFolder(newFolderName.trim(), MediaType.VIDEO);
      
      if (result.success) {
        // Show success message
        toast.success("Folder created", {
          description: `Folder "${newFolderName}" has been created successfully`
        });
        
        // Get the new folder path
        const newFolderPath = result.folder_path;
        
        // Reset the form
        setNewFolderName("");
        setIsCreatingFolder(false);
        
        // Select the newly created folder
        setFolder(newFolderPath);
        
        // Notify parent component about the new folder
        if (onFolderCreated) {
          onFolderCreated(newFolderPath);
        }
        
        // Trigger sidebar refresh
        refreshFolders();
      }
    } catch (error) {
      console.error("Error creating folder:", error);
      toast.error("Failed to create folder", {
        description: error instanceof Error ? error.message : "An unknown error occurred"
      });
    } finally {
      setIsCreatingFolderLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleCreateFolder();
    } else if (e.key === 'Escape') {
      setIsCreatingFolder(false);
      setNewFolderName("");
    }
  };

  // Function to refresh the folders list
  const handleRefreshFolders = async () => {
    if (isRefreshingFolders) return;
    
    try {
      setIsRefreshingFolders(true);
      
      const result = await fetchFolders(MediaType.VIDEO);
      
      if (result.folders && onFolderCreated) {
        // Update the parent component with the full folder list
        onFolderCreated(result.folders);
        
        // Trigger sidebar refresh
        refreshFolders();
        
        toast.success("Folders refreshed", {
          description: `${result.folders.length} folders available`
        });
      }
    } catch (error) {
      console.error("Error refreshing folders:", error);
      toast.error("Failed to refresh folders", {
        description: error instanceof Error ? error.message : "An unknown error occurred"
      });
    } finally {
      setIsRefreshingFolders(false);
    }
  };

  // NEW: Image handling functions (mirroring ImageOverlay)
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files);
      const validFiles: File[] = [];
      
      for (const file of files) {
        // Validate file type (same as ImageOverlay)
        if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
          toast.error("Invalid file type", {
            description: `${file.name}: Only JPEG, PNG, and WebP images are supported`
          });
          continue;
        }
        
        // Validate file size (same as ImageOverlay)
        if (file.size > 25 * 1024 * 1024) {
          toast.error("File too large", {
            description: `${file.name}: Maximum file size is 25MB`
          });
          continue;
        }
        
        validFiles.push(file);
      }
      
      // Limit to 3 images for video (vs 5 for images)
      if (sourceImages.length + validFiles.length > 3) {
        toast.warning("Too many images", {
          description: "Maximum 3 images can be used for video generation"
        });
        
        const spaceLeft = 3 - sourceImages.length;
        validFiles.splice(spaceLeft);
      }
      
      if (validFiles.length > 0) {
        setSourceImages(prev => [...prev, ...validFiles]);
        
        toast.success("Images selected", {
          description: `Added ${validFiles.length} image${validFiles.length > 1 ? 's' : ''} for video generation`
        });
      }
    }
  };

  const handleRemoveImage = (index: number) => {
    setSourceImages(prev => prev.filter((_, i) => i !== index));
  };

  const handleClearAllImages = () => {
    setSourceImages([]);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // Resize textarea when prompt changes
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      // Only auto-resize if we haven't hit the max height
      const scrollHeight = textareaRef.current.scrollHeight;
      if (scrollHeight <= 200) {
        textareaRef.current.style.height = `${scrollHeight}px`;
      } else {
        textareaRef.current.style.height = '200px';
      }
    }
  }, [prompt]);

  const handleSubmit = () => {
    if (!prompt.trim()) return;
    // Enforce 1 variant when source images are present
    const computedVariants = sourceImages.length > 0 ? "1" : variants;

    onGenerate({
      prompt,
      aspectRatio,
      resolution,
      duration,
      variants: computedVariants,
      modality,
      analyzeVideo,
      brandsProtection,
      imageModel,
      hd,
      vivid,
      imageSize,
      brandProtectionModel,
      moderationThresholds,
      saveImages,
      imageCache,
      folder,
      // NEW: Image-to-Video settings
      sourceImages: sourceImages,
      hasSourceImages: sourceImages.length > 0
    });
  };

  const handleWizardEnhance = async () => {
    if (!prompt.trim() || isGenerating || isWizardEnhancing) return;
    
    // Set loading state
    setIsWizardEnhancing(true);
    
    try {
      // Call the API to enhance the prompt
      const enhancedPrompt = await enhancePrompt(prompt.trim());
      
      // Update the prompt with the enhanced version
      setPrompt(enhancedPrompt);
      
      // Notify parent component about the prompt change
      if (onPromptChange) {
        onPromptChange(enhancedPrompt, true);
      }
      
      // Show success message
      toast.success("Prompt enhanced", {
        description: "Your prompt has been enhanced with AI"
      });
    } catch (error) {
      console.error("Error enhancing prompt:", error);
      toast.error("Failed to enhance prompt", {
        description: "Please try again or adjust your prompt"
      });
    } finally {
      // Reset loading state
      setIsWizardEnhancing(false);
    }
  };

  return (
    <div className="sticky bottom-0 left-0 right-0 flex items-end justify-center p-6 z-20 pointer-events-none">
      <div className={cn(
        "w-full transition-all duration-200 ease-in-out pointer-events-auto",
        expanded ? "mb-6" : "mb-2"
      )}
      style={{
        // Dynamic width based on image presence (same as ImageOverlay)
        maxWidth: isClient && sourceImages.length > 0 ? '58rem' : '56rem'
      }}>
        <div className={cn(
          "rounded-xl p-4 shadow-lg border",
          getOverlayBgColor()
        )}>
          <div className="flex flex-col space-y-4">
            
            {/* NEW: Image thumbnails row - EXACT replica from ImageOverlay */}
            {isClient && sourceImages.length > 0 && (
              <div className="flex flex-wrap gap-2 items-center">
                {sourceImages.map((img, index) => (
                  <div key={index} className="relative">
                    <img 
                      src={URL.createObjectURL(img)} 
                      alt={`Video Source ${index + 1}`} 
                      className={cn(
                        "w-12 h-12 object-cover rounded-md border transition-all duration-200",
                        index === 0 && sourceImages.length > 1 
                          ? "border-purple-300 ring-2 ring-purple-300/50 shadow-lg shadow-purple-300/25" 
                          : "border-gray-500/30"
                      )}
                    />
                    
                    {/* Primary image indicator - purple theme for video */}
                    {index === 0 && sourceImages.length > 1 && (
                      <div className="absolute -top-1 -right-1 bg-purple-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center font-bold">
                        1
                      </div>
                    )}
                    
                    <Button 
                      onClick={() => handleRemoveImage(index)}
                      className={cn(
                        "absolute -top-2 -right-2 rounded-full p-0.5 hover:bg-black",
                        isDarkTheme ? "bg-black/70 text-white" : "bg-white/90 text-gray-700"
                      )}
                      disabled={isGenerating}
                      aria-label="Remove image"
                      variant="ghost"
                      size="icon"
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
                
                {/* Clear all button */}
                {sourceImages.length > 1 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleClearAllImages}
                    className={cn("text-xs", getMutedTextColor(), getHoverBgColor())}
                    disabled={isGenerating}
                  >
                    Clear all
                  </Button>
                )}
              </div>
            )}
            <div className="flex items-center gap-3">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setExpanded(!expanded)}
                aria-label="Toggle options"
                className={cn(
                  getMutedTextColor(),
                  getHoverBgColor()
                )}
                disabled={isGenerating}
              >
                {expanded ? (
                  <X className="h-5 w-5" />
                ) : (
                  <Settings className="h-5 w-5" />
                )}
              </Button>
              
              {/* NEW: Upload images button (mirrors ImageOverlay) */}
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => {
                        if (fileInputRef.current) {
                          fileInputRef.current.click();
                        }
                      }}
                      aria-label="Upload images"
                      className={cn(
                        getMutedTextColor(),
                        getHoverBgColor()
                      )}
                      disabled={isGenerating}
                    >
                      <PlusCircle className="h-5 w-5" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Upload images to guide video (max 3)</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>

              {/* Hidden file input for image selection */}
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileSelect}
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
                disabled={isGenerating}
                aria-label="Upload image files"
                multiple
              />
              
              <Textarea
                ref={textareaRef}
                value={prompt}
                onChange={(e) => {
                  setPrompt(e.target.value);
                  if (onPromptChange) {
                    onPromptChange(e.target.value, false);
                  }
                }}
                placeholder={isClient && sourceImages.length > 0 
                  ? "Describe how to use these images in the video..."
                  : "Describe your video..."}
                className={cn(
                  "border border-gray-500/30 min-h-[38px] resize-none overflow-hidden",
                  getControlBgColor(),
                  getTextColor(),
                  isDarkTheme ? "placeholder:text-white/50" : "placeholder:text-gray-400"
                )}
                disabled={isGenerating}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && e.shiftKey) {
                    // Allow shift+enter for new lines
                    return;
                  }
                  if (e.key === 'Enter' && prompt.trim() && !isGenerating) {
                    e.preventDefault();
                    handleSubmit();
                  }
                }}
              />
              
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={handleWizardEnhance}
                      aria-label="Enhance prompt"
                      className={cn(
                        "border-0 min-w-9 h-9",
                        isDarkTheme 
                          ? "bg-white/10 hover:bg-white/20 text-white" 
                          : "bg-gray-100 hover:bg-gray-200 text-gray-900"
                      )}
                      disabled={isGenerating || isWizardEnhancing || !prompt.trim()}
                    >
                      {isWizardEnhancing ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Wand2 className="h-4 w-4" />
                      )}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Enhance your prompt with AI</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
              
              <Button
                variant="outline"
                onClick={handleSubmit}
                className={cn(
                  "border-0",
                  isDarkTheme 
                    ? "bg-white/10 hover:bg-white/20 text-white" 
                    : "bg-gray-100 hover:bg-gray-200 text-gray-900"
                )}
                disabled={isGenerating || !prompt.trim()}
              >
                {isGenerating ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <ArrowUp className="h-4 w-4 mr-2" />
                )}
                {isGenerating ? "Generating..." : "Generate"}
              </Button>
            </div>

            {expanded && (
              <div className="flex flex-wrap items-center gap-3 pt-1">
                <TooltipProvider>
                  <div className={`flex flex-wrap items-center gap-3 transition-all duration-200 ease-in-out opacity-100 translate-y-0`}>
                    {/* MODALITY CONDITIONAL AND SELECTOR REMOVED - START */}
                    {/* {modality === "video" ? ( */}
                      <>
                        {/* Modality Select - REMOVED */}

                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Select
                              value={aspectRatio}
                              onValueChange={setAspectRatio}
                              disabled={isGenerating}
                            >
                              <SelectTrigger className="w-[120px] h-8">
                                <SelectValue placeholder="16:9" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="16:9">
                                  <div className="flex items-center">
                                    <RectangleHorizontal className="h-4 w-4 mr-2" />
                                    16:9
                                  </div>
                                </SelectItem>
                                <SelectItem value="1:1">
                                  <div className="flex items-center">
                                    <Square className="h-4 w-4 mr-2" />
                                    1:1
                                  </div>
                                </SelectItem>
                                <SelectItem value="9:16">
                                  <div className="flex items-center">
                                    <RectangleVertical className="h-4 w-4 mr-2" />
                                    9:16
                                  </div>
                                </SelectItem>
                              </SelectContent>
                            </Select>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Aspect ratio: Width to height ratio of the output</p>
                          </TooltipContent>
                        </Tooltip>

                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Select
                              value={resolution}
                              onValueChange={setResolution}
                              disabled={isGenerating}
                            >
                              <SelectTrigger className="w-[140px] h-8">
                                <SelectValue placeholder="480p" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="480p">
                                  <div className="flex items-center">
                                    <SignalLow className="h-4 w-4 mr-2" />
                                    480p
                                  </div>
                                </SelectItem>
                                <SelectItem value="720p">
                                  <div className="flex items-center">
                                    <SignalMedium className="h-4 w-4 mr-2" />
                                    720p
                                  </div>
                                </SelectItem>
                                <SelectItem value="1080p">
                                  <div className="flex items-center">
                                    <SignalHigh className="h-4 w-4 mr-2" />
                                    1080p
                                  </div>
                                </SelectItem>
                              </SelectContent>
                            </Select>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Resolution: Quality of the output</p>
                          </TooltipContent>
                        </Tooltip>

                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Select
                              value={duration}
                              onValueChange={setDuration}
                              disabled={isGenerating}
                            >
                              <SelectTrigger className="w-[120px] h-8">
                                <div className="flex items-center">
                                  <Timer className="h-4 w-4 mr-2" />
                                  <SelectValue placeholder="5s" />
                                </div>
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="5s">5s</SelectItem>
                                <SelectItem value="10s">10s</SelectItem>
                                <SelectItem value="15s">15s</SelectItem>
                                <SelectItem value="20s">20s</SelectItem>
                              </SelectContent>
                            </Select>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Duration: Length of the video</p>
                          </TooltipContent>
                        </Tooltip>
                        
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Select
                              value={variants}
                              onValueChange={setVariants}
                              disabled={isGenerating || isImageToVideo}
                            >
                              <SelectTrigger className="w-[150px] h-8">
                                <div className="flex items-center">
                                  <Copy className="h-4 w-4 mr-2" />
                                  <SelectValue placeholder="2" />
                                </div>
                              </SelectTrigger>
                              <SelectContent>
                                {isImageToVideo ? (
                                  <SelectItem value="1">1 variation</SelectItem>
                                ) : (
                                  <>
                                    <SelectItem value="1">1 variation</SelectItem>
                                    <SelectItem value="2">2 variations</SelectItem>
                                    <SelectItem value="3">3 variations</SelectItem>
                                    <SelectItem value="4">4 variations</SelectItem>
                                    <SelectItem value="5">5 variations</SelectItem>
                                  </>
                                )}
                              </SelectContent>
                            </Select>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>{isImageToVideo ? 'Variations limited to 1 when images are attached' : 'Variations: Number of different outputs to generate'}</p>
                          </TooltipContent>
                        </Tooltip>
                        
                        {/* Folder Select Dropdown */}
                        <Tooltip delayDuration={300}>
                          <TooltipTrigger asChild>
                            <div className="relative">
                              <Select
                                value={folder}
                                onValueChange={setFolder}
                                disabled={isGenerating}
                                onOpenChange={(open) => {
                                  if (!open) {
                                    setIsCreatingFolder(false);
                                    setNewFolderName("");
                                  }
                                }}
                              >
                                <SelectTrigger className="w-[150px] h-8">
                                  <div className="flex items-center">
                                    <FolderTree className="h-4 w-4 mr-2 text-primary" />
                                    <SelectValue placeholder="Root folder" />
                                  </div>
                                </SelectTrigger>
                                <SelectContent>
                                  {/* Create new folder option */}
                                  {isCreatingFolder ? (
                                    <div className="flex items-center px-2 py-1.5">
                                      <Input
                                        ref={newFolderInputRef}
                                        value={newFolderName}
                                        onChange={(e) => setNewFolderName(e.target.value)}
                                        placeholder="New folder name"
                                        className="h-8 text-sm border-none bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 p-0 pl-1"
                                        onKeyDown={handleKeyDown}
                                        disabled={isCreatingFolderLoading}
                                      />
                                      <Button
                                        variant="ghost"
                                        size="icon"
                                        disabled={!newFolderName.trim() || isCreatingFolderLoading}
                                        onClick={(e) => {
                                          e.preventDefault();
                                          handleCreateFolder();
                                        }}
                                        className="h-7 w-7 ml-1"
                                      >
                                        {isCreatingFolderLoading ? (
                                          <Loader2 className="h-3 w-3 animate-spin" />
                                        ) : (
                                          <Plus className="h-3 w-3" />
                                        )}
                                      </Button>
                                    </div>
                                  ) : (
                                    <div
                                      className="flex items-center px-2 py-1.5 cursor-pointer hover:bg-muted text-primary"
                                      onClick={() => setIsCreatingFolder(true)}
                                    >
                                      <Plus className="h-4 w-4 mr-2" />
                                      <span className="text-sm">New folder</span>
                                    </div>
                                  )}

                                  {/* Refresh folders option */}
                                  <div
                                    className="flex items-center px-2 py-1.5 cursor-pointer hover:bg-muted text-primary"
                                    onClick={handleRefreshFolders}
                                    role="button"
                                  >
                                    {isRefreshingFolders ? (
                                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                    ) : (
                                      <RefreshCw className="h-4 w-4 mr-2" />
                                    )}
                                    <span className="text-sm">Refresh folders</span>
                                  </div>

                                  {/* Root folder option */}
                                  <SelectItem value="root">
                                    Root
                                  </SelectItem>

                                  {/* List of existing folders */}
                                  {folders.map((folderPath) => (
                                    <SelectItem key={folderPath} value={folderPath}>
                                      {folderPath}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            </div>
                          </TooltipTrigger>
                          <TooltipContent side="right" className="font-medium">
                            <p>Storage location for generated video files</p>
                          </TooltipContent>
                        </Tooltip>

                        <Tooltip>
                          <TooltipTrigger asChild>
                            <ToggleGroup 
                              type="single" 
                              size="lg"
                              value={analyzeVideo ? "analyze" : ""}
                              onValueChange={(value) => {
                                setAnalyzeVideo(value === "analyze");
                              }}
                              disabled={isGenerating}
                            >
                              <ToggleGroupItem 
                                value="analyze" 
                                aria-label="Toggle analysis"
                                className={cn(
                                  "rounded-md",
                                  isDarkTheme ? "bg-black/30 border-0 text-white" : "bg-white/50 border-gray-200 text-gray-900"
                                )}
                                style={{
                                  ...getToggleStyle(analyzeVideo),
                                  padding: "0.5rem 1rem",
                                  minWidth: "90px",
                                }}
                              >
                                <Eye className={`h-4 w-4 mr-2 ${analyzeVideo ? (isDarkTheme ? "text-white" : "text-gray-900") : ""}`} />
                                Analyze
                              </ToggleGroupItem>
                            </ToggleGroup>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Analyze video with GPT-4o for insights</p>
                          </TooltipContent>
                        </Tooltip>
                      </>
                    {/* MODALITY CONDITIONAL AND SELECTOR REMOVED - END */}
                  </div>
                </TooltipProvider>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
} 
