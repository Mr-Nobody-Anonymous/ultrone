// Copyright (c) Ultrone Contributors. All rights reserved.
import React, { useState } from 'react';
import { Copy, Check, ChevronRight, ChevronDown } from 'lucide-react';

interface JsonViewerProps {
  data: any;
  title?: string;
  maxHeight?: string;
}

export const JsonViewer: React.FC<JsonViewerProps> = ({
  data,
  title,
  maxHeight = 'max-h-96',
}) => {
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(true);

  const jsonString = JSON.stringify(data, null, 2) || '';

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-lg border border-surface-800 bg-surface-950 font-mono text-xs overflow-hidden">
      <div className="flex items-center justify-between px-3 py-1.5 bg-surface-900/90 border-b border-surface-800">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1.5 text-surface-300 font-semibold hover:text-surface-100 transition-colors"
        >
          {expanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
          <span>{title || 'JSON Payload'}</span>
        </button>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 text-surface-400 hover:text-surface-100 transition-colors px-2 py-0.5 rounded hover:bg-surface-800"
          title="Copy raw JSON"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          <span>{copied ? 'Copied' : 'Copy'}</span>
        </button>
      </div>

      {expanded && (
        <pre
          className={`p-3 overflow-auto ${maxHeight} text-surface-300 whitespace-pre leading-relaxed select-text`}
        >
          <code>{jsonString}</code>
        </pre>
      )}
    </div>
  );
};
