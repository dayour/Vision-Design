"use client";

import { ReactNode } from "react";
import { cn } from "@/utils/utils";

interface MessageContentProps {
  content: string | ReactNode;
  className?: string;
}

export function MessageContent({ content, className }: MessageContentProps) {
  // If content is already a React node, render it directly
  if (typeof content !== 'string') {
    return <div className={cn("prose prose-sm max-w-none", className)}>{content}</div>;
  }

  // Handle string content with basic formatting
  const formatContent = (text: string): ReactNode => {
    // Split by paragraphs (double newlines)
    const paragraphs = text.split(/\n\s*\n/);
    
    return paragraphs.map((paragraph, pIndex) => {
      // Handle lists (lines starting with - or *)
      if (paragraph.includes('\n-') || paragraph.includes('\n*')) {
        const lines = paragraph.split('\n');
        const items: string[] = [];
        let currentItem = '';
        
        lines.forEach(line => {
          const trimmed = line.trim();
          if (trimmed.startsWith('-') || trimmed.startsWith('*')) {
            if (currentItem) items.push(currentItem);
            currentItem = trimmed.substring(1).trim();
          } else if (currentItem && trimmed) {
            currentItem += ' ' + trimmed;
          } else if (!currentItem && trimmed) {
            // Regular line before list starts
            if (items.length === 0) {
              return <p key={pIndex} className="mb-3">{trimmed}</p>;
            }
          }
        });
        
        if (currentItem) items.push(currentItem);
        
        return (
          <div key={pIndex} className="mb-3">
            <ul className="list-disc list-inside space-y-1">
              {items.map((item, iIndex) => (
                <li key={iIndex} className="text-sm">{item}</li>
              ))}
            </ul>
          </div>
        );
      }
      
      // Handle numbered lists
      if (/^\d+\./.test(paragraph.trim())) {
        const lines = paragraph.split('\n');
        const items: string[] = [];
        let currentItem = '';
        
        lines.forEach(line => {
          const trimmed = line.trim();
          if (/^\d+\./.test(trimmed)) {
            if (currentItem) items.push(currentItem);
            currentItem = trimmed.replace(/^\d+\.\s*/, '');
          } else if (currentItem && trimmed) {
            currentItem += ' ' + trimmed;
          }
        });
        
        if (currentItem) items.push(currentItem);
        
        return (
          <div key={pIndex} className="mb-3">
            <ol className="list-decimal list-inside space-y-1">
              {items.map((item, iIndex) => (
                <li key={iIndex} className="text-sm">{item}</li>
              ))}
            </ol>
          </div>
        );
      }
      
      // Regular paragraph
      return (
        <p key={pIndex} className="mb-3 text-sm leading-relaxed whitespace-pre-wrap">
          {paragraph.trim()}
        </p>
      );
    });
  };

  return (
    <div className={cn("text-sm space-y-2", className)}>
      {formatContent(content)}
    </div>
  );
}