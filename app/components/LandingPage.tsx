'use client';

import { useRef, useEffect, useState, useCallback } from 'react';
import dynamic from 'next/dynamic';
import {
  motion,
  useScroll,
  useTransform,
  useSpring,
  useMotionValueEvent,
} from 'motion/react';
import Lenis from 'lenis';

/* ── Lazy-load Scene3D (no SSR) ── */
const Scene3D = dynamic(() => import('./Scene3D'), { ssr: false });

/* ══════════════════════════════════════════════════════════
   Floating Nav
   ══════════════════════════════════════════════════════════ */
function FloatingNav({ visible }: { visible: boolean }) {
  return (
    <motion.header
      className="floating-nav"
      initial={{ y: -100 }}
      animate={{ y: visible ? 0 : -100 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
    >
      <div className="nav-logo">Art Studio</div>
      <nav>
        <ul className="nav-links">
          <li><a href="#hero" className="nav-link">[G] Github</a></li>
          <li><a href="#pipeline" className="nav-link">[D] Docs</a></li>
          <li><a href="#studio" className="nav-link">[B] Blog</a></li>
          <li><a href="#" className="nav-link">[S] Studio</a></li>
        </ul>
      </nav>
    </motion.header>
  );
}

/* ══════════════════════════════════════════════════════════
   Section Indicator
   ══════════════════════════════════════════════════════════ */
const SECTIONS = ['The Vision', 'The Pipeline', 'The Studio'];

function SectionIndicator({ activeIndex }: { activeIndex: number }) {
  return (
    <div className="section-indicator">
      {SECTIONS.map((label, i) => (
        <div key={label} className={`indicator-item ${i === activeIndex ? 'active' : ''}`}>
          <span className="indicator-dot" />
          <span>{label}</span>
        </div>
      ))}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════
   Animated Text Helpers
   ══════════════════════════════════════════════════════════ */
function StaggerWords({ text, delay = 0 }: { text: string; delay?: number }) {
  return (
    <span style={{ display: 'inline' }}>
      {text.split(' ').map((word, i) => (
        <motion.span
          key={`${word}-${i}`}
          initial={{ opacity: 0, y: 30, filter: 'blur(8px)' }}
          whileInView={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
          transition={{
            duration: 0.6,
            delay: delay + i * 0.08,
            ease: [0.25, 0.46, 0.45, 0.94],
          }}
          viewport={{ once: true, amount: 0.5 }}
          style={{ display: 'inline-block', marginRight: '0.3em' }}
        >
          {word}
        </motion.span>
      ))}
    </span>
  );
}

/* ══════════════════════════════════════════════════════════
   Hero Section (0 – 33%)
   ══════════════════════════════════════════════════════════ */
function HeroSection() {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ['start start', 'end start'],
  });

  const opacity = useTransform(scrollYProgress, [0, 0.6, 1], [1, 1, 0]);
  const y = useTransform(scrollYProgress, [0.5, 1], [0, -80]);
  const scale = useTransform(scrollYProgress, [0.5, 1], [1, 0.95]);

  return (
    <section ref={ref} className="section-overlay" style={{ height: '160vh' }} id="hero">
      <motion.div className="section-content" style={{ opacity, y, scale }}>
        <div style={{ maxWidth: 620 }}>
          <motion.div
            className="section-subtitle"
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            viewport={{ once: true }}
          >
            RAG-Powered GAN Art Studio
          </motion.div>

          <h1 className="display-heading">
            <StaggerWords text="Describe a style." delay={0.5} />
            <br />
            <StaggerWords text="Retrieve context." delay={0.8} />
            <br />
            <StaggerWords text="Generate art." delay={1.1} />
          </h1>

          <motion.p
            className="section-body"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 1.4 }}
            viewport={{ once: true }}
          >
            Art Studio ships with a RAG engine that retrieves reference images and
            artist context, then a CLIP-guided GAN generates a new artwork in that
            style. Whether you describe it or tweak it by hand, Art Studio just works.
          </motion.p>

          <motion.div
            className="tag-row"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 1.7 }}
            viewport={{ once: true }}
          >
            <span className="tag">RAG-Powered</span>
            <span className="tag">CLIP-Guided</span>
            <span className="tag">StyleGAN2</span>
            <span className="tag">WikiArt</span>
          </motion.div>
        </div>
      </motion.div>
    </section>
  );
}

/* ══════════════════════════════════════════════════════════
   Pipeline Section (33% – 66%)
   ══════════════════════════════════════════════════════════ */
