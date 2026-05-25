"use client";

import { useEffect, useRef, useCallback } from "react";

/* ─── SVG Monogram Logo ─── */
function MonogramLogo({ size = 32 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M32 4C32 4 12 18 12 36C12 48 20 56 32 56C28 56 20 50 20 38C20 22 32 4 32 4Z"
        fill="white"
        opacity="0.9"
      />
      <path
        d="M32 60C32 60 52 46 52 28C52 16 44 8 32 8C36 8 44 14 44 26C44 42 32 60 32 60Z"
        fill="white"
        opacity="0.7"
      />
    </svg>
  );
}

/* ─── Canvas pixel-sampler hook ─── */
function usePixelSwatch(
  swatchRef: React.RefObject<HTMLCanvasElement>,
  paintingRef: React.RefObject<HTMLImageElement>,
  gridCells: number = 4
) {
  const draw = useCallback(() => {
    const canvas = swatchRef.current;
    const img = paintingRef.current;
    if (!canvas || !img || !img.complete || img.naturalWidth === 0) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const imgRect = img.getBoundingClientRect();
    const canvasRect = canvas.getBoundingClientRect();

    // Map canvas position to painting's natural pixel space
    const scaleX = img.naturalWidth / imgRect.width;
    const scaleY = img.naturalHeight / imgRect.height;

    const srcX = (canvasRect.left - imgRect.left) * scaleX;
    const srcY = (canvasRect.top - imgRect.top) * scaleY;
    const srcW = canvasRect.width * scaleX;
    const srcH = canvasRect.height * scaleY;

    // Clamp source rectangle to image bounds
    if (
      srcX + srcW < 0 ||
      srcY + srcH < 0 ||
      srcX > img.naturalWidth ||
      srcY > img.naturalHeight
    )
      return;

    const size = gridCells;

    // Draw downsampled to gridCells×gridCells
    ctx.imageSmoothingEnabled = true;
    ctx.drawImage(img, srcX, srcY, srcW, srcH, 0, 0, size, size);

    // Read pixels
    let imageData: ImageData;
    try {
      imageData = ctx.getImageData(0, 0, size, size);
    } catch {
      // crossOrigin not set or CORS blocked — fall back to a solid grey
      ctx.fillStyle = "rgba(100,100,100,0.6)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      return;
    }

    // Clear and redraw as pixelated mosaic
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const cellW = canvas.width / size;
    const cellH = canvas.height / size;

    for (let row = 0; row < size; row++) {
      for (let col = 0; col < size; col++) {
        const i = (row * size + col) * 4;
        const r = imageData.data[i];
        const g = imageData.data[i + 1];
        const b = imageData.data[i + 2];
        ctx.fillStyle = `rgb(${r},${g},${b})`;
        ctx.fillRect(
          Math.floor(col * cellW),
          Math.floor(row * cellH),
          Math.ceil(cellW),
          Math.ceil(cellH)
        );
      }
    }

    // Subtle grid lines
    ctx.strokeStyle = "rgba(0,0,0,0.2)";
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= size; i++) {
      ctx.beginPath();
      ctx.moveTo(i * cellW, 0);
      ctx.lineTo(i * cellW, canvas.height);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(0, i * cellH);
      ctx.lineTo(canvas.width, i * cellH);
      ctx.stroke();
    }
  }, [swatchRef, paintingRef, gridCells]);

  useEffect(() => {
    // Draw immediately (image may already be loaded)
    draw();

    // Also draw once image finishes loading
    const img = paintingRef.current;
    if (img && !img.complete) {
      img.addEventListener("load", draw);
    }

    window.addEventListener("scroll", draw, { passive: true });
    window.addEventListener("resize", draw);

    return () => {
      img?.removeEventListener("load", draw);
      window.removeEventListener("scroll", draw);
      window.removeEventListener("resize", draw);
    };
  }, [draw, paintingRef]);

  return draw;
}

