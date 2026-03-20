import { motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import Footer from "./components/Footer";
import ImageCard from "./components/ImageCard";
import LoaderOverlay from "./components/LoaderOverlay";
import MetricCard from "./components/MetricCard";
import TopBar from "./components/TopBar";
import UploadCard from "./components/UploadCard";

interface ApiResponse {
  fingerprint_type?: string;
  confidence?: number;
  ridge_count?: number;
  ridge_density?: number;
  processing_time_ms?: number;
  images?: {
    original?: string;
    enhanced?: string;
    skeleton?: string;
    binary?: string;
  };
  original_image?: string;
  enhanced_image?: string;
  skeleton_image?: string;
  ridge_map_image?: string;
  visualization_image?: string;
  processing_time?: string;
  minutiae_points?: { x: number; y: number; kind?: "ending" | "bifurcation" }[];
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";
const ANALYZE_URL = `${API_BASE}/api/analyze`;

function normalizeImageUrl(url?: string): string | undefined {
  if (!url) return undefined;
  if (url.startsWith("data:")) return url;
  if (url.startsWith("http")) return url;
  if (url.startsWith("/")) return `${API_BASE}${url}`;
  return url;
}

function base64ToDataUrl(value?: string): string | undefined {
  if (!value) return undefined;
  if (value.startsWith("data:")) return value;
  return `data:image/png;base64,${value}`;
}

export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("等待上传指纹图像");
  const [response, setResponse] = useState<ApiResponse | null>(null);
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const metrics = useMemo(() => {
    return {
      fingerprintType: response?.fingerprint_type || "--",
      confidence: response?.confidence ? response.confidence * 100 : NaN,
      ridgeCount: response?.ridge_count ?? NaN
    };
  }, [response]);

  const images = useMemo(() => {
    const imagesFromApi = response?.images || {};
    return {
      original:
        normalizeImageUrl(imagesFromApi.original) ||
        base64ToDataUrl(response?.visualization_image) ||
        base64ToDataUrl(response?.original_image) ||
        preview ||
        undefined,
      enhanced:
        normalizeImageUrl(imagesFromApi.enhanced) ||
        base64ToDataUrl(response?.enhanced_image),
      skeleton:
        normalizeImageUrl(imagesFromApi.skeleton) ||
        base64ToDataUrl(response?.skeleton_image),
      binary:
        normalizeImageUrl(imagesFromApi.binary) ||
        base64ToDataUrl(response?.ridge_map_image)
    };
  }, [response, preview]);

  const handleSelectFile = (selected: File) => {
    setFile(selected);
    setResponse(null);
    setStatus("已选择图像，可开始分析");
    const url = URL.createObjectURL(selected);
    setPreview(url);
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setLoading(true);
    setStatus("正在分析，请稍候...");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(ANALYZE_URL, {
        method: "POST",
        body: formData
      });

      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || "分析失败");
      }

      const data = (await res.json()) as ApiResponse;
      setResponse(data);
      setStatus("分析完成");
    } catch (error) {
      const message = error instanceof Error ? error.message : "分析失败";
      setStatus(`分析失败：${message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen relative overflow-hidden">
      <div className="absolute inset-0 background-grid" />
      <div className="absolute inset-0">
        <div className="absolute left-[22%] top-[220px] h-[360px] w-[360px] rounded-full bg-[#5D5FEF]/25 blur-[140px]" />
      </div>

      <div className="relative z-10">
        <TopBar
          theme={theme}
          onToggle={() => setTheme((prev) => (prev === "dark" ? "light" : "dark"))}
        />

        <motion.main
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="px-8 pb-24"
        >
          <div className="grid grid-cols-1 xl:grid-cols-[450px_1fr] gap-12">
            <section className="space-y-6">
              <div>
                <h1 className="text-4xl xl:text-5xl font-semibold">Fingerprint Vision Lab</h1>
                <p className="mt-3 text-base text-[var(--muted)] max-w-md">
                  A fingerprint recognition and ridge analysis platform powered by deep
                  learning and traditional algorithms.
                </p>
              </div>

              <div className="glass-card rounded-2xl px-5 py-4 text-sm">
                系统状态：<span className="text-emerald-400">FingerNet Model Loaded</span>
              </div>

              <UploadCard
                file={file}
                previewUrl={preview}
                isLoading={loading}
                statusText={status}
                onSelect={handleSelectFile}
                onAnalyze={handleAnalyze}
              />

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <MetricCard label="Type" value={metrics.fingerprintType} />
                <MetricCard
                  label="Confidence"
                  value={Number.isNaN(metrics.confidence) ? "--" : metrics.confidence}
                  suffix="%"
                />
                <MetricCard
                  label="Ridge Count"
                  value={Number.isNaN(metrics.ridgeCount) ? "--" : metrics.ridgeCount}
                />
              </div>
            </section>

            <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <ImageCard title="Core-Delta Ridge Analysis" image={images.original} />
              <ImageCard
                title="方向场"
                image={images.enhanced}
                isLoading={loading}
              />
              <ImageCard
                title="脊线二值图"
                image={images.binary}
                isLoading={loading}
              />
              <ImageCard
                title="脊线骨架"
                image={images.skeleton}
                isLoading={loading}
              />
            </section>
          </div>
        </motion.main>

        <Footer />
      </div>

      <LoaderOverlay visible={loading} />
    </div>
  );
}
