import sys, time, threading, queue, random
import numpy as np
import mss
import ctypes

from PySide6.QtWidgets import QApplication, QWidget,QPushButton,QHBoxLayout,QLabel
from PySide6.QtCore import Qt, QRect, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QShortcut,QKeySequence
import win32gui, win32process,psutil

userScreen = ctypes.windll.user32
try:
    DPI_AWARENESS_CONTEXT_PER_MONITOR = -4  # constant value
    userScreen.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR)
except Exception:
    userScreen.SetProcessDPIAware()

def find_maps_window(title_contains="Google Maps"):
    found=[]
    def wind_handl(h,_):
        if not win32gui.IsWindowVisible(h):
            return
        title=win32gui.GetWindowText(h)
        if title_contains.lower() in title.lower():
            _, pid = win32process.GetWindowThreadProcessId(h)
            try:
                pname = psutil.Process(pid).name().lower()
            except psutil.NoSuchProcess:
                return
            if "chrome" in pname or "msedge" in pname:
                found.append(h)
    win32gui.EnumWindows(wind_handl, None)
    if not found: return None,None

    hwnd = found[0]
    l,t,r,b=win32gui.GetWindowRect(hwnd)
    rect={"left":l+8, "top":t+50, "width":(r-l)-16, "height":(b-t)-88}
    return hwnd,rect


def rect_to_qt_logical(rect_physical: dict, hwnd) -> dict:
    dpi = ctypes.windll.user32.GetDpiForWindow(hwnd)
    scale = dpi / 96.0 if dpi else 1.0
    return {
        "left":   int(rect_physical["left"]   / scale),
        "top":    int(rect_physical["top"]    / scale),
        "width":  int(rect_physical["width"]  / scale),
        "height": int(rect_physical["height"] / scale),
    }

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except Exception:
    YOLO_AVAILABLE = False

#===Advice Giver===
class SafetyAdvisor:
    VEHICLES = {"car","truck","bus","motorbike","bicycle"}
    PEOPLE   = {"person"}
    ANIMALS  = {"dog","cat","horse","cow","sheep","bird"}
    TREES    = {"tree"}

    def make_text(self, labels:set[str]) -> str:
        tips = []
        tips.append("Emergency? Call 112 immediately. Stay at a safe distance. Lave the area imediately!")

        if labels & self.PEOPLE:
            tips.append("Warn others and move away from smoke/heat. Do not enter any building or vehicle that may be on fire.")

        if labels & self.VEHICLES:
            tips.append("Vehicle fires: keep well back. Do not open the hood. Use an ABC extinguisher only if the fire is very small and your escape is clear.")

        if labels & self.TREES:
            tips.append("Vegetation: avoid sparks/ignition sources. If you see smoke or open flame, back away upwind and report it.")

        if labels & self.ANIMALS:
            tips.append("Do not attempt rescues through smoke/flames; tell responders about trapped animals.")

        unique = []
        seen = set()
        for t in tips:
            if t not in seen:
                unique.append(t)
                seen.add(t)
        return "• " + "\n• ".join(unique)

class AdvicePanel(QWidget):
    def __init__(self, anchor_rect_logical: dict):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # Mouse click-through
        try:
            import win32con, win32gui
            hwnd = int(self.winId())
            ex = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            ex |= win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex)
        except Exception:
            pass

        self.label = QLabel(self)
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.NoTextInteraction)
        self.label.setStyleSheet("""
            QLabel {
                background-color: rgba(0,0,0,160);
                color: white;
                padding: 10px;
                border-radius: 10px;
                font-family: Segoe UI;
                font-size: 11pt;
            }
        """)
        self.label.setFixedWidth(360)
        self.label.setText("Analyzing scene…")

        self._anchor = anchor_rect_logical
        self.label.adjustSize()
        self.resize(self.label.size())
        self._reposition()

        self._last_labels: set[str] = set()
        self._advisor = SafetyAdvisor()
        self._last_update_ms = 0

        # periodic refresh (every_30s)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(30_000)
        self._refresh_timer.timeout.connect(self._periodic_refresh)
        self._refresh_timer.start()

        self.show()

    def _reposition(self):
        margin = 12
        x = self._anchor["left"] + self._anchor["width"] - self.width() - margin
        y = self._anchor["top"] + margin
        self.move(x, y)

    def update_anchor(self, anchor_rect_logical: dict):
        self._anchor = anchor_rect_logical
        self._reposition()

    def set_labels(self, labels:set[str]):
        if labels != self._last_labels:
            self._last_labels = set(labels)
            self._apply_advice_text()

    def _periodic_refresh(self):
        self._apply_advice_text()

    def _apply_advice_text(self):
        text = self._advisor.make_text(self._last_labels)
        self.label.setText(text)
        self.label.adjustSize()
        self.resize(self.label.size())
        self._reposition()
