import { motion } from "framer-motion";

interface OverlayPoint {
  x: number;
  y: number;
  kind: "ending" | "bifurcation";
}

interface ImageCardProps {
  title: string;
  image?: string;
  isLoading?: boolean;
  overlayPoints?: OverlayPoint[];
}

export default function ImageCard({ title, image, isLoading, overlayPoints }: ImageCardProps) {
  return (
    <motion.div
      whileHover={{ y: -4, boxShadow: "0 12px 30px rgba(93,95,239,0.18)" }}
      className="glass-card rounded-2xl p-4 transition-all card-shadow"
    >
      <div className="text-sm text-[var(--muted)] mb-2">{title}</div>
      <div className="relative rounded-xl image-frame overflow-hidden h-[200px] flex items-center justify-center">
        {image ? (
          <motion.img
            key={image}
            src={image}
            alt={title}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="h-full w-full object-contain"
          />
        ) : (
          <div className="h-full w-full flex flex-col items-center justify-center text-xs text-[var(--muted)] placeholder-gradient">
            <div className="text-sm">等待分析结果</div>
            <div className="mt-1 text-[11px] opacity-70">高保真可视化区域</div>
          </div>
        )}

        {overlayPoints && overlayPoints.length > 0 && (
          <svg
            className="absolute inset-0"
            viewBox="0 0 256 256"
            preserveAspectRatio="xMidYMid meet"
          >
            {overlayPoints.map((point, index) =>
              point.kind === "ending" ? (
                <circle
                  key={`ending-${index}`}
                  cx={point.x}
                  cy={point.y}
                  r={6}
                  fill="transparent"
                  stroke="#22c55e"
                  strokeWidth={2}
                />
              ) : (
                <circle
                  key={`bif-${index}`}
                  cx={point.x}
                  cy={point.y}
                  r={6}
                  fill="transparent"
                  stroke="#ef4444"
                  strokeWidth={2}
                />
              )
            )}
          </svg>
        )}

        {isLoading && (
          <div className="absolute inset-0">
            <div className="shimmer" />
            <motion.div
              className="absolute inset-x-0 h-10 bg-gradient-to-r from-transparent via-[#5D5FEF]/35 to-transparent"
              initial={{ y: 0 }}
              animate={{ y: [0, 170, 0] }}
              transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
            />
          </div>
        )}
      </div>
    </motion.div>
  );
}
