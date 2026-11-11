import { useEffect, useRef, useState } from "react";

/**
 * Counts down from `seconds` while `running` is true, then calls `onDone` once.
 * Restarts whenever `key` changes. Uses a deadline rather than counting ticks,
 * so it stays accurate when the tab is in the background.
 */
export function useCountdown(seconds: number, running: boolean, key: unknown, onDone: () => void): number {
  const [remaining, setRemaining] = useState(seconds);
  const onDoneRef = useRef(onDone);
  onDoneRef.current = onDone;

  useEffect(() => {
    setRemaining(seconds);
    if (!running) return;
    const deadline = Date.now() + seconds * 1000;
    let done = false;
    const tick = () => {
      const left = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
      setRemaining(left);
      if (left === 0 && !done) {
        done = true;
        window.clearInterval(timer);
        onDoneRef.current();
      }
    };
    const timer = window.setInterval(tick, 250);
    return () => window.clearInterval(timer);
  }, [seconds, running, key]);

  return remaining;
}

export function formatClock(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}
