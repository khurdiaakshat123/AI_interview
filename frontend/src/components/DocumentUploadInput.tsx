import React, { useState, useRef } from 'react';
import { Upload, FileText, Image, FileCode, CheckCircle2, Loader2, X, AlertCircle } from 'lucide-react';
import { BASE_URL } from '../services/api';

interface DocumentUploadInputProps {
  label: string;
  sublabel?: string;
  value: string;
  onChange: (text: string) => void;
  onMetaExtracted?: (meta: { name?: string; email?: string }) => void;
  placeholder?: string;
  rows?: number;
  badgeColor?: 'indigo' | 'emerald' | 'brand';
  required?: boolean;
}

export const DocumentUploadInput: React.FC<DocumentUploadInputProps> = ({
  label,
  sublabel,
  value,
  onChange,
  onMetaExtracted,
  placeholder = 'Paste text or upload a document...',
  rows = 4,
  badgeColor = 'indigo',
  required = false
}) => {
  const [activeMode, setActiveMode] = useState<'upload' | 'text'>('text');
  const [uploading, setUploading] = useState(false);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  const [extractedStats, setExtractedStats] = useState<{ type: string; words: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleFileUpload = async (file: File) => {
    if (!file) return;
    setError(null);
    setUploading(true);
    setUploadedFileName(file.name);

    try {
      const formData = new FormData();
      formData.append('file', file);

      // Relative path works via Vite proxy in dev and same-origin in prod
      const endpoint = `${BASE_URL}/candidate/extract-file`;
      let res: Response;
      try {
        res = await fetch(endpoint, {
          method: 'POST',
          body: formData
        });
        if (!res.ok && res.status === 404 && endpoint !== '/api/candidate/extract-file') {
          const fallbackRes = await fetch('/api/candidate/extract-file', {
            method: 'POST',
            body: formData
          });
          if (fallbackRes.ok) {
            res = fallbackRes;
          }
        }
      } catch {
        res = await fetch('/api/candidate/extract-file', {
          method: 'POST',
          body: formData
        });
      }

      if (!res.ok) {
        const rawText = await res.text().catch(() => '');
        let errMsg = `Failed to extract text (${res.status})`;
        if (rawText) {
          try {
            const errJson = JSON.parse(rawText);
            errMsg = errJson.detail || errMsg;
          } catch {
            errMsg = rawText.length > 250 ? rawText.slice(0, 250) + '...' : rawText;
          }
        }
        throw new Error(errMsg);
      }

      const data = await res.json();
      if (data.extracted_text) {
        onChange(data.extracted_text);
      }
      setExtractedStats({
        type: data.file_type || 'file',
        words: data.word_count || 0
      });

      if (onMetaExtracted && (data.candidate_name || data.candidate_email)) {
        onMetaExtracted({
          name: data.candidate_name,
          email: data.candidate_email
        });
      }

      setActiveMode('text'); // switch to text view so candidate can review the extracted text
    } catch (err: any) {
      console.error(err);
      setError(err?.message || 'Error parsing document.');
      setUploadedFileName(null);
      setExtractedStats(null);
    } finally {
      setUploading(false);
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const colorClasses = {
    indigo: 'text-text border-border bg-surface',
    emerald: 'text-success border-success/30 bg-success/10',
    brand: 'text-accent border-accent/30 bg-accent/10'
  }[badgeColor];

  return (
    <div className='space-y-2 text-xs'>
      <div className='flex items-center justify-between'>
        <div>
          <label className='font-medium text-text block'>
            {label} {required && <span className='text-danger'>*</span>}
          </label>
          {sublabel && <p className='text-[11px] text-text-muted'>{sublabel}</p>}
        </div>

        {/* Mode Switcher */}
        <div className="flex items-center p-0.5 rounded-md bg-bg border border-border text-[11px]">
          <button
            type="button"
            onClick={() => setActiveMode('text')}
            className={`px-2.5 py-1 rounded transition-colors ${
              activeMode === 'text'
                ? 'bg-surface text-text font-medium'
                : 'text-text-muted hover:text-text'
            }`}
          >
            Type / Paste Text
          </button>
          <button
            type="button"
            onClick={() => setActiveMode('upload')}
            className={`px-2.5 py-1 rounded flex items-center gap-1 transition-colors ${
              activeMode === 'upload'
                ? 'bg-surface text-text font-medium'
                : 'text-text-muted hover:text-text'
            }`}
          >
            <Upload className="w-3 h-3" />
            Upload PDF / Image
          </button>
        </div>
      </div>

      {/* Upload Drop Zone Mode */}
      {activeMode === 'upload' && (
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={onDrop}
          onClick={() => fileInputRef.current?.click()}
          className='p-6 rounded-card border border-dashed border-border hover:border-accent bg-bg transition-colors cursor-pointer text-center space-y-2'
        >
          <input
            ref={fileInputRef}
            type='file'
            accept='.pdf,.docx,.doc,.png,.jpg,.jpeg,.webp,.txt,.md'
            className='hidden'
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                handleFileUpload(e.target.files[0]);
              }
              if (e.target) e.target.value = '';
            }}
          />

          <div className='w-9 h-9 mx-auto rounded-md bg-surface border border-border flex items-center justify-center text-text-muted'>
            {uploading ? (
              <Loader2 className='w-4 h-4 animate-spin text-accent' />
            ) : (
              <Upload className='w-4 h-4 text-text-muted' />
            )}
          </div>

          <div>
            <span className='font-medium text-text block text-xs'>
              {uploading ? 'Extracting document text...' : 'Click to select or drag and drop file'}
            </span>
            <span className='text-[11px] text-text-muted'>
              Supports PDF, Word (.docx), image screenshots, and plain text
            </span>
          </div>
        </div>
      )}

      {/* Uploaded File Badge */}
      {uploadedFileName && (
        <div className="flex items-center justify-between p-2 rounded-md border border-border bg-surface text-[11px] text-text">
          <div className='flex items-center gap-2'>
            <CheckCircle2 className='w-3.5 h-3.5 text-success flex-shrink-0' />
            <span className='font-medium'>{uploadedFileName}</span>
            {extractedStats && (
              <span className='text-text-muted font-mono'>
                ({extractedStats.type.toUpperCase()} • {extractedStats.words} words)
              </span>
            )}
          </div>
          <button
            type='button'
            onClick={() => {
              setUploadedFileName(null);
              setExtractedStats(null);
            }}
            className='text-text-muted hover:text-text'
          >
            <X className='w-3.5 h-3.5' />
          </button>
        </div>
      )}

      {error && (
        <div className='p-2 rounded-md bg-danger-subtle border border-danger/40 text-[11px] text-danger flex items-center gap-2'>
          <AlertCircle className='w-3.5 h-3.5 text-danger' />
          <span>{error}</span>
        </div>
      )}

      {/* Textarea (Always available in text mode or after upload for candidate to review) */}
      {activeMode === 'text' && (
        <div 
          className='relative group'
          onDragOver={(e) => e.preventDefault()}
          onDrop={onDrop}
        >
          <textarea
            value={value}
            onChange={(e) => {
              const val = e.target.value;
              onChange(val);
              if (onMetaExtracted && val.length > 25) {
                const emailMatch = val.match(/[\w.-]+@[\w.-]+\.\w+/);
                const email = emailMatch ? emailMatch[0].toLowerCase() : undefined;
                const lines = val.split('\n').map(l => l.trim()).filter(Boolean);
                let name: string | undefined;
                for (const line of lines.slice(0, 6)) {
                  const seg = line.split(/[|•·\t]/)[0].trim();
                  const words = seg.split(/\s+/);
                  if (
                    !seg.includes('@') &&
                    !/(http|linkedin|github|curriculum|resume|page|email|phone|summary|profile)/i.test(seg) &&
                    !/\d/.test(seg) &&
                    words.length >= 2 && words.length <= 4 &&
                    seg.length < 40 &&
                    words.every(w => /^[A-Za-z]/.test(w))
                  ) {
                    name = seg;
                    break;
                  }
                }
                if (name || email) {
                  onMetaExtracted({ name, email });
                }
              }
            }}
            rows={rows}
            placeholder={placeholder}
            className='w-full p-3 rounded-md bg-bg border border-border text-xs text-text font-mono leading-relaxed focus:border-accent focus:outline-none resize-none'
            required={required}
          />
          <div className='absolute right-2.5 bottom-2.5 flex items-center gap-2'>
            <button
              type='button'
              onClick={() => {
                setActiveMode('upload');
                setTimeout(() => fileInputRef.current?.click(), 50);
              }}
              className='text-[10px] text-text-muted hover:text-text bg-surface border border-border hover:border-border-focus px-2 py-0.5 rounded flex items-center gap-1 transition-colors'
            >
              <Upload className='w-2.5 h-2.5' />
              Upload PDF
            </button>
            {value && (
              <span className='text-[10px] text-text-muted font-mono bg-surface px-1.5 py-0.5 rounded border border-border'>
                {value.split(/\s+/).filter(Boolean).length} words
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
