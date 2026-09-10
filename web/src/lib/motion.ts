"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { useReducedMotion } from "motion/react";

/**
 * Motion preferences in one place.
 *
 * - <MotionConfig reducedMotion="user"> in the site layout lets Motion drop
 *   transform animations for visitors who asked for reduced motion while
 *   keeping simple fades; server and client render the same markup.
 * - QA: /?motion=off is read by the page on the server and passed down
 *   through QaContext, so components can render their settled state on the
 *   very first paint without a hydration mismatch. Used for screenshots and
 *   as a hard "no motion" check.
 * - useReduce() answers the same question for timers, canvases and pointer
 *   effects that are not Motion animations.
 */
export const QaContext = createContext(false);

export function useQaMotionOff(): boolean {
  return useContext(QaContext);
}

export function useReduce(): boolean {
  const pref = useReducedMotion();
  const qa = useQaMotionOff();
  return Boolean(pref) || qa;
}

/** For the MotionConfig wrapper, which lives in a layout and cannot see search params. */
export function useMotionOffFromUrl(): boolean {
  const [off, setOff] = useState(false);
  useEffect(() => { setOff(new URLSearchParams(window.location.search).get("motion") === "off"); }, []);
  return off;
}

/** Same answer outside React, for the canvas loop. */
export function reduceMotionNow(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches || new URLSearchParams(window.location.search).get("motion") === "off";
}
