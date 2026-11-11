const PATTERN = [0.3, 0.55, 0.4, 0.8, 0.5, 1, 0.65, 0.35, 0.9, 0.45, 0.7, 0.3, 0.95, 0.55, 0.4, 0.75, 0.5, 0.85, 0.35, 0.6, 0.45, 0.25];

/** Decorative animated waveform (landing page demo). */
export function AnimatedWaveform({ bars = 22, className = "" }: { bars?: number; className?: string }) {
  return (
    <div className={`flex h-12 items-center justify-center gap-[3px] ${className}`} aria-hidden="true">
      {Array.from({ length: bars }, (_, i) => (
        <span
          key={i}
          className="wave-bar w-[3px] rounded-full bg-fg"
          style={{
            height: `${PATTERN[i % PATTERN.length] * 100}%`,
            animationDelay: `${(i * 87) % 900}ms`,
            animationDuration: `${900 + ((i * 131) % 600)}ms`,
          }}
        />
      ))}
    </div>
  );
}

/** Live microphone level meter: bars follow the recent input levels. */
export function LevelMeter({ levels, active }: { levels: number[]; active: boolean }) {
  return (
    <div className="flex h-10 items-center justify-center gap-[4px]" aria-hidden="true">
      {levels.map((level, i) => {
        const height = active ? Math.max(0.12, Math.min(1, level)) : i % 5 === 2 ? 0.28 : 0.12;
        return (
          <span
            key={i}
            className="w-[3px] rounded-full bg-fg transition-[height] duration-100 ease-out"
            style={{ height: `${height * 100}%`, opacity: active ? 1 : 0.85 }}
          />
        );
      })}
    </div>
  );
}
