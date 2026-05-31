"use client";

import { useEffect, useRef, useCallback } from "react";

function MonogramLogo({ size = 32 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M32 4C32 4 12 18 12 36C12 48 20 56 32 56C28 56 20 50 20 38C20 22 32 4 32 4Z" fill="white" opacity="0.9" />
      <path d="M32 60C32 60 52 46 52 28C52 16 44 8 32 8C36 8 44 14 44 26C44 42 32 60 32 60Z" fill="white" opacity="0.7" />
    </svg>
  );
}

function paintPixelSwatch(
  swatchCanvas: HTMLCanvasElement,
  sourceImg: HTMLImageElement,
  gridCells: number = 3
) {
  const ctx = swatchCanvas.getContext("2d");
  if (!ctx) return;

  const sourceRect = sourceImg.getBoundingClientRect();
  const swatchRect = swatchCanvas.getBoundingClientRect();

  const scaleX = sourceImg.naturalWidth / sourceRect.width;
  const scaleY = sourceImg.naturalHeight / sourceRect.height;

  const srcX = (swatchRect.left - sourceRect.left) * scaleX;
  const srcY = (swatchRect.top - sourceRect.top) * scaleY;
  const srcW = swatchRect.width * scaleX;
  const srcH = swatchRect.height * scaleY;

  if (srcX + srcW < 0 || srcY + srcH < 0 || srcX > sourceImg.naturalWidth || srcY > sourceImg.naturalHeight) return;

  const size = gridCells;
  ctx.imageSmoothingEnabled = true;
  ctx.drawImage(sourceImg, srcX, srcY, srcW, srcH, 0, 0, size, size);

  let imageData: ImageData;
  try {
    imageData = ctx.getImageData(0, 0, size, size);
  } catch {
    ctx.fillStyle = "rgba(100,100,100,0.6)";
    ctx.fillRect(0, 0, swatchCanvas.width, swatchCanvas.height);
    return;
  }

  ctx.clearRect(0, 0, swatchCanvas.width, swatchCanvas.height);
  const cellW = swatchCanvas.width / size;
  const cellH = swatchCanvas.height / size;

  for (let row = 0; row < size; row++) {
    for (let col = 0; col < size; col++) {
      const i = (row * size + col) * 4;
      ctx.fillStyle = `rgb(${imageData.data[i]},${imageData.data[i + 1]},${imageData.data[i + 2]})`;
      ctx.fillRect(Math.floor(col * cellW), Math.floor(row * cellH), Math.ceil(cellW), Math.ceil(cellH));
    }
  }

  ctx.strokeStyle = "rgba(0,0,0,0.2)";
  ctx.lineWidth = 0.5;
  for (let i = 0; i <= size; i++) {
    ctx.beginPath(); ctx.moveTo(i * cellW, 0); ctx.lineTo(i * cellW, swatchCanvas.height); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, i * cellH); ctx.lineTo(swatchCanvas.width, i * cellH); ctx.stroke();
  }
}