#===Control Bar===
class ControlBar(QWidget):
    def __init__(self, anchor_rect_logical: dict, on_close):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        btn = QPushButton("× Close")
        btn.setFixedHeight(28)
        btn.clicked.connect(on_close)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.addWidget(btn)

        self._anchor = anchor_rect_logical
        self.show()
        self.adjustSize()
        self._reposition()

    def _reposition(self):
        x = self._anchor["left"] + self._anchor["width"] - self.width() - 12
        y = self._anchor["top"] + 12
        self.move(x, y)

    def update_anchor(self, anchor_rect_logical: dict):
        self._anchor = anchor_rect_logical
        self._reposition()
#===Overlay Window===
class Overlay(QWidget):
    def __init__(self, rect_px, on_close):
        super().__init__()
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        # Position/size overlay to exactly cover the capture rect
        self.setGeometry(rect_px["left"], rect_px["top"], rect_px["width"], rect_px["height"])

        self._make_click_through()

        self.boxes = []

        self.pen = QPen(QColor(255, 0, 0, 255))
        self.pen.setWidth(2)
        self.font = QFont("Segoe UI", 10)

        self.on_close = on_close  # store callback

        #QShortcut(QKeySequence("q"), self, activated=self._quit)

        self.show()

    def _make_click_through(self):
        try:
            import win32con, win32gui
            hwnd = int(self.winId())
            ex = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            ex |= win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex)
        except Exception as e:
            print("Warning: could not set click-through:", e)

    def update_boxes(self, boxes):
        self.boxes = boxes
        self.update()

    def paintEvent(self, event):
        if not self.boxes:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(self.pen)
        p.setFont(self.font)

        for (x1, y1, x2, y2, label, conf) in self.boxes:
            p.drawRect(QRect(int(x1), int(y1), int(x2 - x1), int(y2 - y1)))
            text = f"{label} {conf:.2f}" if conf is not None else str(label)
            metrics = p.fontMetrics()
            tw = metrics.horizontalAdvance(text) + 8
            th = metrics.height() + 4
            bg = QColor(0, 0, 0, 160)
            p.fillRect(int(x1), int(y1 - th), tw, th, bg)
            p.setPen(QColor(255, 255, 255, 230))
            p.drawText(int(x1 + 4), int(y1 - 6), text)
            p.setPen(self.pen)

    def _quit(self):
        if callable(self.on_close):
            self.on_close()
        self.close()

    def closeEvent(self, e):
        if callable(self.on_close):
            self.on_close()
        super().closeEvent(e)


