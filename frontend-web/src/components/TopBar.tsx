import { motion } from "framer-motion";

interface TopBarProps {
  theme: "dark" | "light";
  onToggle: () => void;
}

export default function TopBar({ theme, onToggle }: TopBarProps) {
  return (
    <div className="flex items-center justify-between h-16 px-8">
      <div className="flex items-center gap-3">
        <div className="h-9 w-9 rounded-xl bg-[var(--accent)]/90 flex items-center justify-center text-white font-semibold shadow-[0_8px_20px_rgba(93,95,239,0.35)]">
          FV
        </div>
        <span className="text-lg font-semibold">Fingerprint Vision Lab</span>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-sm">
          <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.6)]" />
          FingerNet Model Loaded
        </div>

        <motion.button
          whileTap={{ scale: 0.96 }}
          className="h-9 px-4 rounded-full border border-white/10 bg-white/5 text-xs"
          onClick={onToggle}
        >
          {theme === "dark" ? "Light" : "Dark"}
        </motion.button>

        <div className="h-9 w-9 rounded-full bg-white/10 border border-white/10 flex items-center justify-center text-xs">
          UX
        </div>
      </div>
    </div>
  );
}
