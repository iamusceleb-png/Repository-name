"""
mouse_pointer.py — 화면 녹화 / 강의 영상 제작용 마우스 커서 하이라이터
------------------------------------------------------------------
기능:
  - 커서 위치에 반투명 노란색 원 표시 (click-through 오버레이)
  - 좌클릭 시 붉은색 파동(ripple) 애니메이션 (0.25초)
  - +/- 키로 하이라이트 크기 조절 (10px ~ 80px)
  - F8 키로 즉시 종료

의존성:
  pip install PyQt5 pynput
"""

import sys
import ctypes
import ctypes.wintypes
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QRadialGradient, QBrush
from pynput import mouse as pmouse, keyboard as pkeyboard

# ─────────────────────────────────────────────
# Windows API 상수
# ─────────────────────────────────────────────
GWL_EXSTYLE       = -20
WS_EX_LAYERED     = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE  = 0x08000000
WS_EX_TOOLWINDOW  = 0x00000080

user32 = ctypes.windll.user32


def set_click_through(hwnd: int) -> None:
    """윈도우에 WS_EX_TRANSPARENT | WS_EX_LAYERED 적용 → 클릭이 뒤로 통과."""
    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    style |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)


# ─────────────────────────────────────────────
# 파동(Ripple) 상태
# ─────────────────────────────────────────────
class RippleState:
    DURATION_MS = 250

    def __init__(self, cx: int, cy: int):
        self.cx = cx
        self.cy = cy
        self.elapsed = 0

    @property
    def progress(self) -> float:
        return min(self.elapsed / self.DURATION_MS, 1.0)

    @property
    def radius(self) -> float:
        return 8 + 44 * self.progress

    @property
    def alpha(self) -> int:
        return int(220 * (1.0 - self.progress))

    @property
    def done(self) -> bool:
        return self.elapsed >= self.DURATION_MS


# ─────────────────────────────────────────────
# 크기 설정
# ─────────────────────────────────────────────
RADIUS_DEFAULT = 28    # 기본 반지름 (px)
RADIUS_MIN     = 10    # 최소
RADIUS_MAX     = 80    # 최대
RADIUS_STEP    = 4     # +/- 한 번에 변화량
OVERLAY_SIZE   = 220   # 오버레이 창 크기 (파동 포함)


# ─────────────────────────────────────────────
# 오버레이 위젯
# ─────────────────────────────────────────────
class OverlayWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._mouse_x = 0
        self._mouse_y = 0
        self._ripples: list[RippleState] = []
        self._radius = RADIUS_DEFAULT

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.resize(OVERLAY_SIZE, OVERLAY_SIZE)

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def show(self):
        super().show()
        hwnd = int(self.winId())
        set_click_through(hwnd)

    # ── 외부 이벤트 ──
    def on_mouse_move(self, x: int, y: int):
        self._mouse_x = x
        self._mouse_y = y

    def on_left_click(self, x: int, y: int):
        self._ripples.append(RippleState(x, y))

    def increase_radius(self):
        self._radius = min(self._radius + RADIUS_STEP, RADIUS_MAX)

    def decrease_radius(self):
        self._radius = max(self._radius - RADIUS_STEP, RADIUS_MIN)

    # ── 타이머 tick ──
    def _tick(self):
        half = OVERLAY_SIZE // 2
        self.move(self._mouse_x - half, self._mouse_y - half)

        for r in self._ripples:
            r.elapsed += 16
        self._ripples = [r for r in self._ripples if not r.done]

        self.update()

    # ── 페인팅 ──
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setCompositionMode(QPainter.CompositionMode_Source)

        half = OVERLAY_SIZE // 2

        # 1) 파동(ripple)
        for rip in self._ripples:
            rx = rip.cx - self._mouse_x + half
            ry = rip.cy - self._mouse_y + half
            pen = QPen(QColor(220, 30, 30, rip.alpha), 2.5)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            r = rip.radius
            painter.drawEllipse(int(rx - r), int(ry - r), int(r * 2), int(r * 2))

        # 2) 노란 하이라이트 원 — 더 진하게 (알파값 상향)
        hr = self._radius
        cx, cy = half, half
        grad = QRadialGradient(cx, cy, hr)
        grad.setColorAt(0.0, QColor(255, 235, 0, 220))   # 중심: 진한 노랑
        grad.setColorAt(0.5, QColor(255, 210, 0, 170))
        grad.setColorAt(0.8, QColor(255, 190, 0, 90))
        grad.setColorAt(1.0, QColor(255, 170, 0, 0))     # 가장자리: 투명
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawEllipse(cx - hr, cy - hr, hr * 2, hr * 2)

        painter.end()


# ─────────────────────────────────────────────
# pynput 리스너
# ─────────────────────────────────────────────
def start_listeners(overlay: OverlayWidget, app: QApplication):
    def on_move(x, y):
        overlay.on_mouse_move(x, y)

    def on_click(x, y, button, pressed):
        if button == pmouse.Button.left and pressed:
            overlay.on_left_click(x, y)

    mouse_listener = pmouse.Listener(on_move=on_move, on_click=on_click)
    mouse_listener.daemon = True
    mouse_listener.start()

    def on_press(key):
        try:
            ch = key.char
            if ch in ('+', '='):      # = 는 Shift 없이 누를 때 +와 같은 키
                overlay.increase_radius()
            elif ch == '-':
                overlay.decrease_radius()
        except AttributeError:
            pass

        if key == pkeyboard.Key.f8:
            app.quit()

    kb_listener = pkeyboard.Listener(on_press=on_press)
    kb_listener.daemon = True
    kb_listener.start()

    return mouse_listener, kb_listener


# ─────────────────────────────────────────────
# 진입점
# ─────────────────────────────────────────────
def main():
    QApplication.setAttribute(Qt.AA_DisableHighDpiScaling)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    overlay = OverlayWidget()
    overlay.show()

    pt = ctypes.wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    overlay.on_mouse_move(pt.x, pt.y)

    start_listeners(overlay, app)

    print("Mouse Highlighter 실행 중")
    print("  +  키 : 크기 키우기")
    print("  -  키 : 크기 줄이기")
    print("  F8 키 : 종료")
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
