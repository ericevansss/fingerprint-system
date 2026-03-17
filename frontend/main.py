"""Qt frontend for the fingerprint system."""
from __future__ import annotations

import base64
import json
import threading
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

API_URL = "http://127.0.0.1:8000/analyze?return_images=true"


@dataclass
class MinutiaePoint:
    x: int
    y: int
    score: float
    angle: float


class Backend(QObject):
    statusChanged = Signal()
    loadingChanged = Signal()
    resultChanged = Signal()
    imagesChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._status = "等待上传指纹图像"
        self._loading = False
        self._fingerprint_type = "--"
        self._confidence = "--"
        self._ridge_count = "--"
        self._ridge_density = "--"
        self._processing_time = "--"
        self._minutiae_points: List[dict] = []
        self._enhanced_image = ""
        self._skeleton_image = ""
        self._ridge_map_image = ""

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    @Property(bool, notify=loadingChanged)
    def loading(self) -> bool:
        return self._loading

    @Property(str, notify=resultChanged)
    def fingerprintType(self) -> str:
        return self._fingerprint_type

    @Property(str, notify=resultChanged)
    def confidence(self) -> str:
        return self._confidence

    @Property(str, notify=resultChanged)
    def ridgeCount(self) -> str:
        return self._ridge_count

    @Property(str, notify=resultChanged)
    def ridgeDensity(self) -> str:
        return self._ridge_density

    @Property(str, notify=resultChanged)
    def processingTime(self) -> str:
        return self._processing_time

    @Property("QVariantList", notify=resultChanged)
    def minutiaePoints(self) -> List[dict]:
        return self._minutiae_points

    @Property(str, notify=imagesChanged)
    def enhancedImage(self) -> str:
        return self._enhanced_image

    @Property(str, notify=imagesChanged)
    def skeletonImage(self) -> str:
        return self._skeleton_image

    @Property(str, notify=imagesChanged)
    def ridgeMapImage(self) -> str:
        return self._ridge_map_image

    @Slot(str)
    def analyze(self, file_path: str) -> None:
        """Run fingerprint analysis in a background thread."""
        if not file_path:
            self._status = "请先选择指纹图像"
            self.statusChanged.emit()
            return

        if file_path.startswith("file://"):
            file_path = QUrl(file_path).toLocalFile()

        if not Path(file_path).exists():
            self._status = "未找到图像文件"
            self.statusChanged.emit()
            return

        if self._loading:
            return

        self._loading = True
        self.loadingChanged.emit()
        self._status = "分析中，请稍候..."
        self.statusChanged.emit()

        thread = threading.Thread(target=self._run_request, args=(file_path,), daemon=True)
        thread.start()

    def _run_request(self, file_path: str) -> None:
        try:
            with open(file_path, "rb") as file:
                boundary = "----fingerprint-boundary"
                body = (
                    f"--{boundary}\r\n"
                    f"Content-Disposition: form-data; name=\"file\"; filename=\"{Path(file_path).name}\"\r\n"
                    "Content-Type: application/octet-stream\r\n\r\n"
                ).encode("utf-8") + file.read() + f"\r\n--{boundary}--\r\n".encode("utf-8")

            request = urllib.request.Request(
                API_URL,
                data=body,
                headers={
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                },
                method="POST",
            )

            with urllib.request.urlopen(request, timeout=60) as response:
                payload = response.read()

            data = json.loads(payload.decode("utf-8"))
            self._apply_result(data)
        except Exception as exc:
            self._status = f"分析失败：{exc}"
            self._loading = False
            self.statusChanged.emit()
            self.loadingChanged.emit()

    def _apply_result(self, data: dict) -> None:
        self._fingerprint_type = data.get("fingerprint_type", "--")
        confidence = data.get("confidence")
        self._confidence = f"{confidence:.2f}" if isinstance(confidence, (int, float)) else "--"
        self._ridge_count = str(data.get("ridge_count", "--"))
        density = data.get("ridge_density")
        self._ridge_density = f"{density:.3f}" if isinstance(density, (int, float)) else "--"
        self._processing_time = data.get("processing_time", "--")

        self._minutiae_points = data.get("minutiae_points", [])

        self._enhanced_image = _as_data_url(data.get("enhanced_image"))
        self._skeleton_image = _as_data_url(data.get("skeleton_image"))
        self._ridge_map_image = _as_data_url(data.get("ridge_map_image"))

        self._status = "分析完成"
        self._loading = False

        self.statusChanged.emit()
        self.loadingChanged.emit()
        self.resultChanged.emit()
        self.imagesChanged.emit()


def _as_data_url(base64_str: Optional[str]) -> str:
    if not base64_str:
        return ""
    return f"data:image/png;base64,{base64_str}"


def main() -> None:
    app = QGuiApplication([])
    engine = QQmlApplicationEngine()

    backend = Backend()
    engine.rootContext().setContextProperty("backend", backend)

    qml_path = Path(__file__).resolve().parent / "ui" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))

    if not engine.rootObjects():
        raise RuntimeError("无法加载QML界面")

    app.exec()


if __name__ == "__main__":
    main()
