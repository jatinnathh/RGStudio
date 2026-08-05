"use client";

import Link from "next/link";
import { FormEvent, useCallback, useMemo, useRef, useState } from "react";
import {
  api,
  resolveImageUrl,
  type RetrievalResponse,
  type GenerateResponse,
  type StyleTransferResponse,
} from "../lib/api";

// ── Types ────────────────────────────────────────────────────────────────────

type Mode = "text-to-art" | "style-transfer";

// ── Component ────────────────────────────────────────────────────────────────

export default function StudioHome() {
  // State
  const [mode, setMode] = useState<Mode>("text-to-art");
  const [query, setQuery] = useState("impressionist sunset over water, Monet style");
  const [topK, setTopK] = useState(5);
  const [styleWeight, setStyleWeight] = useState(0.8);
  const [outputSize, setOutputSize] = useState(512);
  const [useMultiStyle, setUseMultiStyle] = useState(false);

  // RAG state
  const [isRetrieving, setIsRetrieving] = useState(false);
  const [ragResponse, setRagResponse] = useState<RetrievalResponse | null>(null);

  // Generate state
  const [isGenerating, setIsGenerating] = useState(false);
  const [genResult, setGenResult] = useState<GenerateResponse | null>(null);

  // Style transfer state
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [uploadPreview, setUploadPreview] = useState<string | null>(null);
  const [styleTransferResult, setStyleTransferResult] = useState<StyleTransferResponse | null>(null);

  const [error, setError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const results = useMemo(() => ragResponse?.results ?? [], [ragResponse]);
  const topResult = results[0] ?? null;

  const stylePrompt = useMemo(
    () =>
      results
        .slice(0, 3)
        .map((a) => `${a.title} by ${a.artist}: ${a.caption}`)
        .join("\n"),
    [results]
  );

  // ── Handlers ──────────────────────────────────────────────────────────────

  const handleRetrieve = useCallback(
    async (e: FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      setIsRetrieving(true);
      setError("");
      setGenResult(null);
      setStyleTransferResult(null);

      try {
        const data = await api.retrieve(query, topK);
        setRagResponse(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not reach the retrieval service.");
      } finally {
        setIsRetrieving(false);
      }
    },
    [query, topK]
  );

  const handleGenerate = useCallback(async () => {
    setIsGenerating(true);
    setError("");

    try {
      const data = await api.generate({
        query,
        top_k: topK,
        style_weight: styleWeight,
        output_size: outputSize,
        use_multi_style: useMultiStyle,
      });
      setGenResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed.");
    } finally {
      setIsGenerating(false);
    }
  }, [query, topK, styleWeight, outputSize, useMultiStyle]);

  const handleStyleTransfer = useCallback(async () => {
    if (!uploadedFile) return;
    setIsGenerating(true);
    setError("");

    try {
      const data = await api.styleTransfer(uploadedFile, query, {
        topK,
        styleWeight,
        outputSize,
      });
      setStyleTransferResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Style transfer failed.");
    } finally {
      setIsGenerating(false);
    }
  }, [uploadedFile, query, topK, styleWeight, outputSize]);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setUploadedFile(file);
      const reader = new FileReader();
      reader.onload = () => setUploadPreview(reader.result as string);
      reader.readAsDataURL(file);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const file = e.dataTransfer.files?.[0];
    if (file && file.type.startsWith("image/")) {
      setUploadedFile(file);
      const reader = new FileReader();
      reader.onload = () => setUploadPreview(reader.result as string);
      reader.readAsDataURL(file);
    }
  }, []);

  const outputImage =
    genResult?.image_base64 || styleTransferResult?.image_base64 || null;
  const outputRef =
    genResult?.style_reference || styleTransferResult?.style_reference || null;
  const outputScore =
    genResult?.clip_score ?? styleTransferResult?.clip_score ?? null;
  const outputTime =
    genResult?.generation_time_ms ?? styleTransferResult?.generation_time_ms ?? null;
  const outputMessage =
    genResult?.message || styleTransferResult?.message || null;

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <main className="studio-root">
      <style>{STUDIO_CSS}</style>

      {/* ── NAV ─────────────────────────────────────────────────── */}
      <nav className="s-nav">
        <Link href="/" className="s-brand">
          <span className="s-mark">RG</span>
          <span>RGStudio</span>
        </Link>
        <div className="s-nav-links">
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="s-nav-link"
          >
            API Docs
          </a>
        </div>
      </nav>

      {/* ── 3-Column Layout ──────────────────────────────────────── */}
      <div className="s-workspace">
        {/* ═══ LEFT SIDEBAR ═══ */}
        <aside className="s-sidebar">
          {/* Mode selector */}
          <div className="s-panel">
            <h3 className="s-panel-label">Mode</h3>
            <div className="s-mode-tabs">
              <button
                className={`s-mode-tab ${mode === "text-to-art" ? "active" : ""}`}
                onClick={() => setMode("text-to-art")}
              >
                Text to Art
              </button>
              <button
                className={`s-mode-tab ${mode === "style-transfer" ? "active" : ""}`}
                onClick={() => setMode("style-transfer")}
              >
                Style Transfer
              </button>
            </div>
          </div>

          {/* Prompt */}
          <form onSubmit={handleRetrieve} className="s-panel">
            <h3 className="s-panel-label">Style Prompt</h3>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              rows={4}
              className="s-textarea"
              placeholder="Describe the art style you want..."
            />

            {/* Style Transfer Upload */}
            {mode === "style-transfer" && (
              <div
                className="s-dropzone"
                onDrop={handleDrop}
                onDragOver={(e) => e.preventDefault()}
                onClick={() => fileInputRef.current?.click()}
              >
                {uploadPreview ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={uploadPreview} alt="Upload preview" className="s-drop-preview" />
                ) : (
                  <div className="s-drop-placeholder">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12" />
                    </svg>
                    <span>Drop image or click to upload</span>
                  </div>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleFileChange}
                  className="s-file-input"
                />
              </div>
            )}

            <button
              type="submit"
              disabled={isRetrieving}
              className="s-btn s-btn-secondary"
            >
              {isRetrieving ? "Retrieving..." : "Retrieve References"}
            </button>
          </form>

          {/* Settings */}
          <div className="s-panel">
            <h3 className="s-panel-label">Settings</h3>

            <label className="s-slider-label">
              <span>Top K: {topK}</span>
              <input
                type="range"
                min={1}
                max={20}
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="s-slider"
              />
            </label>

            <label className="s-slider-label">
              <span>Style Weight: {styleWeight.toFixed(2)}</span>
              <input
                type="range"
                min={0}
                max={100}
                value={styleWeight * 100}
                onChange={(e) => setStyleWeight(Number(e.target.value) / 100)}
                className="s-slider"
              />
            </label>

            <label className="s-slider-label">
              <span>Output Size: {outputSize}px</span>
              <input
                type="range"
                min={256}
                max={1024}
                step={128}
                value={outputSize}
                onChange={(e) => setOutputSize(Number(e.target.value))}
                className="s-slider"
              />
            </label>

            {mode === "text-to-art" && (
              <label className="s-checkbox-label">
                <input
                  type="checkbox"
                  checked={useMultiStyle}
                  onChange={(e) => setUseMultiStyle(e.target.checked)}
                />
                <span>Multi-style blending</span>
              </label>
            )}
          </div>

          {/* Generate Button */}
          <button
            onClick={mode === "text-to-art" ? handleGenerate : handleStyleTransfer}
            disabled={isGenerating || (mode === "style-transfer" && !uploadedFile)}
            className="s-btn s-btn-primary s-btn-generate"
          >
            {isGenerating ? (
              <span className="s-btn-loading">
                <span className="s-spinner" />
                Generating...
              </span>
            ) : mode === "text-to-art" ? (
              "Generate Art"
            ) : (
              "Apply Style Transfer"
            )}
          </button>

          {error && <p className="s-error">{error}</p>}
        </aside>

        {/* ═══ CENTER CANVAS ═══ */}
        <section className="s-canvas">
          {outputImage ? (
            <div className="s-output-wrap">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`data:image/jpeg;base64,${outputImage}`}
                alt="Generated artwork"
                className="s-output-img"
              />
              <div className="s-output-meta">
                {outputScore !== null && (
                  <span className="s-clip-badge">CLIP {outputScore.toFixed(4)}</span>
                )}
                {outputTime !== null && (
                  <span className="s-time-badge">{(outputTime / 1000).toFixed(1)}s</span>
                )}
              </div>
              {outputMessage && <p className="s-output-msg">{outputMessage}</p>}
              {outputRef && (
                <div className="s-output-ref">
                  <span className="s-ref-label">Style reference:</span>
                  <span>
                    {outputRef.title} by {outputRef.artist} ({outputRef.style})
                  </span>
                </div>
              )}
            </div>
          ) : isGenerating ? (
            <div className="s-canvas-loading">
              <div className="s-pulse-ring" />
              <p>Generating artwork...</p>
              <p className="s-canvas-sub">
                RAG retrieval + CLIP ranking + AdaIN style transfer
              </p>
            </div>
          ) : (
            <div className="s-canvas-empty">
              <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.3">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                <circle cx="8.5" cy="8.5" r="1.5" />
                <path d="M21 15l-5-5L5 21" />
              </svg>
              <h2 className="s-canvas-title">Your Generated Art</h2>
              <p className="s-canvas-sub">
                Enter a style prompt and click Generate to create artwork using the RAG + GAN pipeline
              </p>
            </div>
          )}
        </section>

        {/* ═══ RIGHT PANEL ═══ */}
        <aside className="s-right">
          <div className="s-panel">
            <div className="s-panel-header">
              <h3 className="s-panel-label">RAG References</h3>
              {ragResponse && (
                <span className="s-count">{ragResponse.total_found} found</span>
              )}
            </div>

            {results.length > 0 ? (
              <div className="s-ref-grid">
                {results.map((artwork) => (
                  <div key={artwork.artwork_id} className="s-ref-card">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={resolveImageUrl(artwork.image_url)}
                      alt={artwork.title}
                      className="s-ref-img"
                    />
                    <div className="s-ref-body">
                      <div className="s-ref-topline">
                        <span className="s-score">
                          {artwork.score.toFixed(4)}
                        </span>
                        <span className="s-style-pill">{artwork.style}</span>
                      </div>
                      <h4 className="s-ref-title">{artwork.title}</h4>
                      <p className="s-ref-artist">
                        {artwork.artist}
                        {artwork.year ? `, ${artwork.year}` : ""}
                      </p>
                      <p className="s-ref-caption">{artwork.caption}</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="s-empty-text">
                Click &quot;Retrieve References&quot; to find matching artworks
              </p>
            )}
          </div>

          {/* Context Panel */}
          {topResult && (
            <div className="s-panel s-context">
              <h3 className="s-panel-label">Generation Context</h3>
              <h4 className="s-context-title">Best: {topResult.title}</h4>
              <p className="s-context-text">
                This ranked context feeds into /generate for CLIP-guided AdaIN
                style transfer.
              </p>
              <pre className="s-prompt-box">{stylePrompt}</pre>
            </div>
          )}
        </aside>
      </div>
    </main>
  );
}

// ── CSS ──────────────────────────────────────────────────────────────────────

const STUDIO_CSS = `
  /* === Root & Tokens === */
  .studio-root {
    min-height: 100vh;
    background: #0c0a09;
    color: #f0ebe3;
    font-family: var(--font-dm-sans), system-ui, sans-serif;
  }

  /* === Nav === */
  .s-nav {
    max-width: 1440px;
    margin: 0 auto;
    padding: 16px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid rgba(255,255,255,0.06);
  }
  .s-brand {
    display: flex;
    align-items: center;
    gap: 10px;
    font-weight: 700;
    font-size: 15px;
    color: #f0ebe3;
    text-decoration: none;
  }
  .s-mark {
    display: grid;
    place-items: center;
    width: 32px;
    height: 32px;
    border-radius: 8px;
    background: linear-gradient(135deg, #f59e0b, #ef4444);
    font-family: var(--font-playfair), serif;
    font-size: 13px;
    font-weight: 700;
    color: white;
  }
  .s-nav-links { display: flex; gap: 12px; }
  .s-nav-link {
    padding: 8px 14px;
    border-radius: 6px;
    border: 1px solid rgba(255,255,255,0.12);
    color: #f0ebe3;
    text-decoration: none;
    font-size: 13px;
    transition: background 0.2s;
  }
  .s-nav-link:hover { background: rgba(255,255,255,0.06); }

  /* === 3-Column Workspace === */
  .s-workspace {
    max-width: 1440px;
    margin: 0 auto;
    padding: 20px 24px;
    display: grid;
    grid-template-columns: 280px 1fr 340px;
    gap: 20px;
    min-height: calc(100vh - 68px);
  }

  /* === Panels (shared) === */
  .s-panel {
    background: #161412;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 18px;
    margin-bottom: 14px;
  }
  .s-panel-label {
    margin: 0 0 12px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: rgba(240,235,227,0.5);
    font-weight: 700;
  }
  .s-panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }
  .s-panel-header .s-panel-label { margin-bottom: 0; }
  .s-count {
    font-size: 12px;
    color: rgba(240,235,227,0.4);
  }

  /* === Mode Tabs === */
  .s-mode-tabs {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
    background: #0c0a09;
    border-radius: 8px;
    padding: 3px;
  }
  .s-mode-tab {
    padding: 8px 0;
    border: none;
    border-radius: 6px;
    background: transparent;
    color: rgba(240,235,227,0.5);
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }
  .s-mode-tab.active {
    background: rgba(245,158,11,0.15);
    color: #f59e0b;
  }

  /* === Textarea === */
  .s-textarea {
    width: 100%;
    min-height: 100px;
    padding: 12px;
    border-radius: 8px;
    border: 1px solid rgba(255,255,255,0.1);
    background: #0c0a09;
    color: #f0ebe3;
    font: inherit;
    font-size: 13px;
    line-height: 1.6;
    resize: vertical;
    margin-bottom: 10px;
  }
  .s-textarea:focus {
    outline: none;
    border-color: rgba(245,158,11,0.4);
  }

  /* === Dropzone === */
  .s-dropzone {
    margin-bottom: 10px;
    padding: 16px;
    border: 2px dashed rgba(255,255,255,0.12);
    border-radius: 8px;
    cursor: pointer;
    text-align: center;
    transition: border-color 0.2s;
  }
  .s-dropzone:hover { border-color: rgba(245,158,11,0.4); }
  .s-drop-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    color: rgba(240,235,227,0.3);
    font-size: 12px;
  }
  .s-drop-preview {
    width: 100%;
    max-height: 180px;
    object-fit: contain;
    border-radius: 6px;
  }
  .s-file-input { display: none; }

  /* === Buttons === */
  .s-btn {
    width: 100%;
    padding: 10px 16px;
    border: none;
    border-radius: 8px;
    font: inherit;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.2s;
  }
  .s-btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .s-btn-secondary {
    background: rgba(255,255,255,0.06);
    color: #f0ebe3;
    border: 1px solid rgba(255,255,255,0.1);
  }
  .s-btn-secondary:hover:not(:disabled) {
    background: rgba(255,255,255,0.1);
  }
  .s-btn-primary {
    background: linear-gradient(135deg, #f59e0b, #ef4444);
    color: white;
  }
  .s-btn-primary:hover:not(:disabled) {
    filter: brightness(1.1);
    transform: translateY(-1px);
    box-shadow: 0 4px 20px rgba(245,158,11,0.3);
  }
  .s-btn-generate { margin-top: 6px; }
  .s-btn-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
  }
  .s-spinner {
    width: 14px;
    height: 14px;
    border: 2px solid rgba(255,255,255,0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* === Sliders === */
  .s-slider-label {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-bottom: 12px;
    font-size: 12px;
    color: rgba(240,235,227,0.65);
  }
  .s-slider {
    width: 100%;
    height: 4px;
    appearance: none;
    background: rgba(255,255,255,0.1);
    border-radius: 4px;
    cursor: pointer;
  }
  .s-slider::-webkit-slider-thumb {
    appearance: none;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: #f59e0b;
    cursor: pointer;
  }

  /* === Checkbox === */
  .s-checkbox-label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: rgba(240,235,227,0.65);
    cursor: pointer;
  }

  /* === Error === */
  .s-error {
    margin: 10px 0 0;
    padding: 10px;
    border-radius: 6px;
    background: rgba(239,68,68,0.1);
    border: 1px solid rgba(239,68,68,0.2);
    color: #fca5a5;
    font-size: 12px;
    line-height: 1.5;
  }

  /* === Center Canvas === */
  .s-canvas {
    display: flex;
    align-items: center;
    justify-content: center;
    background: #161412;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px;
    min-height: 500px;
    overflow: hidden;
  }
  .s-canvas-empty, .s-canvas-loading {
    text-align: center;
    padding: 40px;
  }
  .s-canvas-title {
    margin: 20px 0 8px;
    font-family: var(--font-playfair), serif;
    font-size: 22px;
    font-weight: 700;
    color: rgba(240,235,227,0.6);
  }
  .s-canvas-sub {
    color: rgba(240,235,227,0.3);
    font-size: 13px;
    line-height: 1.6;
    max-width: 320px;
    margin: 0 auto;
  }

  /* Loading pulse */
  .s-pulse-ring {
    width: 64px;
    height: 64px;
    margin: 0 auto 24px;
    border-radius: 50%;
    border: 3px solid rgba(245,158,11,0.2);
    border-top-color: #f59e0b;
    animation: spin 1s ease-in-out infinite;
  }
  .s-canvas-loading p {
    color: rgba(240,235,227,0.6);
    font-size: 15px;
    margin: 0 0 6px;
  }

  /* Output image */
  .s-output-wrap {
    width: 100%;
    padding: 20px;
  }
  .s-output-img {
    width: 100%;
    border-radius: 8px;
    display: block;
  }
  .s-output-meta {
    display: flex;
    gap: 8px;
    margin-top: 12px;
  }
  .s-clip-badge, .s-time-badge {
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 700;
    font-family: ui-monospace, monospace;
  }
  .s-clip-badge {
    background: rgba(245,158,11,0.15);
    color: #f59e0b;
  }
  .s-time-badge {
    background: rgba(255,255,255,0.06);
    color: rgba(240,235,227,0.5);
  }
  .s-output-msg {
    margin: 12px 0 0;
    font-size: 13px;
    color: rgba(240,235,227,0.65);
    line-height: 1.6;
  }
  .s-output-ref {
    margin-top: 8px;
    font-size: 12px;
    color: rgba(240,235,227,0.4);
  }
  .s-ref-label { margin-right: 6px; }

  /* === Right Panel - References === */
  .s-right { overflow-y: auto; max-height: calc(100vh - 88px); }
  .s-ref-grid { display: flex; flex-direction: column; gap: 10px; }
  .s-ref-card {
    border-radius: 8px;
    border: 1px solid rgba(255,255,255,0.06);
    background: #0c0a09;
    overflow: hidden;
    transition: border-color 0.2s;
  }
  .s-ref-card:hover {
    border-color: rgba(245,158,11,0.3);
  }
  .s-ref-img {
    width: 100%;
    aspect-ratio: 16 / 9;
    object-fit: cover;
    display: block;
  }
  .s-ref-body { padding: 12px; }
  .s-ref-topline {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
  }
  .s-score {
    font-family: ui-monospace, monospace;
    font-size: 11px;
    color: #f59e0b;
  }
  .s-style-pill {
    padding: 2px 8px;
    border-radius: 999px;
    border: 1px solid rgba(255,255,255,0.1);
    font-size: 10px;
    color: rgba(240,235,227,0.6);
  }
  .s-ref-title {
    margin: 0;
    font-family: var(--font-playfair), serif;
    font-size: 15px;
    font-weight: 700;
    line-height: 1.2;
  }
  .s-ref-artist {
    margin: 4px 0 0;
    font-size: 11px;
    color: rgba(240,235,227,0.4);
  }
  .s-ref-caption {
    margin: 8px 0 0;
    font-size: 11px;
    line-height: 1.5;
    color: rgba(240,235,227,0.5);
  }
  .s-empty-text {
    font-size: 12px;
    color: rgba(240,235,227,0.3);
    text-align: center;
    padding: 20px 0;
  }

  /* === Context Panel === */
  .s-context { position: sticky; top: 20px; }
  .s-context-title {
    margin: 0 0 8px;
    font-family: var(--font-playfair), serif;
    font-size: 18px;
    line-height: 1.2;
  }
  .s-context-text {
    margin: 0 0 12px;
    font-size: 12px;
    color: rgba(240,235,227,0.5);
    line-height: 1.6;
  }
  .s-prompt-box {
    padding: 12px;
    border-radius: 6px;
    background: #0c0a09;
    border: 1px solid rgba(255,255,255,0.06);
    color: rgba(240,235,227,0.6);
    font-size: 11px;
    line-height: 1.6;
    white-space: pre-wrap;
    overflow: auto;
    max-height: 200px;
    margin: 0;
  }

  /* === Responsive === */
  @media (max-width: 1200px) {
    .s-workspace {
      grid-template-columns: 260px 1fr;
    }
    .s-right { display: none; }
  }
  @media (max-width: 768px) {
    .s-workspace {
      grid-template-columns: 1fr;
    }
    .s-sidebar { order: 2; }
    .s-canvas { order: 1; min-height: 300px; }
  }
`;
