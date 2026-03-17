import { useEffect, useState } from "react";
import { useMotionValue, useSpring } from "framer-motion";

export function useSpringNumber(value: number) {
  const motionValue = useMotionValue(0);
  const spring = useSpring(motionValue, { stiffness: 120, damping: 20 });
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    motionValue.set(value);
  }, [value, motionValue]);

  useEffect(() => {
    const unsubscribe = spring.on("change", (latest) => {
      setDisplay(latest);
    });
    return () => unsubscribe();
  }, [spring]);

  return display;
}