function DetectionBox({
  value,
  style,
  animDelay = "0s",
  size = "sm",
  displayImgRef,
}: {
  value: string;
  style: React.CSSProperties;
  animDelay?: string;
  size?: "sm" | "md" | "lg";
  displayImgRef: React.RefObject<HTMLImageElement | null>;
}) {
  const swatchRef = useRef<HTMLCanvasElement>(null);
  const swatchPx = size === "lg" ? 48 : 40;
  const fontSize = size === "lg" ? "13px" : size === "md" ? "12px" : "11px";
  const cornerSize = size === "lg" ? 12 : 10;
  const borderColor = "rgba(255,255,255,0.85)";

  useEffect(() => {
    const repaint = () => {
      const swatch = swatchRef.current;
      const img = displayImgRef.current;
      if (!swatch || !img || !img.complete || img.naturalWidth === 0) return;
      paintPixelSwatch(swatch, img, 3);
    };

    repaint();
    window.addEventListener("hero-frame-update", repaint);
    window.addEventListener("scroll", repaint, { passive: true });
    window.addEventListener("resize", repaint);
    return () => {
      window.removeEventListener("hero-frame-update", repaint);
      window.removeEventListener("scroll", repaint);
      window.removeEventListener("resize", repaint);
    };
  }, [displayImgRef]);

  const corners = [
    { top: 0, left: 0, bt: true, bl: true },
    { top: 0, right: 0, bt: true, br: true },
    { bottom: 0, left: 0, bb: true, bl: true },
    { bottom: 0, right: 0, bb: true, br: true },
  ];

  return (
    <div
      className="float-card"
      style={{
        position: "absolute",
        zIndex: 10,
        animationDelay: animDelay,
        filter: "drop-shadow(0 4px 12px rgba(0,0,0,0.5))",
        ...style,
      }}
    >
      <div style={{ position: "relative", display: "flex", alignItems: "center", padding: 3 }}>
        {corners.map((cs, i) => (
          <span
            key={i}
            style={{
              position: "absolute",
              width: cornerSize,
              height: cornerSize,
              top: cs.top,
              left: cs.left,
              right: (cs as { right?: number }).right,
              bottom: (cs as { bottom?: number }).bottom,
              borderTop: cs.bt ? `2px solid ${borderColor}` : undefined,
              borderLeft: cs.bl ? `2px solid ${borderColor}` : undefined,
              borderRight: (cs as { br?: boolean }).br ? `2px solid ${borderColor}` : undefined,
              borderBottom: (cs as { bb?: boolean }).bb ? `2px solid ${borderColor}` : undefined,
              borderTopLeftRadius: cs.bt && cs.bl ? 3 : 0,
              borderTopRightRadius: cs.bt && (cs as { br?: boolean }).br ? 3 : 0,
              borderBottomLeftRadius: (cs as { bb?: boolean }).bb && cs.bl ? 3 : 0,
              borderBottomRightRadius: (cs as { bb?: boolean }).bb && (cs as { br?: boolean }).br ? 3 : 0,
              zIndex: 2,
            }}
          />
        ))}
        <canvas
          ref={swatchRef}
          width={swatchPx}
          height={swatchPx}
          style={{
            width: swatchPx,
            height: swatchPx,
            borderRadius: 2,
            flexShrink: 0,
            imageRendering: "pixelated",
            filter: "blur(1.5px)",
            boxShadow: "inset 0 0 0 10px rgba(0,0,0,0.3), 0 0 0 1px rgba(255,255,255,0.12)",
          }}
        />
        <span
          style={{
            fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
            fontSize,
            color: "rgba(255,255,255,0.95)",
            fontWeight: 500,
            letterSpacing: "0.04em",
            textShadow: "0 1px 3px rgba(0,0,0,0.6)",
            padding: "2px 6px",
            marginLeft: 2,
            background: "rgba(0,0,0,0.30)",
            backdropFilter: "blur(8px)",
            WebkitBackdropFilter: "blur(8px)",
            borderRadius: "0 3px 3px 0",
          }}
        >
          {value}
        </span>
      </div>
    </div>
  );
}

const TOTAL_FRAMES = 120;
const MAX_TIME = 8;

