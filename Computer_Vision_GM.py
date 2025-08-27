#Imports model for CV
#Opens Google_Maps at selected dots and applies the CV model

import win32gui, win32process
import time,queue,threading
import mss, numpy as np, cv2

#Finding only Google Window(Maps)

def find_maps_window(title_contains="Google Chrome"):
    hwnd=[]
    def wind_handl(h,_):
        if win32gui.IsWindowVisible(h):
            title=win32gui.GetWindowText(h)
            if title_contains.lower() in title.lower():
                hwnd.append(h)
    win32gui.EnumWindows(wind_handl, None)
    if not hwnd: return None
    rect=win32gui.GetWindowRect(hwnd[0])
    l,t,r,b=rect
    return{"left":l+8, "top":t+50, "width":(r-l)-16, "height":(b-t)-88}

from ultralytics import YOLO

model = YOLO("yolov8s_openvino_model/")

capture_reg = find_maps_window("Google Maps") or find_maps_window("Google Chrome")
#capture_reg = {"top": 120, "left": 80, "width": 1280, "height": 720}
#if not capture_reg: raise SystemExit("Window inaccesible. Open Chrome for CV action")
if not capture_reg: print("Window inaccesible. Open Chrome for CV action")

#cv2.namedWindow("Screen Detections", cv2.WINDOW_NORMAL)
#cv2.moveWindow("Screen Detections", 50, 50)

stop = False
cap_q = queue.Queue(maxsize=2)
vis_q = queue.Queue(maxsize=2)

def capture_loop():
    last = 0
    with mss.mss() as sct:
        while not stop:
            frame = np.array(sct.grab(capture_reg))[:, :, :3]
            if not cap_q.full():
                cap_q.put(frame)
            if time.time() - last < 0.2:  # 5 FPS
                if cv2.waitKey(1) & 0xFF == ord('q'): break
                continue
            last = time.time()

def infer_loop():
    while not stop:
        try:
            frame = cap_q.get(timeout=0.1)
        except queue.Empty:
            continue
        res = model(frame, imgsz=640, conf=0.35)[0]
        vis = res.plot()
        if not vis_q.full():
            vis_q.put(vis)

def display_loop():
    cv2.namedWindow("Screen Detections", cv2.WINDOW_NORMAL)
    cv2.moveWindow("Screen Detections", 1500, 100)
    while not stop:
        try:
            vis = vis_q.get(timeout=0.1)
            cv2.imshow("Screen Detections", vis)
        except queue.Empty:
            pass
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cv2.destroyAllWindows()

t1 = threading.Thread(target=capture_loop, daemon=True)
t2 = threading.Thread(target=infer_loop, daemon=True)
t3 = threading.Thread(target=display_loop)

t1.start(); t2.start(); t3.start()
t3.join(); stop = True
"""
last = 0
with mss.mss() as sct:
    while True:
        if time.time() - last < 0.2:  # 5 FPS
            if cv2.waitKey(1) & 0xFF == ord('q'): break
            continue
        last = time.time()

        img = np.array(sct.grab(capture_reg))[:, :, :3]  # BGRA -> BGR
        res = model(img, conf=0.35, imgsz=640)[0]
        vis = res.plot()

        cv2.imshow("Screen Detections", vis)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
cv2.destroyAllWindows()"""
"""
HAZARD_HINTS = {
    "car":      ("Class B (fuel), A interior", "CO2/Dry chem for engine; foam/water for interior if safe."),
    "truck":    ("Class B/A", "CO2/Dry chem; foam for fuel spill."),
    "bus":      ("Class B/A", "CO2/Dry chem; foam."),
    "motorbike":("Class B", "CO2/Dry chem."),
    "bicycle":  ("A (rubber/parts)", "Water/foam if safe."),
    "potted plant": ("A (vegetation)", "Water; clear dry material."),
    "bench":    ("A", "Water."),
    "tree":     ("A (vegetation)", "Water; create defensible space."),
    "plant":    ("A", "Water."),
    "fire hydrant": ("-","Not a hazard; useful resource nearby."),
    # You can extend with custom classes (e.g., oil spill) if you train or use open-vocab models
}"""
