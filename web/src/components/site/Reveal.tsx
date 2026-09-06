"use client";

import { motion } from "motion/react";
import type { ReactNode } from "react";
import { useQaMotionOff } from "@/lib/motion";

const ease = [0.22, 1, 0.36, 1] as const;

/**
 * Fade-and-rise when the element scrolls into view. Under reduced motion
 * (MotionConfig) only the fade remains. With ?motion=off the element is
 * shown as soon as it mounts, which is what screenshots need.
 */
export function Reveal({ children, delay = 0, y = 18, className, as = "div", once = true }:
  { children: ReactNode; delay?: number; y?: number; className?: string; as?: "div" | "section" | "li" | "p" | "h1" | "h2"; once?: boolean }) {
  const M = motion[as];
  const qa = useQaMotionOff();
  if (qa) return <M className={className}>{children}</M>;
  return (
    <M
      className={className}
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once, margin: "0px 0px -10% 0px" }}
      transition={{ duration: 0.7, delay, ease }}
    >
      {children}
    </M>
  );
}

/** Staggered children: wrap a list, each child rises in turn. */
export function Stagger({ children, className, step = 0.08 }: { children: ReactNode; className?: string; step?: number }) {
  const qa = useQaMotionOff();
  if (qa) return <div className={className}>{children}</div>;
  return (
    <motion.div
      className={className}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, margin: "0px 0px -10% 0px" }}
      variants={{ hidden: {}, show: { transition: { staggerChildren: step } } }}
    >
      {children}
    </motion.div>
  );
}

export function Item({ children, className }: { children: ReactNode; className?: string }) {
  const qa = useQaMotionOff();
  if (qa) return <div className={className}>{children}</div>;
  return (
    <motion.div className={className} variants={{ hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0, transition: { duration: 0.6, ease } } }}>
      {children}
    </motion.div>
  );
}