function PipelineSection() {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ['start end', 'end start'],
  });

  const opacity = useTransform(scrollYProgress, [0, 0.2, 0.7, 1], [0, 1, 1, 0]);
  const y = useTransform(scrollYProgress, [0, 0.2], [60, 0]);
  const scale = useTransform(scrollYProgress, [0.7, 1], [1, 0.95]);

  return (
    <section ref={ref} className="section-overlay" style={{ height: '160vh' }} id="pipeline">
      <motion.div className="section-content" style={{ opacity, y, scale }}>
        <div style={{ maxWidth: 560 }}>
          <motion.div
            className="section-subtitle"
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
            viewport={{ once: true, amount: 0.5 }}
          >
            The Pipeline
          </motion.div>

          <h2 className="display-heading">
            <StaggerWords text="Two systems," />
            <br />
            <StaggerWords text="one seamless" delay={0.2} />
            <br />
            <StaggerWords text="pipeline." delay={0.4} />
          </h2>

          <motion.p
            className="section-body"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.6 }}
            viewport={{ once: true, amount: 0.5 }}
          >
            Describe any art style in natural language. Our RAG engine retrieves
            the most relevant reference artworks and artist context. Then CLIP-guided
            latent steering shapes a StyleGAN2 output to match your vision — not just
            a class label, but the actual artistic DNA.
          </motion.p>

          <motion.div
            className="pipeline-steps"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.8 }}
            viewport={{ once: true, amount: 0.5 }}
          >
            {[
              'Text-to-style RAG retrieval',
              'CLIP embedding space mapping',
              'Latent vector optimization',
              'Style-conditioned generation',
            ].map((step, i) => (
              <motion.div
                key={step}
                className="pipeline-step"
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.4, delay: 0.9 + i * 0.12 }}
                viewport={{ once: true }}
              >
                <span className="step-number">{i + 1}</span>
                <span>{step}</span>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </motion.div>
    </section>
  );
}

/* ══════════════════════════════════════════════════════════
   Studio CTA Section (66% – 100%)
   ══════════════════════════════════════════════════════════ */
function StudioCTA() {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ['start end', 'end end'],
  });

  const opacity = useTransform(scrollYProgress, [0, 0.3, 1], [0, 1, 1]);
  const y = useTransform(scrollYProgress, [0, 0.3], [80, 0]);

  return (
    <section ref={ref} className="section-overlay" style={{ height: '120vh' }} id="studio">
      <motion.div
        className="section-content"
        style={{
          opacity,
          y,
          justifyContent: 'flex-end',
          textAlign: 'right',
        }}
      >
        <div style={{ maxWidth: 600 }}>
          <motion.div
            className="section-subtitle"
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
            viewport={{ once: true, amount: 0.5 }}
            style={{ textAlign: 'right' }}
          >
            One platform for any creative vision
          </motion.div>

          <h2 className="display-heading" style={{ textAlign: 'right' }}>
            <StaggerWords text="Your imagination." />
            <br />
            <StaggerWords text="Our engine." delay={0.2} />
            <br />
            <StaggerWords text="Infinite styles." delay={0.4} />
          </h2>

          <motion.p
            className="section-body"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.6 }}
            viewport={{ once: true, amount: 0.5 }}
            style={{ marginLeft: 'auto', textAlign: 'right' }}
          >
            Whatever you want to create, Art Studio can make it happen.
            Start something new, blend styles, or explore the embedding space
            of 10,000+ artworks. One technology, used in whatever way
            the project needs.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.8 }}
            viewport={{ once: true }}
            style={{ display: 'flex', justifyContent: 'flex-end' }}
          >
            <a href="#" className="cta-button">
              Enter the Studio
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path
                  d="M3 8H13M13 8L9 4M13 8L9 12"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </a>
          </motion.div>
        </div>
      </motion.div>
    </section>
  );
}

/* ══════════════════════════════════════════════════════════
   Main Landing Page
   ══════════════════════════════════════════════════════════ */
export default function LandingPage() {
  const [navVisible, setNavVisible] = useState(true);
  const [activeSection, setActiveSection] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  /* ── Lenis smooth scroll ── */
  useEffect(() => {
    const lenis = new Lenis({
      duration: 1.2,
      easing: (t: number) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      touchMultiplier: 1.5,
    });

    function raf(time: number) {
      lenis.raf(time);
      requestAnimationFrame(raf);
    }
    requestAnimationFrame(raf);

    return () => lenis.destroy();
  }, []);

  /* ── Track scroll for nav + indicator ── */
  const { scrollYProgress } = useScroll();
  const smoothProgress = useSpring(scrollYProgress, { stiffness: 100, damping: 30 });

  useMotionValueEvent(smoothProgress, 'change', (v) => {
    setNavVisible(true);
    if (v < 0.3) setActiveSection(0);
    else if (v < 0.65) setActiveSection(1);
    else setActiveSection(2);
  });

  return (
    <>
      {/* 3D background */}
      <Scene3D />

      {/* Navigation */}
      <FloatingNav visible={navVisible} />

      {/* Section indicator */}
      <SectionIndicator activeIndex={activeSection} />

      {/* Scrollable content */}
      <div className="scroll-container" ref={containerRef}>
        <HeroSection />
        <PipelineSection />
        <StudioCTA />
      </div>
    </>
  );
}
