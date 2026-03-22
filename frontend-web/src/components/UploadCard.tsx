import { motion } from "framer-motion";
import { useCallback, useEffect, useRef } from "react";

interface UploadCardProps {
  file?: File | null;
  previewUrl?: string;
  isLoading: boolean;
  onSelect: (file: File) => void;
  onAnalyze: () => void;
}

export default function UploadCard({
  file,
  previewUrl,
  isLoading,
  onSelect,
  onAnalyze
}: UploadCardProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  const handleFile = useCallback(
    (fileList: FileList | null) => {
      if (!fileList || fileList.length === 0) return;
      onSelect(fileList[0]);
    },
    [onSelect]
  );

  useEffect(() => {
    const handleDrop = (event: DragEvent) => {
      event.preventDefault();
      handleFile(event.dataTransfer?.files ?? null);
    };

    const handleDragOver = (event: DragEvent) => {
      event.preventDefault();
    };

    window.addEventListener("drop", handleDrop);
    window.addEventListener("dragover", handleDragOver);

    return () => {
      window.removeEventListener("drop", handleDrop);
      window.removeEventListener("dragover", handleDragOver);
    };
  }, [handleFile]);

  return (
    <div className="glass-card rounded-2xl p-5 card-shadow">
      <div className="text-sm text-[var(--muted)] mb-4">上传指纹图像</div>

      <div className="relative rounded-2xl border border-dashed border-white/10 bg-white/5 p-5 text-center">
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(event) => handleFile(event.target.files)}
        />

        <div className="text-sm text-[var(--muted)]">拖拽图像到这里</div>
        <div className="text-xs text-slate-500 mt-1">支持 PNG / JPG / TIFF</div>

        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.97 }}
          className="mt-4 h-11 px-6 rounded-full btn-ghost text-sm font-medium"
          onClick={() => inputRef.current?.click()}
        >
          选择图像
        </motion.button>

        <div className="mt-4 rounded-2xl border border-white/10 bg-black/30 p-3">
          <div className="relative h-28 w-full overflow-hidden rounded-xl bg-black/40 flex items-center justify-center">
            {previewUrl ? (
              <img
                src={previewUrl}
                alt="preview"
                className="h-full w-full object-contain image-fade"
              />
            ) : (
              <div className="text-xs text-[var(--muted)]">未选择图像</div>
            )}
            {isLoading && (
              <motion.div
                className="absolute inset-x-0 h-10 bg-gradient-to-r from-transparent via-[#5D5FEF]/40 to-transparent"
                initial={{ y: 0 }}
                animate={{ y: [0, 120, 0] }}
                transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
              />
            )}
          </div>
          <div className="mt-2 text-xs text-[var(--muted)] truncate">
            {file?.name || "请选择指纹图像"}
          </div>
        </div>
      </div>

      <motion.button
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.97 }}
        className={`mt-5 h-11 w-full rounded-full btn-action text-sm font-medium flex items-center justify-center gap-2 ${
          isLoading ? "loading pulse-glow" : ""
        }`}
        onClick={onAnalyze}
        disabled={!file || isLoading}
      >
        {isLoading && (
          <span className="h-4 w-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
        )}
        {isLoading ? "处理中" : "开始分析"}
      </motion.button>

    </div>
  );
}