function ScrollVideoHero() {
  const containerRef = useRef<HTMLDivElement>(null);
  const hiddenVideoRef = useRef<HTMLVideoElement>(null);
  const displayImgRef = useRef<HTMLImageElement>(null);
  const framesRef = useRef<string[]>([]); // blob URLs
  const isExtractedRef = useRef(false);
  const loadingRef = useRef<HTMLDivElement>(null);
  const loadProgressRef = useRef<HTMLDivElement>(null);
  const loadTextRef = useRef<HTMLSpanElement>(null);

  const navRef = useRef<HTMLElement>(null);
  const bodyTextRef = useRef<HTMLDivElement>(null);
  const h1Ref = useRef<HTMLHeadingElement>(null);
  const scrollHintRef = useRef<HTMLDivElement>(null);
  const progressBarRef = useRef<HTMLDivElement>(null);
  const scanLineRef = useRef<HTMLDivElement>(null);

  // ── Frame extraction on mount ──
  useEffect(() => {
    const video = hiddenVideoRef.current;
    if (!video || isExtractedRef.current) return;
    isExtractedRef.current = true;

    const offscreen = document.createElement("canvas");
    const ctx = offscreen.getContext("2d")!;

    const extract = async () => {
      offscreen.width = video.videoWidth || 1920;
      offscreen.height = video.videoHeight || 1080;

      const frames: string[] = [];

      for (let i = 0; i < TOTAL_FRAMES; i++) {
        video.currentTime = (i / (TOTAL_FRAMES - 1)) * MAX_TIME;

        await new Promise<void>((res) => {
          video.addEventListener("seeked", () => res(), { once: true });
        });

        ctx.drawImage(video, 0, 0, offscreen.width, offscreen.height);

        const blobUrl = await new Promise<string>((res) => {
          offscreen.toBlob((blob) => {
            res(URL.createObjectURL(blob!));
          }, "image/jpeg", 0.82);
        });

        frames.push(blobUrl);

        // Update loading UI
        const pct = Math.round(((i + 1) / TOTAL_FRAMES) * 100);
        if (loadProgressRef.current) loadProgressRef.current.style.width = `${pct}%`;
        if (loadTextRef.current) loadTextRef.current.textContent = `${pct}%`;
      }

      framesRef.current = frames;

      // Set first frame and hide loader
      if (displayImgRef.current && frames[0]) {
        displayImgRef.current.src = frames[0];
      }
      if (loadingRef.current) {
        loadingRef.current.style.transition = "opacity 0.6s ease";
        loadingRef.current.style.opacity = "0";
        setTimeout(() => {
          if (loadingRef.current) loadingRef.current.style.display = "none";
        }, 650);
      }

      window.dispatchEvent(new Event("hero-frame-update"));
    };

    if (video.readyState >= 1) {
      extract();
    } else {
      video.addEventListener("loadedmetadata", extract, { once: true });
    }
  }, []);

  // ── Scroll handler — pure img.src swap, zero decode lag ──
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let rafId = 0;

    const handleScroll = () => {
      cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(() => {
        const rect = container.getBoundingClientRect();
        const scrollH = container.offsetHeight - window.innerHeight;
        if (scrollH <= 0) return;

        const progress = Math.max(0, Math.min(1, -rect.top / scrollH));

        // Frame swap — instant, no decode
        const frameIndex = Math.min(
          Math.round(progress * (TOTAL_FRAMES - 1)),
          framesRef.current.length - 1
        );
        const img = displayImgRef.current;
        if (img && framesRef.current[frameIndex] && img.src !== framesRef.current[frameIndex]) {
          img.src = framesRef.current[frameIndex];
          window.dispatchEvent(new Event("hero-frame-update"));
        }

        // DOM overlays
        const overlayOpacity = Math.max(0, 1 - progress * 3);
        const textOpacity = Math.max(0, 1 - progress * 2.5);
        const h1Trans = progress * 60;

        if (navRef.current) navRef.current.style.opacity = String(overlayOpacity);
        if (bodyTextRef.current) {
          bodyTextRef.current.style.opacity = String(textOpacity);
          bodyTextRef.current.style.transform = `translateY(${h1Trans * 0.3}px)`;
        }
        if (h1Ref.current) {
          h1Ref.current.style.opacity = String(textOpacity);
          h1Ref.current.style.transform = `translateY(-${h1Trans}px)`;
        }
        if (scrollHintRef.current) scrollHintRef.current.style.opacity = String(overlayOpacity);
        if (progressBarRef.current) progressBarRef.current.style.width = `${progress * 100}%`;
        if (scanLineRef.current) scanLineRef.current.style.top = `${progress * 100}%`;
      });
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();

    return () => {
      cancelAnimationFrame(rafId);
      window.removeEventListener("scroll", handleScroll);
    };
  }, []);

  return (
    <div
      ref={containerRef}
      style={{ position: "relative", height: "300vh", background: "#0a0806" }}
    >
      {/* Hidden video — only used for frame extraction, never displayed */}
      <video
        ref={hiddenVideoRef}
        src="/hero_video3.mp4"
        muted
        playsInline
        preload="auto"
        style={{ position: "absolute", opacity: 0, pointerEvents: "none", width: 1, height: 1 }}
      />

      <div style={{ position: "sticky", top: 0, width: "100%", height: "100vh", overflow: "hidden" }}>

        {/* Loading overlay */}
        <div
          ref={loadingRef}
          style={{
            position: "absolute",
            inset: 0,
            zIndex: 50,
            background: "#0a0806",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: "1.5rem",
          }}
        >
          <MonogramLogo size={44} />
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "0.6rem" }}>
            <div style={{ width: "180px", height: "1px", background: "rgba(255,255,255,0.12)", borderRadius: 1 }}>
              <div
                ref={loadProgressRef}
                style={{
                  height: "100%",
                  width: "0%",
                  background: "rgba(255,255,255,0.6)",
                  borderRadius: 1,
                  transition: "width 0.1s linear",
                }}
              />
            </div>
            <span
              ref={loadTextRef}
              style={{ fontSize: "10px", letterSpacing: "0.2em", color: "rgba(255,255,255,0.4)", fontFamily: "ui-monospace, monospace" }}
            >
              0%
            </span>
          </div>
        </div>

        {/* Display image — frame is swapped on scroll */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          ref={displayImgRef}
          alt=""
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            objectFit: "cover",
            zIndex: 0,
            opacity: 0.95,
            filter: "brightness(0.92) contrast(1.08) saturate(1.05)",
          }}
        />

        {/* Vignette */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            zIndex: 1,
            background: `
              radial-gradient(circle at 50% 40%, transparent 35%, rgba(0,0,0,0.45) 100%),
              linear-gradient(to top, rgba(0,0,0,0.55) 0%, transparent 40%)
            `,
            pointerEvents: "none",
          }}
        />

        {/* Progress bar */}
        <div
          ref={progressBarRef}
          style={{
            position: "absolute", bottom: 0, left: 0,
            height: "2px", width: "0%",
            background: "linear-gradient(90deg, rgba(255,255,255,0.0), rgba(255,255,255,0.6), rgba(255,255,255,0.0))",
            zIndex: 25, willChange: "width",
          }}
        />

        {/* Scan line */}
        <div
          ref={scanLineRef}
          style={{
            position: "absolute", left: 0, right: 0,
            height: "1px", top: "0%",
            background: "linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.25) 30%, rgba(255,255,255,0.4) 50%, rgba(255,255,255,0.25) 70%, transparent 100%)",
            zIndex: 15,
            boxShadow: "0 0 15px 2px rgba(255,255,255,0.08)",
            pointerEvents: "none", willChange: "top",
          }}
        />

        {/* Nav */}
        <nav
          ref={navRef}
          style={{
            position: "absolute", top: 0, left: 0, right: 0,
            zIndex: 20, display: "flex", justifyContent: "space-between",
            alignItems: "center", padding: "1.5rem 2.5rem",
            maxWidth: "80rem", margin: "0 auto", willChange: "opacity",
          }}
        >
          <div style={{ display: "flex", alignItems: "center" }}>
            <MonogramLogo size={34} />
            <p style={{
              fontSize: "11px", color: "rgba(255,255,255,0.7)",
              lineHeight: 1.5, maxWidth: "140px", marginLeft: "0.9rem",
              fontWeight: 300, letterSpacing: "0.02em",
            }}>
              Complete Business Automation. We Handle All Tasks. You Relax.
            </p>
          </div>
          <button
            style={{
              padding: "0.6rem 1.75rem", fontSize: "0.75rem",
              textTransform: "uppercase", letterSpacing: "0.18em",
              color: "rgba(255,255,255,0.9)", borderRadius: "9999px",
              cursor: "pointer", fontWeight: 400,
              background: "rgba(255,255,255,0.06)",
              border: "1px solid rgba(255,255,255,0.35)",
              transition: "all 0.3s ease", backdropFilter: "blur(4px)",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = "rgba(255,255,255,0.14)";
              e.currentTarget.style.borderColor = "rgba(255,255,255,0.65)";
              e.currentTarget.style.transform = "translateY(-1px)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "rgba(255,255,255,0.06)";
              e.currentTarget.style.borderColor = "rgba(255,255,255,0.35)";
              e.currentTarget.style.transform = "translateY(0)";
            }}
          >
            Get Started
          </button>
        </nav>

        {/* Detection boxes */}
        <DetectionBox value="0.1429" size="sm" animDelay="0s" style={{ top: "8%", left: "48%", zIndex: 10, opacity: 0.5 }} displayImgRef={displayImgRef} />
        <DetectionBox value="0.2857" size="sm" animDelay="0.6s" style={{ top: "16%", left: "16%", zIndex: 10 }} displayImgRef={displayImgRef} />
        <DetectionBox value="0.7443" size="md" animDelay="1.2s" style={{ top: "20%", left: "42%", zIndex: 10 }} displayImgRef={displayImgRef} />
        <DetectionBox value="1.0000" size="md" animDelay="1.8s" style={{ top: "18%", left: "32%", zIndex: 10 }} displayImgRef={displayImgRef} />
        <DetectionBox value="1.1429" size="sm" animDelay="2.4s" style={{ top: "28%", right: "30%", zIndex: 10 }} displayImgRef={displayImgRef} />
        <DetectionBox value="1.5714" size="sm" animDelay="1.5s" style={{ top: "36%", right: "18%", zIndex: 10 }} displayImgRef={displayImgRef} />
        <DetectionBox value="1.8671" size="sm" animDelay="2.0s" style={{ top: "52%", left: "34%", zIndex: 10 }} displayImgRef={displayImgRef} />
        <DetectionBox value="2.2857" size="sm" animDelay="3s" style={{ bottom: "32%", left: "38%", zIndex: 10 }} displayImgRef={displayImgRef} />

        {/* Body text */}
        <div
          ref={bodyTextRef}
          className="animate-fade-rise-d1"
          style={{
            position: "absolute", bottom: "20%", left: "2.5rem",
            maxWidth: "240px", zIndex: 10, willChange: "opacity, transform",
          }}
        >
          <p style={{ fontSize: "11px", color: "rgba(255,255,255,0.82)", lineHeight: 1.75, fontWeight: 300, marginBottom: "1rem", textShadow: "0 1px 10px rgba(0,0,0,0.5)" }}>
            Our SaaS product takes over all exhausting operational activities,
            complex analytics, and tedious process management. While algorithms
            seamlessly build your success infrastructure and generate stable
            profit, you get time for truly important things.
          </p>
          <p style={{ fontSize: "11px", color: "rgba(255,255,255,0.82)", lineHeight: 1.75, fontWeight: 300, textShadow: "0 1px 10px rgba(0,0,0,0.5)" }}>
            Delegate micromanagement to artificial intelligence and reliable
            cloud solutions to enjoy absolute peace of mind.
          </p>
        </div>

        {/* H1 */}
        <h1
          ref={h1Ref}
          className="animate-fade-rise"
          style={{
            position: "absolute", bottom: "6%", right: "2.5rem",
            textAlign: "right", maxWidth: "55%",
            fontSize: "clamp(2.6rem, 5.2vw, 4.8rem)",
            lineHeight: 0.98, letterSpacing: "-1.2px",
            fontWeight: 400, color: "white", fontStyle: "italic",
            zIndex: 10, textShadow: "0 4px 30px rgba(0,0,0,0.55)",
            willChange: "opacity, transform",
          }}
        >
          Intelligent Daily<br />
          Routine Automation<br />
          For Your Business.<br />
          You Relax
        </h1>

        {/* Scroll hint */}
        <div
          ref={scrollHintRef}
          style={{
            position: "absolute", bottom: "1.5rem", left: "50%",
            transform: "translateX(-50%)", zIndex: 20,
            display: "flex", flexDirection: "column",
            alignItems: "center", gap: "0.4rem",
            willChange: "opacity", pointerEvents: "none",
          }}
        >
          <span style={{ fontSize: "9px", letterSpacing: "0.25em", textTransform: "uppercase", color: "rgba(255,255,255,0.5)", fontWeight: 400 }}>
            Scroll to explore
          </span>
          <div style={{ width: "1px", height: "28px", background: "linear-gradient(to bottom, rgba(255,255,255,0.5), transparent)", animation: "scrollPulse 2s ease-in-out infinite" }} />
        </div>

      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   SECTION 2 — unchanged from your original
   ═══════════════════════════════════════════════════ */
