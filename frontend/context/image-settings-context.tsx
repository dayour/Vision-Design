"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

export type BrandsProtectionMode = 'off' | 'neutralize' | 'replace';

interface ImageSettings {
  brandsProtection: BrandsProtectionMode;
  brandsList: string[];
  customAnalysisPrompt: string;
}

const defaultImageSettings: ImageSettings = {
  brandsProtection: 'off',
  brandsList: [],
  customAnalysisPrompt: "Analyze this image for marketing effectiveness, visual appeal, and target audience. Focus on composition, colors, and overall impact.",
};

interface ImageSettingsContextType {
  settings: ImageSettings;
  updateSettings: (settings: Partial<ImageSettings>) => void;
  addBrand: (brand: string) => void;
  removeBrand: (brand: string) => void;
  clearBrands: () => void;
  updateCustomAnalysisPrompt: (prompt: string) => void;
}

const ImageSettingsContext = createContext<ImageSettingsContextType | null>(null);

export function useImageSettings() {
  const context = useContext(ImageSettingsContext);
  if (!context) {
    throw new Error("useImageSettings must be used within an ImageSettingsProvider");
  }
  return context;
}

export function ImageSettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<ImageSettings>(defaultImageSettings);

  // Load settings from localStorage on initial render
  useEffect(() => {
    const savedSettings = localStorage.getItem('imageSettings');
    if (savedSettings) {
      try {
        setSettings(JSON.parse(savedSettings));
      } catch (e) {
        console.error("Failed to parse image settings", e);
      }
    }
  }, []);

  // Save settings to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem('imageSettings', JSON.stringify(settings));
  }, [settings]);

  const updateSettings = (newSettings: Partial<ImageSettings>) => {
    setSettings(prev => {
      const updated = { ...prev, ...newSettings };
      
      // If brand protection is turned off, clear the brand list
      if (newSettings.brandsProtection === 'off') {
        updated.brandsList = [];
      }
      
      return updated;
    });
  };

  const addBrand = (brand: string) => {
    if (!brand.trim() || settings.brandsList.length >= 3) return;
    
    setSettings(prev => ({
      ...prev,
      brandsList: [...prev.brandsList, brand.trim()]
    }));
  };

  const removeBrand = (brand: string) => {
    setSettings(prev => ({
      ...prev,
      brandsList: prev.brandsList.filter(b => b !== brand)
    }));
  };

  const clearBrands = () => {
    setSettings(prev => ({
      ...prev,
      brandsList: []
    }));
  };

  const updateCustomAnalysisPrompt = (prompt: string) => {
    setSettings(prev => ({
      ...prev,
      customAnalysisPrompt: prompt
    }));
  };

  return (
    <ImageSettingsContext.Provider 
      value={{ 
        settings, 
        updateSettings,
        addBrand,
        removeBrand,
        clearBrands,
        updateCustomAnalysisPrompt
      }}
    >
      {children}
    </ImageSettingsContext.Provider>
  );
} 