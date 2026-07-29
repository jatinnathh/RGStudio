"use client";
import React from "react";
import { motion, useScroll, useTransform } from "framer-motion";

interface HeroTextProps {
  text?: string;
  className?: string;
  color?: string;
}

export default function HeroText({
  text = "IMMERSE",
  className = "",
  color = "#ffffff",
}: HeroTextProps) {
  const characters = text.split("");
  const { scrollYProgress } = useScroll();
  const y = useTransform(scrollYProgress, [0.4, 0.75], ["0vh", "-15vh"]);

  return (
    <div className={`pointer-events-none flex flex-col items-center justify-center w-full ${className}`}>
      <div className="relative z-10 w-full px-4 flex flex-col items-center">
        <motion.div style={{ y }} className="flex flex-wrap justify-center items-center w-full">
          {characters.map((char, i) => {
            // Text disappears and slices sweep starting slightly earlier in the scroll
            const start = 0.4 + i * 0.015;
            const end = start + 0.15;

            // Main text opacity maps from 1 to 0
            const opacity = useTransform(scrollYProgress, [start, end], [1, 0]);
            // Blur maps from 0px to 10px
            const blur = useTransform(scrollYProgress, [start, end], ["blur(0px)", "blur(10px)"]);

            // Slices sweep in from opposite sides
            const slice1X = useTransform(scrollYProgress, [start, end], ["-100%", "100%"]);
            const slice1Opacity = useTransform(scrollYProgress, [start, start + 0.05, end], [0, 1, 0]);

            const slice2X = useTransform(scrollYProgress, [start + 0.02, end + 0.02], ["100%", "-100%"]);
            const slice2Opacity = useTransform(scrollYProgress, [start + 0.02, start + 0.07, end + 0.02], [0, 1, 0]);

            const slice3X = useTransform(scrollYProgress, [start + 0.04, end + 0.04], ["-100%", "100%"]);
            const slice3Opacity = useTransform(scrollYProgress, [start + 0.04, start + 0.09, end + 0.04], [0, 1, 0]);

            return (
              <div key={i} className="relative px-[0.1vw] overflow-hidden group">
                {/* Main Character */}
                <motion.span
                  style={{ opacity, filter: blur, color }}
                  className="text-[12vw] leading-none font-black tracking-tighter"
                >
                  {char === " " ? "\u00A0" : char}
                </motion.span>

                {/* Top Slice Layer */}
                <motion.span
                  style={{ x: slice1X, opacity: slice1Opacity, clipPath: "polygon(0 0, 100% 0, 100% 35%, 0 35%)", color }}
                  className="absolute inset-0 text-[12vw] leading-none font-black z-10 pointer-events-none"
                >
                  {char}
                </motion.span>

                {/* Middle Slice Layer */}
                <motion.span
                  style={{ x: slice2X, opacity: slice2Opacity, clipPath: "polygon(0 35%, 100% 35%, 100% 65%, 0 65%)", color }}
                  className="absolute inset-0 text-[12vw] leading-none font-black z-10 pointer-events-none"
                >
                  {char}
                </motion.span>

                {/* Bottom Slice Layer */}
                <motion.span
                  style={{ x: slice3X, opacity: slice3Opacity, clipPath: "polygon(0 65%, 100% 65%, 100% 100%, 0 100%)", color }}
                  className="absolute inset-0 text-[12vw] leading-none font-black z-10 pointer-events-none"
                >
                  {char}
                </motion.span>
              </div>
            );
          })}
        </motion.div>
      </div>
    </div>
  );
}
