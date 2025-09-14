"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { MessageContent } from "@/components/simple-ai/message-content";
import { Copy, Download, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

interface AnalysisResultsProps {
  results: any;
  isLoading: boolean;
  customPrompt: string;
}

export function AnalysisResults({ results, isLoading, customPrompt }: AnalysisResultsProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 animate-pulse text-primary" />
            Analyzing Image...
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="p-3 bg-muted rounded-lg">
            <Skeleton className="h-4 w-full mb-2" />
            <Skeleton className="h-4 w-3/4" />
          </div>
          <Skeleton className="h-20 w-full" />
          <div className="flex gap-2">
            <Skeleton className="h-6 w-16" />
            <Skeleton className="h-6 w-20" />
            <Skeleton className="h-6 w-18" />
          </div>
          <Skeleton className="h-16 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (!results) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Analysis Results</CardTitle>
        </CardHeader>
        <CardContent className="text-center text-muted-foreground py-12">
          <Sparkles className="h-12 w-12 mx-auto mb-4 opacity-20" />
          <p className="text-lg mb-2">Ready to analyze</p>
          <p className="text-sm">Upload an image and enter a custom prompt to see analysis results</p>
        </CardContent>
      </Card>
    );
  }

  const handleCopyResults = () => {
    const resultText = `Analysis Results:\n\nPrompt: ${customPrompt}\n\nDescription: ${results.description}\n\nProducts: ${results.products}\n\nTags: ${results.tags?.join(', ')}\n\nFeedback: ${results.feedback}`;
    navigator.clipboard.writeText(resultText);
    toast.success("Results copied to clipboard");
  };

  const handleDownloadResults = () => {
    const resultData = {
      custom_prompt: customPrompt,
      timestamp: new Date().toISOString(),
      ...results
    };
    const blob = new Blob([JSON.stringify(resultData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `custom-analysis-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Analysis results downloaded");
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-primary" />
          Analysis Results
        </CardTitle>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleCopyResults}>
            <Copy className="h-4 w-4 mr-1" />
            Copy
          </Button>
          <Button variant="outline" size="sm" onClick={handleDownloadResults}>
            <Download className="h-4 w-4 mr-1" />
            Export
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Custom Prompt Used */}
        <div>
          <h4 className="font-medium mb-2 text-sm text-muted-foreground">ANALYSIS PROMPT USED</h4>
          <div className="p-3 bg-muted rounded-lg text-sm border-l-4 border-primary">
            {customPrompt}
          </div>
        </div>

        {/* Description */}
        <div>
          <h4 className="font-medium mb-3 flex items-center gap-2">
            📝 Analysis Description
          </h4>
          <div className="prose prose-sm max-w-none">
            <MessageContent content={results.description} />
          </div>
        </div>

        {/* Products */}
        {results.products && results.products !== "None identified" && results.products !== "No products identified" && (
          <div>
            <h4 className="font-medium mb-3 flex items-center gap-2">
              🏷️ Products/Brands Identified
            </h4>
            <div className="p-3 bg-muted rounded-lg">
              <MessageContent content={results.products} />
            </div>
          </div>
        )}

        {/* Tags */}
        {results.tags && results.tags.length > 0 && (
          <div>
            <h4 className="font-medium mb-3 flex items-center gap-2">
              🏷️ Metadata Tags
            </h4>
            <div className="flex flex-wrap gap-2">
              {results.tags.map((tag: string, idx: number) => (
                <Badge key={idx} variant="secondary" className="bg-primary/10 text-primary hover:bg-primary/20">
                  {tag}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Feedback */}
        {results.feedback && (
          <div>
            <h4 className="font-medium mb-3 flex items-center gap-2">
              💡 Feedback & Suggestions
            </h4>
            <div className="border-l-4 border-amber-400 bg-amber-50 dark:bg-amber-950/20 p-3 rounded-lg">
              <MessageContent content={results.feedback} />
            </div>
          </div>
        )}

        {/* Analysis Metadata */}
        <div className="pt-4 border-t">
          <p className="text-xs text-muted-foreground">
            Analysis completed at {new Date().toLocaleString()} using custom prompt analysis
          </p>
        </div>
      </CardContent>
    </Card>
  );
}