"""
mouse_pointer.py — 화면 녹화 / 강의 영상 제작용 마우스 커서 하이라이터
------------------------------------------------------------------
기능:
  - 커서 위치에 반투명 노란색 원 표시 (click-through 오버레이)
  - 좌클릭 시 붉은색 파동(ripple) 애니메이션 (0.25초)
  - F8 키로 즉시 종료

의존성:
  pip install PyQt5 pynput
"""

import sys
import ctypes
import ctypes.wintypes
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QRect, pyqtProperty, QPoint
from PyQt5.QtGui import QPainter, QColor, QPen, QRadialGradient, QBrush
from pynput import mouse as pmouse, keyboard as pkeyboard

# ─────────────────────────────────────────────
# Windows API 상수
# ─────────────────────────────────────────────
GWL_EXSTYLE      = -20
WS_EX_LAYERED    = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
LWA_ALPHA        = 0x00000002

user32 = ctypes.windll.user32


def set_click_through(hwnd: int) -> None:
    """윈도우에 WS_EX_TRANSPARENT | WS_EX_LAYERED 적용 → 클릭이 뒤로 통과."""
    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    style |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)


# ─────────────────────────────────────────────
# 파동(Ripple) 애니메이션 클래스
# ─────────────────────────────────────────────
class RippleState:
    """단일 파동의 상태를 보관합니다."""
    DURATION_MS = 250          # 파동 지속 시간(ms)

    def __init__(self, cx: int, cy: int):
        self.cx = cx
        self.cy = cy
        self.elapsed = 0        # 경과 ms

    @property
    def progress(self) -> float:
        """0.0 → 1.0"""
        return min(self.elapsed / self.DURATION_MS, 1.0)

    @property
    def radius(self) -> float:
        return 8 + 44 * self.progress   # 8px → 52px

    @property
    def alpha(self) -> int:
        """끝으로 갈수록 투명해짐."""
        return int(220 * (1.0 - self.progress))

    @property
    def done(self) -> bool:
        return self.elapsed >= self.DURATION_MS


# ─────────────────────────────────────────────
# 오버레이 위젯
# ─────────────────────────────────────────────
HIGHLIGHT_RADIUS = 22          # 노란 원 반지름(px)
OVERLAY_SIZE     = 160         # 오버레이 창 크기(px) — 파동이 커져도 잘리지 않게

class OverlayWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._mouse_x = 0
        self._mouse_y = 0
        self._ripples: list[RippleState] = []

        # ── 창 스타일 ──
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowTransparentForInput   # Qt 레벨 click-through
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.resize(OVERLAY_SIZE, OVERLAY_SIZE)

        # ── 메인 루프 타이머 (16ms ≒ 60fps) ──
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def show(self):
        super().show()
        # show() 이후 hwnd가 생성되므로 여기서 Win32 스타일 적용
        hwnd = int(self.winId())
        set_click_through(hwnd)

    # ── 외부에서 호출되는 이벤트 수신 메서드 ──
    def on_mouse_move(self, x: int, y: int):
        self._mouse_x = x
        self._mouse_y = y

    def on_left_click(self, x: int, y: int):
        self._ripples.append(RippleState(x, y))

    # ── 타이머 tick ──
    def _tick(self):
        # 오버레이 창 위치를 커서 중심으로 이동
        half = OVERLAY_SIZE // 2
        self.move(self._mouse_x - half, self._mouse_y - half)

        # 파동 시간 진행
        for r in self._ripples:
            r.elapsed += 16
        self._ripples = [r for r in self._ripples if not r.done]

        self.update()   # 재그리기 요청

    # ── 페인팅 ──
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setCompositionMode(QPainter.CompositionMode_Source)

        half = OVERLAY_SIZE // 2

        # 1) 파동(ripple) — 먼저 그려서 하이라이트 뒤에 나타나도록
        for rip in self._ripples:
            # 파동 중심은 오버레이 로컬 좌표로 변환
            rx = rip.cx - self._mouse_x + half
            ry = rip.cy - self._mouse_y + half
            pen = QPen(QColor(220, 30, 30, rip.alpha), 2.5)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            r = rip.radius
            painter.drawEllipse(int(rx - r), int(ry - r), int(r * 2), int(r * 2))

        # 2) 노란 하이라이트 원 (반투명)
        hr = HIGHLIGHT_RADIUS
        cx, cy = half, half
        grad = QRadialGradient(cx, cy, hr)
        grad.setColorAt(0.0, QColor(255, 230, 0, 160))   # 중심: 밝은 노랑
        grad.setColorAt(0.6, QColor(255, 200, 0, 100))
        grad.setColorAt(1.0, QColor(255, 180, 0, 0))     # 가장자리: 투명
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawEllipse(cx - hr, cy - hr, hr * 2, hr * 2)

        painter.end()


# ─────────────────────────────────────────────
# pynput 리스너 설정
# ─────────────────────────────────────────────
def start_listeners(overlay: OverlayWidget, app: QApplication):
    # 마우스 이동 / 클릭
    def on_move(x, y):
        overlay.on_mouse_move(x, y)

    def on_click(x, y, button, pressed):
        if button == pmouse.Button.left and pressed:
            overlay.on_left_click(x, y)

    mouse_listener = pmouse.Listener(on_move=on_move, on_click=on_click)
    mouse_listener.daemon = True
    mouse_listener.start()

    # 키보드 — F8 종료
    def on_press(key):
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
    # HiDPI 스케일링 비활성화 — 좌표 불일치 방지
    QApplication.setAttribute(Qt.AA_DisableHighDpiScaling)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)   # 오버레이만 열려 있어도 유지

    overlay = OverlayWidget()
    overlay.show()

    # 초기 커서 위치 획득
    pt = ctypes.wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    overlay.on_mouse_move(pt.x, pt.y)

    start_listeners(overlay, app)

    print("Mouse Highlighter 실행 중 — F8 을 누르면 종료됩니다.")
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
