import { NextResponse } from 'next/server';

export async function GET() {
  try {
    // Check if we can connect to the backend API
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
    
    const response = await fetch(`${backendUrl}/health`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
      // Add timeout to prevent hanging
      signal: AbortSignal.timeout(5000), // 5 second timeout
    });

    if (!response.ok) {
      throw new Error(`Backend health check failed: ${response.status}`);
    }

    const backendData = await response.json();

    return NextResponse.json({
      status: 'healthy',
      frontend: {
        timestamp: new Date().toISOString(),
        environment: process.env.NODE_ENV,
        api_url: backendUrl,
      },
      backend: backendData,
    });
  } catch (error) {
    console.error('Health check failed:', error);
    
    return NextResponse.json(
      {
        status: 'unhealthy',
        frontend: {
          timestamp: new Date().toISOString(),
          environment: process.env.NODE_ENV,
          api_url: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
        },
        error: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 503 }
    );
  }
}