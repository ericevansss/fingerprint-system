import { motion } from "framer-motion";

export default function LoaderOverlay({ visible }: { visible: boolean }) {
  if (!visible) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center"
    >
      <div className="glass-card rounded-2xl px-8 py-6 text-center">
        <div className="mb-3 text-sm text-slate-300">正在分析指纹...</div>
        <div className="h-2 w-52 overflow-hidden rounded-full bg-white/5">
          <motion.div
            className="h-full bg-gradient-to-r from-indigo-600 to-indigo-500"
            animate={{ x: ["-100%", "100%"] }}
            transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
          />
        </div>
      </div>
    </motion.div>
  );
}
