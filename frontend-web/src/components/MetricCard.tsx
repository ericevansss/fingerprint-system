import { motion } from "framer-motion";
import { useSpringNumber } from "../hooks/useSpringNumber";

interface MetricCardProps {
  label: string;
  value: number | string;
  suffix?: string;
}

export default function MetricCard({ label, value, suffix }: MetricCardProps) {
  const numericValue = typeof value === "number" ? value : NaN;
  const animated = useSpringNumber(Number.isNaN(numericValue) ? 0 : numericValue);

  const displayValue = Number.isNaN(numericValue)
    ? value
    : `${animated.toFixed(numericValue % 1 === 0 ? 0 : 2)}${suffix ?? ""}`;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="rounded-2xl border border-white/10 bg-white/5 px-3 py-2"
    >
      <div className="text-xs uppercase tracking-wide text-[var(--muted)]">{label}</div>
      <div className="mt-1 text-lg font-semibold">{displayValue}</div>
    </motion.div>
  );
}
