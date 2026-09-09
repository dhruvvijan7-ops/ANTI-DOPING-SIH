import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import { prefersReducedMotion } from "@/components/landing/Reveal";

const INTRO_SEEN_KEY = "verity.intro.seen";

// Timeline (ms from mount). Total ≈ 3550ms → 3.5s, inside the 3–4s target.
//   Phase A   write      0     → ~1420ms   VERITY is progressively drawn
//   Phase B   hold     1420   →  2040ms   completed wordmark registers
//   Phase C   focus    2040   →   2540ms   camera pushes toward the I
//   Phase D   zoom     2540   →   3550ms   through the hollow dot; reveal
export const INTRO_WRITE_MS = 1420;
export const INTRO_ZOOM_MS = 1510;
export const INTRO_LANDING_REVEAL_FROM = 0.014;

const MEASURE_MS = 260;
const HOLD_END_MS = 2040;
const ZOOM_MS = INTRO_ZOOM_MS;
const FADE_START_MS = 2540;
const FADE_MS = 1010;
const END_MS = 3550;
const REDUCED_END_MS = 900;
const WORD_ZOOM_SCALE = 16;

type Phase = "enter" | "zoom" | "fade";

export interface IntroPoint {
  x: number;
  y: number;
}

/** VERITY opening animation for the public landing page.
 *
 * Stage 1: minimal paper background. Stage 2: the centered VERITY wordmark is
 * progressively "written" left→right (clip-path sweep); the hollow I-dot is
 * dotted last. Stage 3: the wordmark holds so it registers. Stage 4: the camera
 * pushes toward the I, then passes through the hollow dot — the wordmark scales
 * up around the measured dot centre and fades, the landing page grows out of
 * that same measured point, and the paper dissolves.
 *
 * Pure CSS transforms/opacity on a handful of elements — no canvas/WebGL/deps.
 * Geometry is measured once from the rendered dot (viewport-correct), never a
 * hardcoded coordinate. Reduced motion skips the sweep and zoom and cuts
 * straight to the page. Plays at most once per session and is skipped for
 * deep links (#anchor).
 */
export default function Intro({
  onComplete,
  onZoom,
}: {
  onComplete?: () => void;
  onZoom?: (dot: IntroPoint) => void;
}) {
  const location = useLocation();
  const [phase, setPhase] = useState<Phase>("enter");
  const [done, setDone] = useState(false);
  const [wordOrigin, setWordOrigin] = useState<IntroPoint | null>(null);
  const wordRef = useRef<HTMLDivElement>(null);
  const markerRef = useRef<HTMLSpanElement>(null);
  const originRef = useRef<IntroPoint | null>(null);

  const reduced = prefersReducedMotion();

  const shouldPlay = useMemo(() => {
    if (typeof window === "undefined" || typeof window.sessionStorage === "undefined") {
      return false;
    }
    if (location.hash) return false;
    return window.sessionStorage.getItem(INTRO_SEEN_KEY) !== "1";
  }, [location.hash]);

  useEffect(() => {
    if (!shouldPlay) return;

    function end() {
      setDone(true);
      onComplete?.();
    }

    window.sessionStorage.setItem(INTRO_SEEN_KEY, "1");

    if (reduced) {
      const t = window.setTimeout(() => end(), REDUCED_END_MS);
      return () => window.clearTimeout(t);
    }

    const timers: number[] = [];
    timers.push(
      window.setTimeout(() => {
        const marker = markerRef.current;
        const wordEl = wordRef.current;
        if (!marker) return;
        const m = marker.getBoundingClientRect();
        const cx = m.left + m.width / 2;
        const cy = m.top + m.height / 2;
        const point = { x: cx, y: cy };
        originRef.current = point;
        if (wordEl) {
          const w = wordEl.getBoundingClientRect();
          setWordOrigin({ x: cx - w.left, y: cy - w.top });
        }
      }, MEASURE_MS),
      window.setTimeout(() => {
        setPhase("zoom");
        const dot = originRef.current;
        if (dot) onZoom?.(dot);
      }, HOLD_END_MS),
      window.setTimeout(() => setPhase("fade"), FADE_START_MS),
      window.setTimeout(() => end(), END_MS),
    );
    return () => timers.forEach((t) => window.clearTimeout(t));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shouldPlay, reduced]);

  if (!shouldPlay || done) return null;

  const zooming = phase === "zoom" || phase === "fade";
  const fading = phase === "fade";

  return (
    <div
      data-testid="intro-overlay"
      role="presentation"
      aria-hidden="true"
      className={cn("pointer-events-none fixed inset-0 z-[60] bg-paper-50", fading && "intro-bg-fade")}
      style={fading ? { animationDuration: `${FADE_MS}ms` } : undefined}
    >
      <div className="absolute inset-0 grid place-items-center">
        <div
          ref={wordRef}
          className={cn(
            "relative select-none font-serif text-[13vw] font-medium leading-none tracking-[0.04em] text-ink-950 sm:text-[9vw] md:text-[7vw]",
            reduced ? "intro-reduced-word" : "intro-write",
          )}
          style={
            wordOrigin && zooming
              ? {
                  transformOrigin: `${wordOrigin.x}px ${wordOrigin.y}px`,
                  transform: `scale(${WORD_ZOOM_SCALE})`,
                  opacity: 0,
                  transition: `transform ${ZOOM_MS}ms cubic-bezier(0.4, 0, 0.2, 1), opacity 850ms ease-in 350ms`,
                  willChange: "transform, opacity",
                }
              : undefined
          }
        >
          VER
          <span className="relative inline-block">
            I
            <span
              ref={markerRef}
              aria-hidden
              className={cn(
                "absolute -top-[0.44em] left-1/2 block rounded-full border-[1.5px] border-signal-600",
                reduced ? "-translate-x-1/2" : "intro-dot-in",
              )}
              style={{ width: "0.13em", height: "0.13em" }}
            />
          </span>
          TY
        </div>
      </div>
    </div>
  );
}