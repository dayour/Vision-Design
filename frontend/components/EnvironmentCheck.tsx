"use client";

import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { API_BASE_URL } from '@/services/api';
import { checkHealthSafe } from '@/services/api-enhanced';

interface EnvironmentStatus {
  apiConnection: boolean;
  backendHealth: boolean;
  frontendEnvConfigured: boolean;
  backendMissingVars: string[];
  backendOptionalMissing: string[];
}

interface BackendEnvStatusResponse {
  set?: string[];
  missing?: string[];
  optional_missing?: string[];
}

const DEBUG_MODE = process.env.NEXT_PUBLIC_DEBUG_MODE === 'true';

export function EnvironmentCheck() {
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const checkEnvironment = async () => {
      if (checked) {
        return;
      }

      const frontendConfigured = Boolean(
        process.env.NEXT_PUBLIC_API_URL ||
        (process.env.NEXT_PUBLIC_API_HOSTNAME && process.env.NEXT_PUBLIC_API_PORT)
      );

      const newStatus: EnvironmentStatus = {
        apiConnection: false,
        backendHealth: false,
        frontendEnvConfigured: frontendConfigured,
        backendMissingVars: [],
        backendOptionalMissing: [],
      };

      try {
        const healthResult = await checkHealthSafe();

        newStatus.apiConnection = healthResult.success;
        newStatus.backendHealth = healthResult.success;

        if (newStatus.backendHealth) {
          try {
            const envResponse = await fetch(`${API_BASE_URL}/env/status`, {
              method: 'GET',
              headers: {
                Accept: 'application/json',
              },
            });

            if (envResponse.ok) {
              const envJson = (await envResponse.json()) as BackendEnvStatusResponse;
              newStatus.backendMissingVars = envJson.missing ?? [];
              newStatus.backendOptionalMissing = envJson.optional_missing ?? [];
            } else if (DEBUG_MODE) {
              console.debug('Backend env status request failed', envResponse.status);
            }
          } catch (envError) {
            if (DEBUG_MODE) {
              console.debug('Failed to retrieve backend env status', envError);
            }
          }
        }

        if (DEBUG_MODE) {
          console.debug('Environment check status:', newStatus);
        }

        if (!newStatus.apiConnection) {
          toast.error('Backend API connection failed', {
            description: `Cannot connect to ${API_BASE_URL}. Verify the backend is running.`,
            duration: 10000,
          });
        } else if (newStatus.backendMissingVars.length > 0) {
          const missingList = newStatus.backendMissingVars.join(", ");
          toast.error('Backend configuration incomplete', {
            description: `Missing required variables: ${missingList}`,
            duration: 10000,
          });
        } else if (!newStatus.frontendEnvConfigured) {
          toast.warning('Missing front-end environment settings', {
            description: 'NEXT_PUBLIC_API_URL or host/port variables are not configured.',
            duration: 8000,
          });
        } else if (newStatus.backendOptionalMissing.length > 0) {
          const optionalList = newStatus.backendOptionalMissing.join(", ");
          toast.warning('Optional backend variables unavailable', {
            description: optionalList,
            duration: 8000,
          });
        } else if (newStatus.backendHealth) {
          toast.success('System ready', {
            description: 'Backend API and environment configuration verified.',
            duration: 3000,
          });
        }
      } catch (error) {
        toast.error('System check failed', {
          description: `Error: ${error instanceof Error ? error.message : "Unknown error"}`,
          duration: 10000,
        });

        if (DEBUG_MODE) {
          console.error('Environment check failed:', error);
        }
      } finally {
        setChecked(true);
      }
    };

    const timeoutId = window.setTimeout(checkEnvironment, 1000);
    return () => window.clearTimeout(timeoutId);
  }, [checked]);

  return null;
}
