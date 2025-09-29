"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { CheckCircle, XCircle, AlertCircle, ChevronDown, ChevronRight, ExternalLink, Loader2 } from "lucide-react";
import { toast } from "sonner";

interface AuthStatus {
  authenticated: boolean;
  error?: string;
  account?: any;
  context?: any;
  method?: string;
  note?: string;
  environment_info?: string;
  status_info?: string;
}

interface AuthenticationStatus {
  azure_cli: AuthStatus;
  power_platform: AuthStatus;
  microsoft_graph: AuthStatus;
  github: AuthStatus;
  dataverse?: {
    enabled: boolean;
    configured: boolean;
  };
}

interface SetupInstructions {
  [key: string]: {
    install: string;
    authenticate: string;
    verify: string;
  };
}

export function CliAuthStatus() {
  const [authStatus, setAuthStatus] = useState<AuthenticationStatus | null>(null);
  const [instructions, setInstructions] = useState<SetupInstructions>({});
  const [loading, setLoading] = useState(true);
  const [isOpen, setIsOpen] = useState(false);

  const fetchAuthStatus = async () => {
    try {
      setLoading(true);
      const response = await fetch("/api/v1/auth/status");
      const data = await response.json();
      
      if (data.success) {
        setAuthStatus(data.authentication_status);
      } else {
        toast.error("Failed to fetch authentication status");
      }
    } catch (error) {
      console.error("Error fetching auth status:", error);
      toast.error("Error fetching authentication status");
    } finally {
      setLoading(false);
    }
  };

  const fetchInstructions = async () => {
    try {
      const response = await fetch("/api/v1/auth/setup-instructions");
      const data = await response.json();
      
      if (data.success) {
        setInstructions(data.setup_instructions);
      }
    } catch (error) {
      console.error("Error fetching setup instructions:", error);
    }
  };

  useEffect(() => {
    fetchAuthStatus();
    fetchInstructions();
  }, []);

  const getStatusIcon = (status: AuthStatus) => {
    if (status.authenticated) {
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    } else if (status.error?.includes("not installed")) {
      return <AlertCircle className="h-4 w-4 text-orange-500" />;
    } else {
      return <XCircle className="h-4 w-4 text-red-500" />;
    }
  };

  const getStatusBadge = (status: AuthStatus) => {
    if (status.authenticated) {
      return <Badge variant="default" className="bg-green-100 text-green-800">Connected</Badge>;
    } else if (status.error?.includes("not installed")) {
      return <Badge variant="secondary">Not Installed</Badge>;
    } else {
      return <Badge variant="destructive">Not Connected</Badge>;
    }
  };

  const authServices = [
    {
      key: "azure_cli",
      name: "Azure CLI",
      description: "Azure resource authentication",
      docs: "https://docs.microsoft.com/en-us/cli/azure/"
    },
    {
      key: "power_platform",
      name: "Power Platform CLI",
      description: "Dataverse and Power Platform integration",
      docs: "https://docs.microsoft.com/en-us/power-platform/developer/cli/introduction"
    },
    {
      key: "microsoft_graph",
      name: "Microsoft Graph",
      description: "Microsoft 365 integration",
      docs: "https://docs.microsoft.com/en-us/graph/powershell/installation"
    },
    {
      key: "github",
      name: "GitHub CLI",
      description: "Repository integration",
      docs: "https://cli.github.com/"
    }
  ];

  if (loading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            Checking CLI Authentication...
          </CardTitle>
        </CardHeader>
      </Card>
    );
  }

  const authenticatedCount = authStatus ? 
    Object.values(authStatus).filter(status => 
      typeof status === 'object' && 'authenticated' in status && status.authenticated
    ).length : 0;

  const totalServices = authServices.length;

  return (
    <Card>
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CollapsibleTrigger asChild>
          <CardHeader className="pb-2 cursor-pointer hover:bg-muted/50 transition-colors">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CardTitle className="text-sm font-medium">
                  CLI Authentication Status
                </CardTitle>
                <Badge variant="outline">
                  {authenticatedCount}/{totalServices}
                </Badge>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    fetchAuthStatus();
                  }}
                >
                  Refresh
                </Button>
                {isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              </div>
            </div>
            <CardDescription className="text-xs">
              Integration status for development tools and services
            </CardDescription>
          </CardHeader>
        </CollapsibleTrigger>
        
        <CollapsibleContent>
          <CardContent className="pt-0">
            <div className="space-y-3">
              {authServices.map((service) => {
                const status = authStatus?.[service.key as keyof AuthenticationStatus] as AuthStatus;
                if (!status) return null;

                return (
                  <div key={service.key} className="flex items-start justify-between p-3 rounded-lg border bg-muted/20">
                    <div className="flex items-start gap-3 flex-1">
                      {getStatusIcon(status)}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <p className="text-sm font-medium">{service.name}</p>
                          {getStatusBadge(status)}
                        </div>
                        <p className="text-xs text-muted-foreground mb-2">
                          {service.description}
                        </p>
                        
                        {status.authenticated ? (
                          <div className="text-xs text-muted-foreground">
                            {status.account?.name && (
                              <p>Account: {status.account.name}</p>
                            )}
                            {status.context?.account && (
                              <p>Account: {status.context.account}</p>
                            )}
                            {status.method && (
                              <p>Method: {status.method}</p>
                            )}
                            {status.environment_info && (
                              <p className="mt-1 font-mono text-xs bg-muted p-1 rounded">
                                {status.environment_info.slice(0, 100)}...
                              </p>
                            )}
                          </div>
                        ) : (
                          <div className="text-xs space-y-1">
                            <p className="text-red-600">{status.error}</p>
                            {instructions[service.key] && (
                              <div className="mt-2 p-2 bg-muted rounded text-xs">
                                <p><strong>Install:</strong> {instructions[service.key].install}</p>
                                <p><strong>Auth:</strong> {instructions[service.key].authenticate}</p>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                      
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 w-6 p-0"
                        onClick={() => window.open(service.docs, '_blank')}
                      >
                        <ExternalLink className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                );
              })}

              {/* Dataverse Status */}
              {authStatus?.dataverse && (
                <div className="flex items-start justify-between p-3 rounded-lg border bg-muted/20">
                  <div className="flex items-start gap-3 flex-1">
                    {authStatus.dataverse.enabled ? 
                      <CheckCircle className="h-4 w-4 text-green-500" /> : 
                      <XCircle className="h-4 w-4 text-red-500" />
                    }
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="text-sm font-medium">Microsoft Dataverse</p>
                        <Badge variant={authStatus.dataverse.enabled ? "default" : "destructive"} 
                               className={authStatus.dataverse.enabled ? "bg-green-100 text-green-800" : ""}>
                          {authStatus.dataverse.enabled ? "Available" : "Not Available"}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Rich metadata storage and indexing
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        Configured: {authStatus.dataverse.configured ? "Yes" : "No"}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              <div className="pt-2 border-t">
                <p className="text-xs text-muted-foreground">
                  <strong>Vision Design</strong> integrates with multiple CLI tools for streamlined authentication and development workflows. 
                  Configure these tools to enable full functionality including Dataverse integration, Azure resource management, and GitHub operations.
                </p>
              </div>
            </div>
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
}