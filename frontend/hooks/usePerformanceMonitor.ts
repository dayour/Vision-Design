import { useEffect, useCallback, useRef } from 'react';

interface PerformanceMetrics {
  loadTime: number;
  domContentLoaded: number;
  firstContentfulPaint?: number;
  largestContentfulPaint?: number;
  cumulativeLayoutShift?: number;
  firstInputDelay?: number;
}

interface AssetLoadMetrics {
  url: string;
  loadTime: number;
  size: number;
  type: string;
}

export function usePerformanceMonitor() {
  const metricsRef = useRef<PerformanceMetrics | null>(null);
  const assetMetricsRef = useRef<AssetLoadMetrics[]>([]);

  // Measure page load performance
  const measurePagePerformance = useCallback(() => {
    if (typeof window === 'undefined') return;

    const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    
    if (navigation) {
      metricsRef.current = {
        loadTime: navigation.loadEventEnd - navigation.loadEventStart,
        domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
      };
    }

    // Measure Web Vitals
    if ('web-vitals' in window || typeof window.PerformanceObserver !== 'undefined') {
      // First Contentful Paint
      new PerformanceObserver((list) => {
        const entries = list.getEntries();
        const fcpEntry = entries.find(entry => entry.name === 'first-contentful-paint');
        if (fcpEntry && metricsRef.current) {
          metricsRef.current.firstContentfulPaint = fcpEntry.startTime;
        }
      }).observe({ entryTypes: ['paint'] });

      // Largest Contentful Paint
      new PerformanceObserver((list) => {
        const entries = list.getEntries();
        const lcpEntry = entries[entries.length - 1];
        if (lcpEntry && metricsRef.current) {
          metricsRef.current.largestContentfulPaint = lcpEntry.startTime;
        }
      }).observe({ entryTypes: ['largest-contentful-paint'] });

      // Cumulative Layout Shift
      new PerformanceObserver((list) => {
        let clsValue = 0;
        for (const entry of list.getEntries()) {
          const layoutShiftEntry = entry as PerformanceEntry & { hadRecentInput?: boolean; value?: number };
          if (!layoutShiftEntry.hadRecentInput) {
            clsValue += layoutShiftEntry.value || 0;
          }
        }
        if (metricsRef.current) {
          metricsRef.current.cumulativeLayoutShift = clsValue;
        }
      }).observe({ entryTypes: ['layout-shift'] });

      // First Input Delay
      new PerformanceObserver((list) => {
        const entries = list.getEntries();
        const fidEntry = entries[0];
        if (fidEntry && metricsRef.current) {
          const firstInputEntry = fidEntry as PerformanceEntry & { processingStart?: number };
          metricsRef.current.firstInputDelay = (firstInputEntry.processingStart || 0) - fidEntry.startTime;
        }
      }).observe({ entryTypes: ['first-input'] });
    }
  }, []);

  // Measure asset loading performance
  const measureAssetPerformance = useCallback(() => {
    if (typeof window === 'undefined') return;

    const resourceEntries = performance.getEntriesByType('resource') as PerformanceResourceTiming[];
    
    assetMetricsRef.current = resourceEntries
      .filter(entry => 
        entry.name.includes('/_next/static/') ||
        entry.name.includes('/api/v1/gallery/assets/') ||
        entry.name.includes('.jpg') ||
        entry.name.includes('.png') ||
        entry.name.includes('.webp') ||
        entry.name.includes('.avif')
      )
      .map(entry => ({
        url: entry.name,
        loadTime: entry.responseEnd - entry.requestStart,
        size: entry.transferSize || 0,
        type: getAssetType(entry.name),
      }));
  }, []);

  // Get asset type from URL
  const getAssetType = (url: string): string => {
    if (url.includes('/_next/static/js/')) return 'javascript';
    if (url.includes('/_next/static/css/')) return 'stylesheet';
    if (url.includes('.blob.core.windows.net')) {
      if (url.match(/\.(jpg|jpeg|png|webp|avif)/i)) return 'azure-image';
      if (url.match(/\.(mp4|webm|mov)/i)) return 'azure-video';
      return 'azure-blob';
    }
    if (url.match(/\.(jpg|jpeg|png|webp|avif)$/i)) return 'image';
    if (url.match(/\.(mp4|webm|mov)$/i)) return 'video';
    return 'other';
  };

  // Log performance metrics
  const logMetrics = useCallback(() => {
    if (metricsRef.current) {
      console.group('🚀 Performance Metrics');
      console.log('Load Time:', metricsRef.current.loadTime, 'ms');
      console.log('DOM Content Loaded:', metricsRef.current.domContentLoaded, 'ms');
      if (metricsRef.current.firstContentfulPaint) {
        console.log('First Contentful Paint:', metricsRef.current.firstContentfulPaint, 'ms');
      }
      if (metricsRef.current.largestContentfulPaint) {
        console.log('Largest Contentful Paint:', metricsRef.current.largestContentfulPaint, 'ms');
      }
      if (metricsRef.current.cumulativeLayoutShift) {
        console.log('Cumulative Layout Shift:', metricsRef.current.cumulativeLayoutShift);
      }
      if (metricsRef.current.firstInputDelay) {
        console.log('First Input Delay:', metricsRef.current.firstInputDelay, 'ms');
      }
      console.groupEnd();
    }

    if (assetMetricsRef.current.length > 0) {
      console.group('📦 Asset Loading Metrics');
      
      const groupedAssets = assetMetricsRef.current.reduce((acc, asset) => {
        if (!acc[asset.type]) acc[asset.type] = [];
        acc[asset.type].push(asset);
        return acc;
      }, {} as Record<string, AssetLoadMetrics[]>);

      Object.entries(groupedAssets).forEach(([type, assets]) => {
        const avgLoadTime = assets.reduce((sum, asset) => sum + asset.loadTime, 0) / assets.length;
        const totalSize = assets.reduce((sum, asset) => sum + asset.size, 0);
        
        console.log(`${type.toUpperCase()}:`, {
          count: assets.length,
          avgLoadTime: Math.round(avgLoadTime),
          totalSize: Math.round(totalSize / 1024) + 'KB'
        });
      });
      
      console.groupEnd();
    }
  }, []);

  // Get performance recommendations
  const getRecommendations = useCallback((): string[] => {
    const recommendations: string[] = [];
    
    if (metricsRef.current) {
      if (metricsRef.current.firstContentfulPaint && metricsRef.current.firstContentfulPaint > 2500) {
        recommendations.push('Consider optimizing critical rendering path - FCP is slow');
      }
      
      if (metricsRef.current.largestContentfulPaint && metricsRef.current.largestContentfulPaint > 4000) {
        recommendations.push('Optimize largest content element - LCP is slow');
      }
      
      if (metricsRef.current.cumulativeLayoutShift && metricsRef.current.cumulativeLayoutShift > 0.25) {
        recommendations.push('Reduce layout shifts - CLS is high');
      }
      
      if (metricsRef.current.firstInputDelay && metricsRef.current.firstInputDelay > 300) {
        recommendations.push('Optimize JavaScript execution - FID is high');
      }
    }

    // Asset-specific recommendations
    const imageAssets = assetMetricsRef.current.filter(asset => 
      asset.type === 'image' || asset.type === 'azure-image'
    );
    const slowImages = imageAssets.filter(asset => asset.loadTime > 2000);
    
    if (slowImages.length > 0) {
      recommendations.push(`${slowImages.length} images are loading slowly (>2s)`);
    }

    const largeAssets = assetMetricsRef.current.filter(asset => asset.size > 500 * 1024); // >500KB
    if (largeAssets.length > 0) {
      recommendations.push(`${largeAssets.length} assets are large (>500KB)`);
    }

    return recommendations;
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    // Measure performance after page load
    const measurePerformance = () => {
      measurePagePerformance();
      measureAssetPerformance();
      
      // Log metrics in development
      if (process.env.NODE_ENV === 'development') {
        setTimeout(() => {
          logMetrics();
          const recommendations = getRecommendations();
          if (recommendations.length > 0) {
            console.group('💡 Performance Recommendations');
            recommendations.forEach(rec => console.warn(rec));
            console.groupEnd();
          }
        }, 1000);
      }
    };

    if (document.readyState === 'complete') {
      measurePerformance();
    } else {
      window.addEventListener('load', measurePerformance);
      return () => window.removeEventListener('load', measurePerformance);
    }
  }, [measurePagePerformance, measureAssetPerformance, logMetrics, getRecommendations]);

  return {
    metrics: metricsRef.current,
    assetMetrics: assetMetricsRef.current,
    getRecommendations,
    logMetrics,
  };
} 