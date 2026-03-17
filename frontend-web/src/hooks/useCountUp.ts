import { useEffect, useRef, useState } from "react";

export function useCountUp(value: number, duration = 600): number {
  const [current, setCurrent] = useState(0);
  const previous = useRef(0);

  useEffect(() => {
    const start = performance.now();
    const from = previous.current;
    const diff = value - from;

    function tick(now: number) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCurrent(from + diff * eased);
      if (progress < 1) {
        requestAnimationFrame(tick);
      } else {
        previous.current = value;
      }
    }

    requestAnimationFrame(tick);
  }, [value, duration]);

  return current;
}
