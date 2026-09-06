"use client";

import { MotionConfig } from "motion/react";
import { useMotionOffFromUrl } from "@/lib/motion";

/** Reduced motion follows the visitor's setting; ?motion=off forces it for QA. */
export function MotionRoot({ children }: { children: React.ReactNode }) {
  const off = useMotionOffFromUrl();
  return <MotionConfig reducedMotion={off ? "always" : "user"}>{children}</MotionConfig>;
}
