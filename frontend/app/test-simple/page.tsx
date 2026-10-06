'use client';

import { useState, useEffect } from 'react';
import { API_BASE_URL } from '@/services/api';

async function testApiConnection() {
  try {
    console.log('Testing API connection to:', API_BASE_URL);
    
    // Test 1: Health check
    const healthResponse = await fetch(`${API_BASE_URL}/health`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' }
    });
    
    const healthData = healthResponse.ok ? await healthResponse.json() : { error: 'Health check failed' };
    
    // Test 2: Simple endpoint test  
    const imageResponse = await fetch(`${API_BASE_URL}/gallery/images?limit=1`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' }
    });
    
    const imageData = imageResponse.ok ? await imageResponse.json() : { error: 'Images endpoint failed' };
    
    return {
      baseUrl: API_BASE_URL,
      health: {
        status: healthResponse.status,
        ok: healthResponse.ok,
        data: healthData
      },
      images: {
        status: imageResponse.status,
        ok: imageResponse.ok,
        data: imageData
      },
      environment: {
        api_url: process.env.NEXT_PUBLIC_API_URL,
        debug_mode: process.env.NEXT_PUBLIC_DEBUG_MODE,
        flux_provider: process.env.NEXT_PUBLIC_FLUX_MODEL_PROVIDER,
        default_model: process.env.NEXT_PUBLIC_DEFAULT_IMAGE_MODEL
      }
    };
  } catch (error) {
    console.error('API connection test error:', error);
    throw error;
  }
}

export default function TestSimplePage() {
  const [status, setStatus] = useState('Starting API tests...');
  const [data, setData] = useState(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    console.log('Running API connection tests...');
    setStatus('Testing API connection...');
    
    testApiConnection()
      .then((result) => {
        console.log('API test results:', result);
        setStatus('Tests completed');
        setData(result);
      })
      .catch((error) => {
        console.error('API test error:', error);
        setError(error.message);
        setStatus('Tests failed');
      });
  }, []);

  return (
    <div className="p-5 font-mono max-w-3xl">
      <h1>API Connection Test</h1>
      <div className="mb-5">
        <strong>Status:</strong> {status}
      </div>
      
      {error && (
        <div className="bg-red-50 border border-red-400 p-2.5 mb-5 rounded">
          <strong>Error:</strong> {error}
        </div>
      )}
      
      {data && (
        <div>
          <h2>Test Results</h2>
          <div className="bg-gray-100 p-2.5 rounded">
            <pre className="text-xs overflow-auto">
              {JSON.stringify(data, null, 2)}
            </pre>
          </div>
          
          <h3>Quick Status</h3>
          <ul>
            <li>Base URL: {data.baseUrl}</li>
            <li>Health Check: {data.health?.ok ? '✅ Pass' : '❌ Fail'} ({data.health?.status})</li>
            <li>Images Endpoint: {data.images?.ok ? '✅ Pass' : '❌ Fail'} ({data.images?.status})</li>
          </ul>
        </div>
      )}
    </div>
  );
}