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
      } catch {
        res = await fetch('/api/candidate/extract-file', {
          method: 'POST',
          body: formData
        });
      }

      if (!res.ok) {
        let errMsg = `Failed to extract text (${res.status})`;
        try {
          const errJson = await res.json();
          errMsg = errJson.detail || errMsg;
        } catch {
          const text = await res.text();
          if (text) errMsg = text;
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
      setError(err.message || 'Error parsing document.');
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
    indigo: 'text-indigo-400 border-indigo-500/40 bg-indigo-950/20',
    emerald: 'text-emerald-400 border-emerald-500/40 bg-emerald-950/20',
    brand: 'text-brand-400 border-brand-500/40 bg-brand-950/20'
  }[badgeColor];

  return (
    <div className='space-y-2 text-xs'>
      <div className='flex items-center justify-between'>
        <div>
          <label className='font-bold text-slate-200 block'>
            {label} {required && <span className='text-red-400'>*</span>}
          </label>
          {sublabel && <p className='text-[11px] text-slate-400'>{sublabel}</p>}
        </div>

        {/* Mode Switcher */}
        <div className="flex items-center p-0.5 rounded-lg bg-slate-950 border border-slate-800 text-[11px] font-medium">
          <button
            type="button"
            onClick={() => setActiveMode('text')}
            className={`px-2.5 py-1 rounded-md transition-all ${
              activeMode === 'text'
                ? 'bg-slate-800 text-white shadow-sm font-semibold'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Type / Paste Text
          </button>
          <button
            type="button"
            onClick={() => setActiveMode('upload')}
            className={`px-2.5 py-1 rounded-md flex items-center gap-1 transition-all ${
              activeMode === 'upload'
                ? 'bg-slate-800 text-white shadow-sm font-semibold'
                : 'text-slate-400 hover:text-slate-200'
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
          className='p-6 rounded-2xl border-2 border-dashed border-slate-700 hover:border-brand-500/60 bg-slate-950/50 hover:bg-slate-900/50 transition-all cursor-pointer text-center space-y-2'
        >
          <input
            ref={fileInputRef}
            type='file'
            accept='.pdf,.png,.jpg,.jpeg,.webp,.txt,.md'
            className='hidden'
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                handleFileUpload(e.target.files[0]);
              }
              if (e.target) e.target.value = '';
            }}
          />

          <div className='w-10 h-10 mx-auto rounded-xl bg-slate-800/80 border border-slate-700 flex items-center justify-center text-slate-300'>
            {uploading ? (
              <Loader2 className='w-5 h-5 animate-spin text-brand-400' />
            ) : (
              <Upload className='w-5 h-5 text-brand-400' />
            )}
          </div>

          <div>
            <span className='font-bold text-slate-200 block text-xs'>
              {uploading ? 'Analyzing Document with Multimodal AI...' : 'Click to upload or drag & drop'}
            </span>
            <span className='text-[11px] text-slate-400'>
              Supports PDF, Screenshots/Images (PNG, JPG, WEBP), and Plain Text
            </span>
          </div>

          <div className='flex items-center justify-center gap-3 pt-1 text-[10px] text-slate-400'>
            <span className='flex items-center gap-1'><FileText className='w-3 h-3 text-red-400' /> PDF (PyMuPDF)</span>
            <span className='flex items-center gap-1'><Image className='w-3 h-3 text-blue-400' /> Images (Vision AI)</span>
            <span className='flex items-center gap-1'><FileCode className='w-3 h-3 text-emerald-400' /> TXT/MD</span>
          </div>
        </div>
      )}

      {/* Uploaded File Badge */}
      {uploadedFileName && (
        <div className={`flex items-center justify-between p-2 rounded-xl border text-[11px] ${colorClasses}`}>
          <div className='flex items-center gap-2'>
            <CheckCircle2 className='w-3.5 h-3.5 flex-shrink-0' />
            <span className='font-semibold'>{uploadedFileName}</span>
            {extractedStats && (
              <span className='opacity-75'>
                ({extractedStats.type.toUpperCase()} • {extractedStats.words} words extracted)
              </span>
            )}
          </div>
          <button
            type='button'
            onClick={() => {
              setUploadedFileName(null);
              setExtractedStats(null);
            }}
            className='hover:text-white'
          >
            <X className='w-3.5 h-3.5' />
          </button>
        </div>
      )}

      {error && (
        <div className='p-2 rounded-xl bg-red-950/40 border border-red-800/50 text-[11px] text-red-300 flex items-center gap-2'>
          <AlertCircle className='w-3.5 h-3.5 text-red-400' />
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
            onChange={(e) => onChange(e.target.value)}
            rows={rows}
            placeholder={placeholder}
            className='w-full p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white font-mono leading-relaxed focus:border-brand-500 focus:outline-none resize-none'
            required={required}
          />
          <div className='absolute right-2.5 bottom-2.5 flex items-center gap-2'>
            <button
              type='button'
              onClick={() => {
                setActiveMode('upload');
                setTimeout(() => fileInputRef.current?.click(), 50);
              }}
              className='text-[10px] text-slate-400 hover:text-brand-300 bg-slate-900/90 border border-slate-800 hover:border-brand-500/50 px-2 py-0.5 rounded flex items-center gap-1 transition-all'
            >
              <Upload className='w-2.5 h-2.5' />
              Upload PDF
            </button>
            {value && (
              <span className='text-[10px] text-slate-400 font-mono bg-slate-900/90 px-1.5 py-0.5 rounded border border-slate-800/60'>
                {value.split(/\s+/).filter(Boolean).length} words
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