/* ─── ML Detection Bounding Box with real canvas pixel swatch ─── */
function DetectionBox({
  value,
  style,
  animDelay = "0s",
  size = "sm",
  paintingRef,
}: {
  value: string;
  style: React.CSSProperties;
  animDelay?: string;
  size?: "sm" | "md" | "lg";
  paintingRef: React.RefObject<HTMLImageElement>;
}) {
  const swatchRef = useRef<HTMLCanvasElement>(null);
  const swatchPx = size === "lg" ? 48 : size === "md" ? 40 : 40;
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
      <div
        style={{
          position: "relative",
          display: "flex",
          alignItems: "center",
          padding: 3,
        }}
      >
        {/* Corner brackets */}
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
              borderRight: (cs as { br?: boolean }).br
                ? `2px solid ${borderColor}`
                : undefined,
              borderBottom: (cs as { bb?: boolean }).bb
                ? `2px solid ${borderColor}`
                : undefined,
              borderTopLeftRadius: cs.bt && cs.bl ? 3 : 0,
              borderTopRightRadius:
                cs.bt && (cs as { br?: boolean }).br ? 3 : 0,
              borderBottomLeftRadius:
                (cs as { bb?: boolean }).bb && cs.bl ? 3 : 0,
              borderBottomRightRadius:
                (cs as { bb?: boolean }).bb && (cs as { br?: boolean }).br
                  ? 3
                  : 0,
              zIndex: 2,
            }}
          />
        ))}

        {/* ── Real pixel-sampled canvas swatch ── */}
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
            
            boxShadow:
              "inset 0 0 0 10px rgba(0,0,0,0.3), 0 0 0 1px rgba(255,255,255,0.12)",
          }}
        />

        {/* Value label */}
        <span
          style={{
            fontFamily:
              "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
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

/* ═══════════════════════════════════════════════════════
   HOME PAGE
   ═══════════════════════════════════════════════════════ */
export default function Home() {
  const section2Ref = useRef<HTMLDivElement>(null);
  const heroPaintingRef = useRef<HTMLImageElement>(null);
  const scholarsPaintingRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const els = entry.target.querySelectorAll("[data-animate]");
            els.forEach((el, i) => {
              (el as HTMLElement).style.animation = `fade-rise 1s ease-out ${i * 0.18
                }s both`;
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
      {/* ═══════════════════════════════════════════════════════
          GLOBAL ANIMATIONS & BASE STYLES
          ═══════════════════════════════════════════════════════ */}
      <style>{`
        @keyframes fade-rise {
          from { opacity: 0; transform: translateY(30px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50%      { transform: translateY(-10px); }
        }
        @keyframes scan {
          0%   { top: 0%; opacity: 0; }
          15%  { opacity: 1; }
          85%  { opacity: 1; }
          100% { top: 100%; opacity: 0; }
        }
        .animate-fade-rise {
          animation: fade-rise 1.2s cubic-bezier(0.22, 1, 0.36, 1) both;
        }
        .animate-fade-rise-d1 {
          animation: fade-rise 1.2s cubic-bezier(0.22, 1, 0.36, 1) 0.35s both;
        }
        .float-card {
          animation: float 6s ease-in-out infinite;
          will-change: transform;
        }
        .grain::before {
          content: "";
          position: absolute;
          inset: 0;
          opacity: 0.05;
          pointer-events: none;
          background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
        }
      `}</style>

      {/* ═══════════════════════════════════════════════════════
          SECTION 1 — BAROQUE HERO
          ═══════════════════════════════════════════════════════ */}
      <section
        className="baroque-hero"
        id="hero-section"
        style={{
          position: "relative",
          width: "100%",
          minHeight: "100vh",
          overflow: "hidden",
          background: "#1a1510",
        }}
      >
        {/* Background painting — crossOrigin required for canvas pixel access */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          ref={heroPaintingRef}
          src="/hero-painting.png"
          alt=""
          aria-hidden="true"
          crossOrigin="anonymous"
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

        {/* Vignette + bottom gradient for text legibility */}
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

        {/* ── Navigation Bar ── */}
        <nav
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            zIndex: 20,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "1.5rem 2.5rem",
            maxWidth: "80rem",
            margin: "0 auto",
          }}
        >
          <div style={{ display: "flex", alignItems: "center" }}>
            <MonogramLogo size={34} />
            <p
              style={{
                fontSize: "11px",
                color: "rgba(255,255,255,0.7)",
                lineHeight: 1.5,
                maxWidth: "140px",
                marginLeft: "0.9rem",
                fontWeight: 300,
                letterSpacing: "0.02em",
              }}
            >
              Complete Business Automation. We Handle All Tasks. You Relax.
            </p>
          </div>
          <button
            id="get-started-btn"
            style={{
              padding: "0.6rem 1.75rem",
              fontSize: "0.75rem",
              textTransform: "uppercase",
              letterSpacing: "0.18em",
              color: "rgba(255,255,255,0.9)",
              borderRadius: "9999px",
              cursor: "pointer",
              fontWeight: 400,
              background: "rgba(255,255,255,0.06)",
              border: "1px solid rgba(255,255,255,0.35)",
              transition: "all 0.3s ease",
              backdropFilter: "blur(4px)",
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

        {/* ── ML Detection Boxes — Hero ── */}
        <DetectionBox
          value="0.1429"
          size="sm"
          animDelay="0s"
          style={{ top: "8%", left: "48%", zIndex: 10,opacity: 0.5, }}
          paintingRef={heroPaintingRef}
        />
        <DetectionBox
          value="0.2857"
          size="sm"
          animDelay="0.6s"
          style={{ top: "16%", left: "16%", zIndex: 10 }}
          paintingRef={heroPaintingRef}
        />
        <DetectionBox
          value="0.7443"
          size="md"
          animDelay="1.2s"
          style={{ top: "20%", left: "42%", zIndex: 10 }}
          paintingRef={heroPaintingRef}
        />
        <DetectionBox
          value="1.0000"
          size="md"
          animDelay="1.8s"
          style={{ top: "18%", left: "32%", zIndex: 10 }}
          paintingRef={heroPaintingRef}
        />
        <DetectionBox
          value="1.1429"
          size="sm"
          animDelay="2.4s"
          style={{ top: "28%", right: "30%", zIndex: 10 }}
          paintingRef={heroPaintingRef}
        />
        <DetectionBox
          value="1.5714"
          size="sm"
          animDelay="1.5s"
          style={{ top: "36%", right: "18%", zIndex: 10 }}
          paintingRef={heroPaintingRef}
        />
        <DetectionBox
          value="1.8671"
          size="sm"
          animDelay="2.0s"
          style={{ top: "52%", left: "34%", zIndex: 10 }}
          paintingRef={heroPaintingRef}
        />
        <DetectionBox
          value="2.2857"
          size="sm"
          animDelay="3s"
          style={{ bottom: "32%", left: "38%", zIndex: 10 }}
          paintingRef={heroPaintingRef}
        />

        {/* ── Body text (left column) ── */}
        <div
          className="animate-fade-rise-d1"
          style={{
            position: "absolute",
            bottom: "20%",
            left: "2.5rem",
            maxWidth: "240px",
            zIndex: 10,
          }}
        >
          <p
            style={{
              fontSize: "11px",
              color: "rgba(255,255,255,0.82)",
              lineHeight: 1.75,
              fontWeight: 300,
              marginBottom: "1rem",
              textShadow: "0 1px 10px rgba(0,0,0,0.5)",
            }}
          >
            Our SaaS product takes over all exhausting operational activities,
            complex analytics, and tedious process management. While algorithms
            seamlessly build your success infrastructure and generate stable
            profit, you get time for truly important things.
          </p>
          <p
            style={{
              fontSize: "11px",
              color: "rgba(255,255,255,0.82)",
              lineHeight: 1.75,
              fontWeight: 300,
              textShadow: "0 1px 10px rgba(0,0,0,0.5)",
            }}
          >
            Delegate micromanagement to artificial intelligence and reliable
            cloud solutions to enjoy absolute peace of mind.
          </p>
        </div>

        {/* ── Hero H1 ── */}
        <h1
          className="animate-fade-rise"
          style={{
            position: "absolute",
            bottom: "6%",
            right: "2.5rem",
            textAlign: "right",
            maxWidth: "55%",
            fontSize: "clamp(2.6rem, 5.2vw, 4.8rem)",
            lineHeight: 0.98,
            letterSpacing: "-1.2px",
            fontWeight: 400,
            color: "white",
            fontStyle: "italic",
            zIndex: 10,
            textShadow: "0 4px 30px rgba(0,0,0,0.55)",
          }}
        >
          Intelligent Daily
          <br />
          Routine Automation
          <br />
          For Your Business.
          <br />
          You Relax
        </h1>
      </section>

      {/* ═══════════════════════════════════════════════════════
          SECTION 2 — CRIMSON MANIFESTO
          ═══════════════════════════════════════════════════════ */}
      <section
        ref={section2Ref}
        className="crimson-section grain"
        id="crimson-section"
        style={{
          position: "relative",
          width: "100%",
          background: "#9a1b1b",
          padding: "6rem 1.5rem 4rem",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          textAlign: "center",
          overflow: "hidden",
        }}
      >
        {/* Subtle radial glow */}
        <div
          style={{
            position: "absolute",
            top: "-20%",
            left: "50%",
            transform: "translateX(-50%)",
            width: "120%",
            height: "80%",
            background:
              "radial-gradient(circle, rgba(255,255,255,0.08) 0%, transparent 70%)",
            pointerEvents: "none",
          }}
        />

        {/* Logo */}
        <div data-animate style={{ opacity: 0 }}>
          <MonogramLogo size={42} />
        </div>

        {/* Tagline */}
        <p
          data-animate
          style={{
            opacity: 0,
            fontSize: "11px",
            letterSpacing: "0.22em",
            color: "rgba(255,255,255,0.75)",
            maxWidth: "26rem",
            lineHeight: 1.8,
            textTransform: "uppercase",
            fontWeight: 500,
            marginTop: "1.75rem",
          }}
        >
          We built this platform with a single purpose to eliminate operational
          chaos and restore balance to your daily business routine
        </p>

        {/* Signature Script */}
        <p
          data-animate
          style={{
            opacity: 0,
            fontSize: "clamp(4rem, 8vw, 6.5rem)",
            fontWeight: 700,
            color: "white",
            margin: "1.75rem 0",
            lineHeight: 1.05,
            fontStyle: "italic",
            letterSpacing: "-0.02em",
            textShadow: "0 2px 20px rgba(0,0,0,0.2)",
          }}
        >
          S.PD
        </p>

        {/* Body paragraphs */}
        <div
          data-animate
          style={{
            opacity: 0,
            maxWidth: "26rem",
            margin: "0 auto",
          }}
        >
          <p
            style={{
              fontSize: "13px",
              color: "rgba(255,255,255,0.85)",
              lineHeight: 1.8,
              textAlign: "center",
              fontWeight: 300,
              marginBottom: "1.25rem",
            }}
          >
            I was exhausted by software that demanded more effort than it
            actually saved. That is why we engineered an autonomous architecture
            that operates silently in the background.
          </p>
          <p
            style={{
              fontSize: "13px",
              color: "rgba(255,255,255,0.85)",
              lineHeight: 1.8,
              textAlign: "center",
              fontWeight: 300,
            }}
          >
            Your business should serve your life, not consume it. Let our
            algorithms handle the heavy lifting, so you can focus on the vision.
          </p>
        </div>

        {/* ── Scholars Painting with Detection Box Overlays ── */}
        <div
          data-animate
          style={{
            opacity: 0,
            position: "relative",
            width: "100%",
            maxWidth: "900px",
            margin: "3.5rem auto 0",
            borderRadius: "1rem",
            overflow: "hidden",
            boxShadow: "0 24px 70px rgba(0,0,0,0.55)",
          }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            ref={scholarsPaintingRef}
            src="/scholars.png"
            alt="Classical scholars examining modern technology — baroque painting"
            crossOrigin="anonymous"
            style={{
              width: "100%",
              height: "auto",
              display: "block",
              filter: "brightness(1.05) contrast(1.05)",
            }}
          />

          {/* Gradient overlay */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              background:
                "linear-gradient(to bottom, rgba(0,0,0,0.25) 0%, transparent 35%, transparent 65%, rgba(0,0,0,0.3) 100%)",
              pointerEvents: "none",
              borderRadius: "1rem",
            }}
          />

          {/* Detection boxes — Scholars */}
          <DetectionBox
            value="0.1429"
            size="sm"
            animDelay="0s"
            style={{ top: "10%", left: "42%" }}
            paintingRef={scholarsPaintingRef}
          />
          <DetectionBox
            value="0.7443"
            size="sm"
            animDelay="0.5s"
            style={{ top: "22%", left: "28%" }}
            paintingRef={scholarsPaintingRef}
          />
          <DetectionBox
            value="0.8671"
            size="sm"
            animDelay="1.0s"
            style={{ top: "18%", right: "22%" }}
            paintingRef={scholarsPaintingRef}
          />
          <DetectionBox
            value="1.0000"
            size="sm"
            animDelay="1.5s"
            style={{ top: "40%", right: "28%" }}
            paintingRef={scholarsPaintingRef}
          />
          <DetectionBox
            value="1.7429"
            size="sm"
            animDelay="0.8s"
            style={{ top: "35%", left: "30%" }}
            paintingRef={scholarsPaintingRef}
          />
          <DetectionBox
            value="1.5714"
            size="sm"
            animDelay="1.2s"
            style={{ bottom: "38%", left: "35%" }}
            paintingRef={scholarsPaintingRef}
          />
          <DetectionBox
            value="1.8671"
            size="sm"
            animDelay="2.0s"
            style={{ bottom: "28%", left: "18%" }}
            paintingRef={scholarsPaintingRef}
          />
          <DetectionBox
            value="2.0000"
            size="sm"
            animDelay="1.8s"
            style={{ bottom: "32%", left: "28%" }}
            paintingRef={scholarsPaintingRef}
          />
          <DetectionBox
            value="1.7443"
            size="sm"
            animDelay="2.5s"
            style={{ bottom: "20%", right: "15%" }}
            paintingRef={scholarsPaintingRef}
          />
          <DetectionBox
            value="2.2857"
            size="sm"
            animDelay="3.0s"
            style={{ bottom: "12%", right: "5%" }}
            paintingRef={scholarsPaintingRef}
          />
        </div>
      </section>
    </main>
  );
}