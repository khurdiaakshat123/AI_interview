import React, { useMemo } from 'react';
import { marked } from 'marked';

interface LCMarkdownViewerProps {
  content: string;
  className?: string;
}

export const LCMarkdownViewer: React.FC<LCMarkdownViewerProps> = ({ content, className = '' }) => {
  const html = useMemo(() => {
    if (!content) return '';
    
    // Normalize any lingering asset links
    let processed = content
      .replace(/!\[(.*?)\]\(\.\/assets\/(.*?)\)/g, '![$1](/lc_assets/$2)')
      .replace(/!\[(.*?)\]\(assets\/(.*?)\)/g, '![$1](/lc_assets/$2)')
      .replace(/src=["']\.\/assets\/(.*?)["']/g, 'src="/lc_assets/$1"')
      .replace(/src=["']assets\/(.*?)["']/g, 'src="/lc_assets/$1"');

    try {
      return marked.parse(processed, {
        gfm: true,
        breaks: true,
      }) as string;
    } catch (e) {
      console.error('Failed to parse markdown:', e);
      return processed;
    }
  }, [content]);

  return (
    <div 
      className={`lc-statement text-[13.5px] leading-relaxed text-text ${className}`}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
};
