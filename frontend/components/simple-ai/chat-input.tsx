"use client";

import { useState, useCallback, KeyboardEvent } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Send, Loader2 } from "lucide-react";
import { cn } from "@/utils/utils";

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  placeholder?: string;
  disabled?: boolean;
  submitLabel?: string;
  maxRows?: number;
  className?: string;
}

export function ChatInput({
  value,
  onChange,
  onSubmit,
  placeholder = "Type your message...",
  disabled = false,
  submitLabel = "Send",
  maxRows = 6,
  className,
}: ChatInputProps) {
  const [rows, setRows] = useState(1);

  const handleKeyDown = useCallback((e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!disabled && value.trim()) {
        onSubmit();
      }
    }
  }, [disabled, value, onSubmit]);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value;
    onChange(newValue);
    
    // Auto-resize based on content
    const lineHeight = 24;
    const padding = 16;
    const scrollHeight = e.target.scrollHeight;
    const newRows = Math.min(
      Math.max(1, Math.floor((scrollHeight - padding) / lineHeight)),
      maxRows
    );
    setRows(newRows);
  }, [onChange, maxRows]);

  const canSubmit = !disabled && value.trim().length > 0;

  return (
    <div className={cn("flex gap-2 items-end", className)}>
      <div className="flex-1 relative">
        <Textarea
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={rows}
          className="resize-none pr-12 min-h-[40px]"
          style={{
            height: 'auto',
          }}
        />
        <div className="absolute right-2 top-2">
          <Button
            size="sm"
            variant="ghost"
            className="h-8 w-8 p-0"
            onClick={onSubmit}
            disabled={!canSubmit}
          >
            {disabled ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            <span className="sr-only">{submitLabel}</span>
          </Button>
        </div>
      </div>
    </div>
  );
}