# ===Worker: capture + (optional) YOLO inference===
class CaptureAndDetect(threading.Thread):
    def __init__(self, rect_px, out_queue, fps=10,scale=1.0):
        super().__init__(daemon=True)
        self.rect = rect_px
        self.out_q = out_queue
        self.delay = 1.0 / max(fps, 1)
        self.stop_flag = False
        self.scale = scale
        self.model = YOLO("yolov8s_openvino_model/")

    def run(self):
        last = 0
        with mss.mss() as sct:
            while not self.stop_flag:
                now = time.time()
                if now - last < self.delay:
                    time.sleep(0.002)
                    continue
                last = now

                # Capture raw frame (BGRA) to BGR
                frame = np.array(sct.grab(self.rect))[:, :, :3]

                boxes = self._yolo_boxes(frame)

                s = self.scale
                boxes_log = [(x1 / s, y1 / s, x2 / s, y2 / s, label, conf) for
                             (x1, y1, x2, y2, label, conf) in boxes]

                # Send boxes to overlay
                if self.stop_flag:
                    break
                if not self.out_q.full():
                    self.out_q.put(boxes_log)

    def _yolo_boxes(self, frame):
        if self.model is None:
            return []
        res = self.model(frame, imgsz=640, conf=0.35)[0]
        names = res.names
        boxes = []
        for b in res.boxes:
            x1, y1, x2, y2 = map(float, b.xyxy[0].tolist())
            cls = int(b.cls)
            conf = float(b.conf)
            label = names.get(cls, str(cls))
            boxes.append((x1, y1, x2, y2, label, conf))
        return boxes

import signal
# ===Logic Concat===
def main():
    app = QApplication(sys.argv)

    #Window Find
    HWND, CAPTURE_RECT = find_maps_window("Google Maps")
    if not CAPTURE_RECT:
        HWND, CAPTURE_RECT = find_maps_window("Google Chrome")
    if not CAPTURE_RECT:
        print("Window inaccessible. Open Google Maps.")
        return


    dpi = ctypes.windll.user32.GetDpiForWindow(HWND) or 96
    scale = dpi / 96.0
    RECT_L= rect_to_qt_logical(CAPTURE_RECT, HWND)

    det_q = queue.Queue(maxsize=2)
    worker = CaptureAndDetect(CAPTURE_RECT, det_q, fps=5, scale=scale)
    worker.start()

    def stop_everything():
        timer.stop()
        watch_timer.stop()
        worker.stop_flag = True
        QApplication.quit()

    overlay = Overlay(RECT_L, on_close=stop_everything)
    control=ControlBar(RECT_L, on_close=stop_everything)
    control.update_anchor(RECT_L)
    advice_panel = AdvicePanel(RECT_L)

    timer = QTimer()
    '''def pump():
        try:
            while True:
                boxes = det_q.get_nowait()
                overlay.update_boxes(boxes)
        except queue.Empty:
            pass'''

    def pump():
        try:
            updated = False
            labels_present = set()
            while True:
                boxes = det_q.get_nowait()
                overlay.update_boxes(boxes)
                for (_, _, _, _, label, conf) in boxes:
                    if conf is None or conf >= 0.35:
                        labels_present.add(label)
                updated = True
        except queue.Empty:
            if updated:
                norm = {
                    "motorcycle": "motorbike",
                    "bicycle": "bicycle",
                    "truck": "truck",
                    "bus": "bus",
                    "person": "person",
                    "car": "car",
                    "dog": "dog", "cat": "cat", "bird": "bird", "horse": "horse", "cow": "cow", "sheep": "sheep",
                    "tree": "tree"
                }
                labels_norm = {norm.get(l, l) for l in labels_present}
                advice_panel.set_labels(labels_norm)
            pass
    timer.timeout.connect(pump)
    timer.start(16)  # 60 Hz refresh

    watch_timer = QTimer()

    def watch_maps():
        try:
            if not win32gui.IsWindow(HWND) or not win32gui.IsWindowVisible(HWND):
                stop_everything()
                app.quit()
        except Exception:
            stop_everything()
            app.quit()

    watch_timer.timeout.connect(watch_maps)
    watch_timer.start(1000)  # every 1s

    def handle_sigint(*_):
        stop_everything()
        app.quit()
    signal.signal(signal.SIGINT, handle_sigint)
    app.aboutToQuit.connect(stop_everything)

    ret = app.exec()
    time.sleep(0.05)
    sys.exit(ret)


if __name__ == "__main__":
    main()
