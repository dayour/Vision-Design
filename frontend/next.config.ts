import type { NextConfig } from "next";

// Bundle analyzer
// eslint-disable-next-line @typescript-eslint/no-require-imports
const withBundleAnalyzer = require('@next/bundle-analyzer')({
  enabled: process.env.ANALYZE === 'true',
});

// Resolve flux provider from either build-time or already-prefixed env var
const fluxProvider = (process.env.FLUX_MODEL_PROVIDER || process.env.NEXT_PUBLIC_FLUX_MODEL_PROVIDER || '').toLowerCase();
const resolvedDefaultImageModel = process.env.DEFAULT_IMAGE_MODEL
  || process.env.NEXT_PUBLIC_DEFAULT_IMAGE_MODEL
  || ((fluxProvider === 'foundry' || fluxProvider === 'bfl') ? 'flux-pro' : 'gpt-image-1');

const nextConfig: NextConfig = {
  /* config options here */
  // output: 'standalone', // Disabled for now to use 'next start' normally
  env: {
    // Public flags that can be consumed in the browser. Do NOT expose secrets like API keys here.
    NEXT_PUBLIC_FLUX_MODEL_PROVIDER: fluxProvider || '',
    NEXT_PUBLIC_DEFAULT_IMAGE_MODEL: resolvedDefaultImageModel,
    // Foundry (Flux) endpoints - safe to expose if they are not accompanied by secrets
    NEXT_PUBLIC_FOUNDRY_ENDPOINT: process.env.FOUNDRY_ENDPOINT || '',
    NEXT_PUBLIC_FOUNDRY_FLUX_PRO_ENDPOINT: process.env.FOUNDRY_FLUX_PRO_ENDPOINT || '',
    NEXT_PUBLIC_FOUNDRY_FLUX_KONTEXT_ENDPOINT: process.env.FOUNDRY_FLUX_KONTEXT_ENDPOINT || '',
    NEXT_PUBLIC_FOUNDRY_DEPLOYMENT_FLUX_PRO: process.env.FOUNDRY_DEPLOYMENT_FLUX_PRO || '',
    NEXT_PUBLIC_FOUNDRY_DEPLOYMENT_FLUX_KONTEXT: process.env.FOUNDRY_DEPLOYMENT_FLUX_KONTEXT || '',
  },
  // Add allowedDevOrigins to prevent the CORS warning in development
  allowedDevOrigins: ['localhost', '127.0.0.1', '::1'],
  
  // Enable compression
  compress: true,
  
  // Optimize static generation
  trailingSlash: false,
  
  // Image optimization configuration for Dataverse storage
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '8000',
        pathname: '/api/v1/gallery/assets/**',
      },
      {
        protocol: 'https',
        hostname: '*.azurewebsites.net',
        pathname: '/api/v1/gallery/assets/**',
      }
    ],
    // Image optimization settings
    minimumCacheTTL: 86400, // 24 hours
    formats: ['image/webp', 'image/avif'],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
    // Enable unoptimized images for Dataverse served content
    unoptimized: false,
  },
  
  experimental: {
    serverActions: {
      bodySizeLimit: '26mb', // Increased for large image uploads
    },
    // Enable modern bundling optimizations
    optimizePackageImports: ['lucide-react', '@radix-ui/react-icons'],
    // Enable turbo mode for faster builds
    turbo: {
      rules: {
        '*.svg': {
          loaders: ['@svgr/webpack'],
          as: '*.js',
        },
      },
    },
  },
  
  
  // Disable ESLint during builds
  eslint: {
    ignoreDuringBuilds: true,
  },
  // Disable TypeScript checks during builds temporarily
  typescript: {
    ignoreBuildErrors: true,
  },
  
  // Enhanced headers with caching and security
  async headers() {
    return [
      {
        // Add CORS headers to all API routes
        source: "/api/:path*",
        headers: [
          { key: "Access-Control-Allow-Credentials", value: "true" },
          { key: "Access-Control-Allow-Origin", value: "*" },
          { key: "Access-Control-Allow-Methods", value: "GET,POST,PUT,DELETE,OPTIONS" },
          { key: "Access-Control-Allow-Headers", value: "X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version, Authorization" },
        ]
      },
      {
        // Service worker caching
        source: '/sw.js',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=0, must-revalidate',
          },
          {
            key: 'Service-Worker-Allowed',
            value: '/',
          },
        ],
      },
      {
        // Cache static assets
        source: '/(.*)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },

      {
        // Security headers
        source: '/(.*)',
        headers: [
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
        ],
      },
    ];
  },
};

export default withBundleAnalyzer(nextConfig);
