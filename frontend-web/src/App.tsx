import { motion } from "framer-motion";
import { useEffect, useMemo, useRef, useState } from "react";
import Footer from "./components/Footer";
import LoaderOverlay from "./components/LoaderOverlay";
import MetricCard from "./components/MetricCard";
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

const API_BASE = (import.meta as { env?: Record<string, string> }).env?.VITE_API_BASE_URL || "http://127.0.0.1:8000";
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

function resolveImage(value?: string): string | undefined {
  if (!value) return undefined;
  if (value.startsWith("data:") || value.startsWith("http") || value.startsWith("/")) {
    return normalizeImageUrl(value);
  }
  return base64ToDataUrl(value);
}

export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("等待上传指纹图像");
  const [response, setResponse] = useState<ApiResponse | null>(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const statusTimerRef = useRef<number | null>(null);
  const statusStages = [
    "图像增强中",
    "提取方向场",
    "骨架细化中",
    "CNN分类中"
  ];
  const statusIntervalMs = 1300;

  useEffect(() => {
    document.documentElement.dataset.theme = "dark";
  }, []);

  useEffect(() => {
    setActiveIndex(0);
  }, [response, preview]);

  const metrics = useMemo(() => {
    return {
      fingerprintType: response?.fingerprint_type || "--",
      confidence: response?.confidence ? response.confidence * 100 : NaN,
      ridgeCount: response?.ridge_count ?? NaN
    };
  }, [response]);

  const confidenceValue = useMemo(() => {
    if (Number.isNaN(metrics.confidence)) return 0;
    return Math.min(100, Math.max(0, metrics.confidence));
  }, [metrics.confidence]);


  const images = useMemo(() => {
    const imagesFromApi = (response?.images || {}) as Record<string, string | undefined>;
    const original =
      resolveImage(imagesFromApi.visualization) ||
      resolveImage(imagesFromApi.visualization_image) ||
      resolveImage(imagesFromApi.original) ||
      resolveImage(imagesFromApi.original_image) ||
      base64ToDataUrl(response?.visualization_image) ||
      base64ToDataUrl(response?.original_image) ||
      preview ||
      undefined;
    const enhanced =
      resolveImage(imagesFromApi.enhanced) ||
      resolveImage(imagesFromApi.enhanced_image) ||
      base64ToDataUrl(response?.enhanced_image);
    const skeleton =
      resolveImage(imagesFromApi.skeleton) ||
      resolveImage(imagesFromApi.skeleton_image) ||
      base64ToDataUrl(response?.skeleton_image);
    const binary =
      resolveImage(imagesFromApi.binary) ||
      resolveImage(imagesFromApi.ridge_map_image) ||
      base64ToDataUrl(response?.ridge_map_image);
    return { original, enhanced, skeleton, binary };
  }, [response, preview]);

  const pipelineSteps = useMemo(() => {
    return [
      {
        id: "orientation",
        title: "方向场",
        imgSrc: images.enhanced,
        description: "基于梯度的块级方向场估计",
        metrics: {
          time: response?.processing_time || "--",
          method: "Block 16×16"
        }
      },
      {
        id: "binary",
        title: "脊线二值图",
        imgSrc: images.binary,
        description: "阈值化与形态学优化后的脊线区域",
        metrics: {
          time: response?.processing_time || "--",
          method: "Binary Map"
        }
      },
      {
        id: "skeleton",
        title: "脊线骨架",
        imgSrc: images.skeleton,
        description: "细化后的脊线骨架 用于细节点提取",
        metrics: {
          time: response?.processing_time || "--",
          nodes: response?.minutiae_points?.length
            ? `${response.minutiae_points.length} points`
            : "--"
        }
      },
      {
        id: "ridge_count",
        title: "核心-三角脊线测算",
        imgSrc: images.original,
        description: "连线统计核心与三角区域的脊线交叉数",
        metrics: {
          count: response?.ridge_count ?? "--",
          confidence: response?.confidence
            ? `${(response.confidence * 100).toFixed(2)}%`
            : "--"
        }
      }
    ];
  }, [images, response]);

  const activeStep = pipelineSteps[activeIndex] || pipelineSteps[0];
  const metricLabels: Record<string, string> = {
    time: "时间",
    method: "方法",
    nodes: "细节点",
    count: "脊线数",
    confidence: "置信度"
  };

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
    setStatus(statusStages[0]);
    if (statusTimerRef.current) {
      window.clearInterval(statusTimerRef.current);
    }
    let stage = 0;
    statusTimerRef.current = window.setInterval(() => {
      stage += 1;
      if (stage >= statusStages.length) {
        if (statusTimerRef.current) {
          window.clearInterval(statusTimerRef.current);
          statusTimerRef.current = null;
        }
        setStatus(statusStages[statusStages.length - 1]);
        return;
      }
      setStatus(statusStages[stage]);
    }, statusIntervalMs);

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
    } catch (error) {
      const message = error instanceof Error ? error.message : "分析失败";
      setStatus(`分析失败：${message}`);
    } finally {
      setLoading(false);
      if (statusTimerRef.current) {
        window.clearInterval(statusTimerRef.current);
        statusTimerRef.current = null;
      }
    }
  };

  return (
    <div className="min-h-screen relative overflow-hidden">
      <div className="absolute inset-0 background-grid" />
      <div className="absolute inset-0">
        <div className="absolute left-[22%] top-[220px] h-[360px] w-[360px] rounded-full bg-[#5D5FEF]/25 blur-[140px]" />
      </div>

      <div className="relative z-10">
        <motion.main
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="px-6 pt-4 pb-4 xl:h-[calc(100vh-48px)]"
        >
          <div className="grid grid-cols-1 xl:grid-cols-[420px_1fr] gap-6 h-full">
            <section className="space-y-4 pt-12 pb-1">
              <div>
                <h1 className="hero-title text-3xl xl:text-[3.1rem] font-semibold flex items-start gap-3">
                  <div className="flex flex-col leading-[0.95]">
                    <span className="block">Fingerprint</span>
                    <span className="block ml-3 mt-1">Vision Lab</span>
                  </div>
                  <span className="text-6xl xl:text-7xl leading-none rotate-[24deg] -translate-y-1">🫆</span>
                </h1>
                <p className="mt-3 text-base text-[var(--muted)] max-w-md">
                  A fingerprint recognition and ridge analysis platform powered by deep
                  learning and traditional algorithms
                </p>
              </div>

              <UploadCard
                file={file}
                previewUrl={preview}
                isLoading={loading}
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

              <div className="glass-card rounded-2xl px-5 py-4 card-shadow space-y-3">
                <div className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">
                  Classification Confidence
                </div>
                <div className="text-base font-semibold">
                  {metrics.fingerprintType}{" "}
                  <span className="text-[var(--muted)]">
                    {Number.isNaN(metrics.confidence) ? "--" : `${metrics.confidence.toFixed(2)}%`}
                  </span>
                </div>
                <div className="confidence-bar">
                  <span style={{ width: `${confidenceValue}%` }} />
                </div>
              </div>

            </section>

            <section className="right-panel h-full min-h-0">
              <div className="main-view">
                <div className="main-card">
                  <div className="main-image">
                    {activeStep?.imgSrc ? (
                      <motion.img
                        key={activeStep.imgSrc}
                        src={activeStep.imgSrc}
                        alt={activeStep.title}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ duration: 0.3 }}
                        className="main-media"
                      />
                    ) : (
                      <div className="h-full w-full flex items-center justify-center text-xs text-[var(--muted)]">
                        等待分析结果
                      </div>
                    )}
                  </div>
                </div>

                <div className="main-info">
                  <div>
                    <div className="text-sm uppercase tracking-[0.16em] text-[var(--muted)]">
                      {activeStep?.title}
                    </div>
                    <div className="text-xl xl:text-2xl font-semibold text-[var(--text)]/95 leading-snug">
                      {activeStep?.description}
                    </div>
                  </div>
                  <div className="main-metrics">
                    {activeStep?.metrics &&
                      Object.entries(activeStep.metrics).map(([key, value]) => (
                        <div key={key} className="flex items-center gap-2 text-sm">
                          <span className="uppercase tracking-[0.1em] text-[var(--muted)]">
                            {metricLabels[key] || key}
                          </span>
                          <span className="text-[var(--text)] font-semibold">{value as string}</span>
                        </div>
                      ))}
                  </div>
                </div>
              </div>

              <div className="thumbs-column">
                {pipelineSteps.map((step, index) => {
                  const isActive = index === activeIndex;
                  return (
                    <button
                      type="button"
                      key={step.id}
                      onClick={() => setActiveIndex(index)}
                      className={`thumbnail-card transition-all ${
                        isActive ? "thumbnail-active" : "thumbnail-inactive"
                      }`}
                    >
                      <div className="h-full w-full thumbnail-card-inner">
                        <div className="thumbnail-media-wrap">
                          {step.imgSrc ? (
                            <img
                              src={step.imgSrc}
                              alt={step.title}
                              className="thumbnail-image"
                            />
                          ) : (
                            <div className="text-[10px] text-[var(--muted)]">等待图像</div>
                          )}
                        </div>
                        <div className="thumbnail-title text-xs text-[#a0aec0]">
                          {step.title}
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </section>
          </div>
        </motion.main>

        <Footer />
      </div>

      <LoaderOverlay visible={loading} text={status} />
    </div>
  );
}
