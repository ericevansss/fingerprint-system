import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import Qt.labs.platform 1.1

ApplicationWindow {
    id: window
    visible: true
    width: 1440
    height: 860
    title: "指纹识别分析系统"
    color: "#0b0f19"

    property real gridOffset: 0
    property string selectedFile: ""

    Timer {
        interval: 20
        running: true
        repeat: true
        onTriggered: {
            gridOffset = (gridOffset + 0.35) % 48
            gridCanvas.requestPaint()
            glowCanvas.requestPaint()
        }
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0b0f19" }
            GradientStop { position: 0.55; color: "#111827" }
            GradientStop { position: 1.0; color: "#0f172a" }
        }
    }

    Canvas {
        id: gridCanvas
        anchors.fill: parent
        opacity: 0.045
        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            ctx.strokeStyle = "rgba(255, 255, 255, 0.9)"
            ctx.lineWidth = 1
            var step = 48
            var offset = gridOffset
            for (var x = -step; x < width + step; x += step) {
                ctx.beginPath()
                ctx.moveTo(x + offset, 0)
                ctx.lineTo(x + offset, height)
                ctx.stroke()
            }
            for (var y = -step; y < height + step; y += step) {
                ctx.beginPath()
                ctx.moveTo(0, y + offset)
                ctx.lineTo(width, y + offset)
                ctx.stroke()
            }
        }
    }

    Canvas {
        id: glowCanvas
        anchors.fill: parent
        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            if (!uploadCard) {
                return
            }
            var cx = uploadCard.x + uploadCard.width / 2
            var cy = uploadCard.y + uploadCard.height / 2
            var radius = Math.max(uploadCard.width, uploadCard.height) * 1.2
            var gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius)
            gradient.addColorStop(0, "rgba(79, 70, 229, 0.28)")
            gradient.addColorStop(0.5, "rgba(79, 70, 229, 0.12)")
            gradient.addColorStop(1, "rgba(79, 70, 229, 0)")
            ctx.fillStyle = gradient
            ctx.fillRect(0, 0, width, height)
        }
    }

    Row {
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: 28
        spacing: 8
        z: 3

        Rectangle {
            width: 10
            height: 10
            radius: 5
            color: "#22c55e"
        }
        Text {
            text: "AI 引擎就绪"
            color: "#cbd5f5"
            font.pixelSize: 12
            font.family: "Inter"
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 36
        spacing: 28

        RowLayout {
            Layout.fillWidth: true
            spacing: 32

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 12

                Text {
                    text: "指纹视觉实验室"
                    font.pixelSize: 48
                    font.weight: Font.DemiBold
                    font.family: "Inter"
                    color: "#eef2ff"
                }
                Text {
                    text: "融合深度学习与传统算法的指纹识别与脊线分析平台"
                    font.pixelSize: 16
                    font.family: "Inter"
                    color: "#9aa4c5"
                    wrapMode: Text.WordWrap
                }
            }

            Item {
                Layout.preferredWidth: 420
                Layout.fillHeight: true

                Rectangle {
                    id: uploadShadow
                    anchors.fill: uploadCard
                    anchors.margins: -8
                    radius: 20
                    color: "#000000"
                    opacity: 0.35
                }

                Rectangle {
                    id: uploadCard
                    anchors.fill: parent
                    radius: 16
                    color: Qt.rgba(1, 1, 1, 0.04)
                    border.color: Qt.rgba(1, 1, 1, 0.08)
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 22
                        spacing: 16

                        Text {
                            text: "上传指纹图像"
                            color: "#cbd5f5"
                            font.pixelSize: 14
                            font.family: "Inter"
                        }

                        GradientButton {
                            text: selectedFile === "" ? "选择图像" : "重新选择"
                            Layout.fillWidth: true
                            onClicked: fileDialog.open()
                        }

                        Text {
                            text: selectedFile === "" ? "未选择文件" : ("已选择：" + selectedFile)
                            color: "#9aa4c5"
                            font.pixelSize: 12
                            font.family: "Inter"
                            elide: Text.ElideMiddle
                        }

                        ActionButton {
                            text: backend.loading ? "分析中..." : "开始分析"
                            Layout.fillWidth: true
                            enabled: !backend.loading && selectedFile !== ""
                            onClicked: backend.analyze(selectedFile)
                        }

                        Text {
                            text: backend.status
                            color: backend.loading ? "#22d3ee" : "#cbd5f5"
                            font.pixelSize: 12
                            font.family: "Inter"
                            wrapMode: Text.WordWrap
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: Qt.rgba(1, 1, 1, 0.08)
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 2
                            rowSpacing: 14
                            columnSpacing: 18

                            MetricItem { label: "类型"; value: backend.fingerprintType }
                            MetricItem { label: "置信度"; value: backend.confidence === "--" ? "--" : (backend.confidence + "%") }
                            MetricItem { label: "脊线数量"; value: backend.ridgeCount }
                            MetricItem { label: "脊线密度"; value: backend.ridgeDensity }
                            MetricItem { label: "处理时间"; value: backend.processingTime }
                        }
                    }
                }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: 2
            rowSpacing: 24
            columnSpacing: 24

            ImageCard {
                title: "Original · 原始指纹"
                source: selectedFile
                scanning: backend.loading
            }

            ImageCard {
                title: "Enhanced + Minutiae · 增强 + 细节点"
                source: backend.enhancedImage
                minutiaePoints: backend.minutiaePoints
                scanning: backend.loading
            }

            ImageCard {
                title: "Skeleton · 脊线骨架"
                source: backend.skeletonImage
            }

            ImageCard {
                title: "Binary Map · 脊线二值图"
                source: backend.ridgeMapImage
            }
        }
    }

    FileDialog {
        id: fileDialog
        title: "选择指纹图像"
        fileMode: FileDialog.OpenFile
        nameFilters: ["图像文件 (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)"]
        onAccepted: {
            if (fileDialog.file) {
                selectedFile = fileDialog.file.toString()
            } else {
                selectedFile = ""
            }
        }
    }

    component MetricItem: ColumnLayout {
        property string label: ""
        property string value: "--"
        spacing: 6

        Text {
            text: label
            color: "#9aa4c5"
            font.pixelSize: 12
            font.family: "Inter"
        }
        Text {
            text: value
            color: "#eef2ff"
            font.pixelSize: 18
            font.family: "Inter"
            font.weight: Font.Medium
        }
    }

    component GradientButton: Button {
        id: btn
        height: 44
        hoverEnabled: true
        font.pixelSize: 14
        font.weight: Font.Medium
        font.family: "Inter"

        background: Rectangle {
            radius: 999
            border.color: Qt.rgba(1, 1, 1, 0.08)
            border.width: 1
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#4f46e5" }
                GradientStop { position: 1.0; color: "#6366f1" }
            }
            scale: btn.hovered ? 1.02 : 1.0
            opacity: btn.enabled ? 1.0 : 0.6
            Behavior on scale { NumberAnimation { duration: 120 } }
        }

        contentItem: Text {
            text: btn.text
            color: "#eef2ff"
            font.pixelSize: 14
            font.weight: Font.Medium
            font.family: "Inter"
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }

    component ActionButton: Button {
        id: actionBtn
        height: 46
        hoverEnabled: true
        font.pixelSize: 14
        font.weight: Font.Medium
        font.family: "Inter"

        background: Rectangle {
            id: actionBg
            radius: 999
            border.color: Qt.rgba(1, 1, 1, 0.12)
            border.width: 1
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#4f46e5" }
                GradientStop { position: 1.0; color: "#6366f1" }
            }
            opacity: actionBtn.enabled ? 1.0 : 0.6
        }

        contentItem: Text {
            text: actionBtn.text
            color: "#eef2ff"
            font.pixelSize: 14
            font.weight: Font.Medium
            font.family: "Inter"
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }

        Rectangle {
            id: glow
            anchors.fill: parent
            radius: 999
            color: "#22d3ee"
            opacity: actionBtn.hovered ? 0.12 : 0.0
            Behavior on opacity { NumberAnimation { duration: 160 } }
        }

        Rectangle {
            id: ripple
            width: 0
            height: 0
            radius: width / 2
            anchors.centerIn: parent
            color: Qt.rgba(1, 1, 1, 0.18)
            opacity: 0
        }

        onPressed: {
            ripple.width = 0
            ripple.height = 0
            ripple.opacity = 0.45
            rippleAnim.restart()
        }

        SequentialAnimation {
            id: rippleAnim
            ParallelAnimation {
                NumberAnimation { target: ripple; property: "width"; to: 220; duration: 320 }
                NumberAnimation { target: ripple; property: "height"; to: 220; duration: 320 }
                NumberAnimation { target: ripple; property: "opacity"; to: 0; duration: 320 }
            }
        }
    }

    component ImageCard: Rectangle {
        id: card
        property string title: ""
        property string source: ""
        property var minutiaePoints: []
        property bool scanning: false
        property bool hovered: false

        radius: 16
        color: Qt.rgba(1, 1, 1, 0.03)
        border.color: hovered ? Qt.rgba(0.31, 0.27, 0.9, 0.45) : Qt.rgba(1, 1, 1, 0.06)
        border.width: 1
        Layout.fillWidth: true
        Layout.fillHeight: true
        scale: hovered ? 1.01 : 1.0
        Behavior on scale { NumberAnimation { duration: 140 } }
        Behavior on border.color { ColorAnimation { duration: 160 } }

        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            onEntered: hovered = true
            onExited: hovered = false
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 12

            Text {
                text: title
                font.pixelSize: 13
                font.family: "Inter"
                color: "#cbd5f5"
            }

            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                Rectangle {
                    anchors.fill: parent
                    radius: 12
                    color: Qt.rgba(0.04, 0.05, 0.11, 0.6)
                }

                Image {
                    id: img
                    anchors.fill: parent
                    fillMode: Image.PreserveAspectFit
                    source: source
                    smooth: true
                    opacity: status === Image.Ready ? 1.0 : 0.0
                    Behavior on opacity { NumberAnimation { duration: 320 } }
                }

                Rectangle {
                    id: scanLine
                    width: parent.width
                    height: 6
                    y: 0
                    visible: scanning && source !== ""
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: Qt.rgba(0.13, 0.83, 0.93, 0.0) }
                        GradientStop { position: 0.5; color: Qt.rgba(0.13, 0.83, 0.93, 0.6) }
                        GradientStop { position: 1.0; color: Qt.rgba(0.13, 0.83, 0.93, 0.0) }
                    }
                    opacity: 0.9
                }

                NumberAnimation {
                    id: scanAnim
                    target: scanLine
                    property: "y"
                    from: 0
                    to: card.height
                    duration: 1400
                    loops: Animation.Infinite
                    running: scanning && source !== ""
                }

                Canvas {
                    id: overlayCanvas
                    anchors.fill: parent
                    onPaint: {
                        var ctx = getContext("2d")
                        ctx.clearRect(0, 0, width, height)
                        if (img.status !== Image.Ready || minutiaePoints.length === 0) {
                            return
                        }

                        var paintedWidth = img.paintedWidth
                        var paintedHeight = img.paintedHeight
                        var offsetX = (width - paintedWidth) / 2
                        var offsetY = (height - paintedHeight) / 2
                        var scaleX = paintedWidth / 256
                        var scaleY = paintedHeight / 256

                        ctx.fillStyle = "rgba(34, 211, 238, 0.95)"
                        ctx.strokeStyle = "rgba(15, 23, 42, 0.8)"
                        ctx.lineWidth = 1

                        for (var i = 0; i < minutiaePoints.length; i++) {
                            var pt = minutiaePoints[i]
                            var x = offsetX + pt.x * scaleX
                            var y = offsetY + pt.y * scaleY
                            ctx.beginPath()
                            ctx.arc(x, y, 3, 0, Math.PI * 2)
                            ctx.fill()
                            ctx.stroke()
                        }
                    }
                }

                Connections {
                    target: img
                    function onStatusChanged() { overlayCanvas.requestPaint() }
                    function onSourceChanged() { overlayCanvas.requestPaint() }
                }

            }
        }

        onMinutiaePointsChanged: overlayCanvas.requestPaint()
        onScanningChanged: {
            if (!scanning) {
                scanLine.y = 0
            }
        }
    }
}