function usePixelSwatch(
  swatchRef: React.RefObject<HTMLCanvasElement | null>,
  paintingRef: React.RefObject<HTMLImageElement | null>,
  gridCells: number = 4
) {
  const draw = useCallback(() => {
    const canvas = swatchRef.current;
    const img = paintingRef.current;
    if (!canvas || !img || !img.complete || img.naturalWidth === 0) return;
    paintPixelSwatch(canvas, img, gridCells);
  }, [swatchRef, paintingRef, gridCells]);

  useEffect(() => {
    draw();
    const img = paintingRef.current;
    if (img && !img.complete) img.addEventListener("load", draw);
    window.addEventListener("scroll", draw, { passive: true });
    window.addEventListener("resize", draw);
    return () => {
      img?.removeEventListener("load", draw);
      window.removeEventListener("scroll", draw);
      window.removeEventListener("resize", draw);
    };
  }, [draw, paintingRef]);
}

function StaticDetectionBox({
  value, style, animDelay = "0s", size = "sm", paintingRef,
}: {
  value: string; style: React.CSSProperties; animDelay?: string;
  size?: "sm" | "md" | "lg"; paintingRef: React.RefObject<HTMLImageElement | null>;
}) {
  const swatchRef = useRef<HTMLCanvasElement>(null);
  const swatchPx = size === "lg" ? 48 : 40;
  const fontSize = size === "lg" ? "13px" : size === "md" ? "12px" : "11px";
  const cornerSize = size === "lg" ? 12 : 10;
  const borderColor = "rgba(255,255,255,0.85)";
  usePixelSwatch(swatchRef, paintingRef, 3);

  const corners = [
    { top: 0, left: 0, bt: true, bl: true },
    { top: 0, right: 0, bt: true, br: true },
    { bottom: 0, left: 0, bb: true, bl: true },
    { bottom: 0, right: 0, bb: true, br: true },
  ];

  return (
    <div className="float-card" style={{ position: "absolute", zIndex: 10, animationDelay: animDelay, filter: "drop-shadow(0 4px 12px rgba(0,0,0,0.5))", ...style }}>
      <div style={{ position: "relative", display: "flex", alignItems: "center", padding: 3 }}>
        {corners.map((cs, i) => (
          <span key={i} style={{
            position: "absolute", width: cornerSize, height: cornerSize,
            top: cs.top, left: cs.left,
            right: (cs as { right?: number }).right, bottom: (cs as { bottom?: number }).bottom,
            borderTop: cs.bt ? `2px solid ${borderColor}` : undefined,
            borderLeft: cs.bl ? `2px solid ${borderColor}` : undefined,
            borderRight: (cs as { br?: boolean }).br ? `2px solid ${borderColor}` : undefined,
            borderBottom: (cs as { bb?: boolean }).bb ? `2px solid ${borderColor}` : undefined,
            borderTopLeftRadius: cs.bt && cs.bl ? 3 : 0,
            borderTopRightRadius: cs.bt && (cs as { br?: boolean }).br ? 3 : 0,
            borderBottomLeftRadius: (cs as { bb?: boolean }).bb && cs.bl ? 3 : 0,
            borderBottomRightRadius: (cs as { bb?: boolean }).bb && (cs as { br?: boolean }).br ? 3 : 0,
            zIndex: 2,
          }} />
        ))}
        <canvas ref={swatchRef} width={swatchPx} height={swatchPx} style={{ width: swatchPx, height: swatchPx, borderRadius: 2, flexShrink: 0, imageRendering: "pixelated", filter: "blur(1.5px)", boxShadow: "inset 0 0 0 10px rgba(0,0,0,0.3), 0 0 0 1px rgba(255,255,255,0.12)" }} />
        <span style={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace", fontSize, color: "rgba(255,255,255,0.95)", fontWeight: 500, letterSpacing: "0.04em", textShadow: "0 1px 3px rgba(0,0,0,0.6)", padding: "2px 6px", marginLeft: 2, background: "rgba(0,0,0,0.30)", backdropFilter: "blur(8px)", WebkitBackdropFilter: "blur(8px)", borderRadius: "0 3px 3px 0" }}>
          {value}
        </span>
      </div>
    </div>
  );
}

export default function Home() {
  const section2Ref = useRef<HTMLDivElement>(null);
  const scholarsPaintingRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const els = entry.target.querySelectorAll("[data-animate]");
            els.forEach((el, i) => {
              (el as HTMLElement).style.animation = `fade-rise 1s ease-out ${i * 0.18}s both`;
            });
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12 }
    );
    if (section2Ref.current) observer.observe(section2Ref.current);
    return () => observer.disconnect();
  }, []);

  return (
    <main>
      <style>{`
        @keyframes fade-rise {
          from { opacity: 0; transform: translateY(30px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50%      { transform: translateY(-10px); }
        }
        @keyframes scrollPulse {
          0%, 100% { opacity: 0.3; transform: scaleY(1); }
          50%      { opacity: 0.7; transform: scaleY(1.3); }
        }
        .animate-fade-rise      { animation: fade-rise 1.2s cubic-bezier(0.22, 1, 0.36, 1) both; }
        .animate-fade-rise-d1   { animation: fade-rise 1.2s cubic-bezier(0.22, 1, 0.36, 1) 0.35s both; }
        .float-card             { animation: float 6s ease-in-out infinite; will-change: transform; }
        .grain::before {
          content: ""; position: absolute; inset: 0; opacity: 0.05; pointer-events: none;
          background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
        }
      `}</style>

      <ScrollVideoHero />

      <section
        ref={section2Ref}
        className="crimson-section grain"
        style={{
          position: "relative", width: "100%", background: "#9a1b1b",
          padding: "6rem 1.5rem 4rem", display: "flex",
          flexDirection: "column", alignItems: "center",
          textAlign: "center", overflow: "hidden",
        }}
      >
        <div style={{ position: "absolute", top: "-20%", left: "50%", transform: "translateX(-50%)", width: "120%", height: "80%", background: "radial-gradient(circle, rgba(255,255,255,0.08) 0%, transparent 70%)", pointerEvents: "none" }} />

        <div data-animate style={{ opacity: 0 }}><MonogramLogo size={42} /></div>

        <p data-animate style={{ opacity: 0, fontSize: "11px", letterSpacing: "0.22em", color: "rgba(255,255,255,0.75)", maxWidth: "26rem", lineHeight: 1.8, textTransform: "uppercase", fontWeight: 500, marginTop: "1.75rem" }}>
          WE BUILT THIS STUDIO WITH A SINGLE CONVICTION — THAT LANGUAGE AND VISION BELONG IN THE SAME CREATIVE LOOP
        </p>

        <p data-animate style={{ opacity: 0, fontSize: "clamp(4rem, 8vw, 6.5rem)", fontWeight: 700, color: "white", margin: "1.75rem 0", lineHeight: 1.05, fontStyle: "italic", letterSpacing: "-0.02em", textShadow: "0 2px 20px rgba(0,0,0,0.2)" }}>
          S.PD
        </p>

        <div data-animate style={{ opacity: 0, maxWidth: "26rem", margin: "0 auto" }}>
          <p style={{ fontSize: "13px", color: "rgba(255,255,255,0.85)", lineHeight: 1.8, textAlign: "center", fontWeight: 300, marginBottom: "1.25rem" }}>
            I was exhausted by generative tools that demanded technical fluency before they gave you beauty. Prompt engineers, not artists, were the gatekeepers.

          </p>
          <p style={{ fontSize: "13px", color: "rgba(255,255,255,0.85)", lineHeight: 1.8, textAlign: "center", fontWeight: 300 }}>
            That is why we built a pipeline where your words do the thinking. RAG retrieves the references. CLIP guides the generation. The GAN paints. You just describe what you see in your mind.          </p>
        </div>

        <div data-animate style={{ opacity: 0, position: "relative", width: "100%", maxWidth: "900px", margin: "3.5rem auto 0", borderRadius: "1rem", overflow: "hidden", boxShadow: "0 24px 70px rgba(0,0,0,0.55)" }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img ref={scholarsPaintingRef} src="/scholars.png" alt="Classical scholars examining modern technology" crossOrigin="anonymous" style={{ width: "100%", height: "auto", display: "block", filter: "brightness(1.05) contrast(1.05)" }} />
          <div style={{ position: "absolute", inset: 0, background: "linear-gradient(to bottom, rgba(0,0,0,0.25) 0%, transparent 35%, transparent 65%, rgba(0,0,0,0.3) 100%)", pointerEvents: "none", borderRadius: "1rem" }} />

          <StaticDetectionBox value="0.1429" size="sm" animDelay="0s" style={{ top: "10%", left: "42%" }} paintingRef={scholarsPaintingRef} />
          <StaticDetectionBox value="0.7443" size="sm" animDelay="0.5s" style={{ top: "22%", left: "28%" }} paintingRef={scholarsPaintingRef} />
          <StaticDetectionBox value="0.8671" size="sm" animDelay="1.0s" style={{ top: "18%", right: "22%" }} paintingRef={scholarsPaintingRef} />
          <StaticDetectionBox value="1.0000" size="sm" animDelay="1.5s" style={{ top: "40%", right: "28%" }} paintingRef={scholarsPaintingRef} />
          <StaticDetectionBox value="1.7429" size="sm" animDelay="0.8s" style={{ top: "35%", left: "30%" }} paintingRef={scholarsPaintingRef} />
          <StaticDetectionBox value="1.5714" size="sm" animDelay="1.2s" style={{ bottom: "38%", left: "35%" }} paintingRef={scholarsPaintingRef} />
          <StaticDetectionBox value="1.8671" size="sm" animDelay="2.0s" style={{ bottom: "28%", left: "18%" }} paintingRef={scholarsPaintingRef} />
          <StaticDetectionBox value="2.0000" size="sm" animDelay="1.8s" style={{ bottom: "32%", left: "28%" }} paintingRef={scholarsPaintingRef} />
          <StaticDetectionBox value="1.7443" size="sm" animDelay="2.5s" style={{ bottom: "20%", right: "15%" }} paintingRef={scholarsPaintingRef} />
          <StaticDetectionBox value="2.2857" size="sm" animDelay="3.0s" style={{ bottom: "12%", right: "5%" }} paintingRef={scholarsPaintingRef} />
        </div>
      </section>
    </main>
  );
}