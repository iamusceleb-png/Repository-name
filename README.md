# 🖱️ Mouse Highlighter

화면 녹화 및 강의 영상 제작 시 마우스 커서를 강조해 주는 초경량 Python 유틸리티입니다.

## ✨ 기능

- **노란 원 하이라이트** — 마우스 커서를 실시간으로 따라다니는 반투명 노란색 원
- **클릭 파동 효과** — 좌클릭 시 붉은색 링이 0.25초 동안 퍼졌다 사라지는 애니메이션
- **Click-through** — 오버레이가 클릭/조작을 가로막지 않음 (Windows API `WS_EX_TRANSPARENT` 적용)
- **F8 종료** — 키보드 F8 키로 즉시 종료

## 🚀 실행 방법

### 1. 의존성 설치
```bash
pip install PyQt5 pynput
```

### 2. 실행
```bash
python mouse_pointer.py
```

## 📦 PyInstaller로 .exe 빌드 (배포용)

```bash
pip install pyinstaller

pyinstaller --onefile --noconsole --name "MouseHighlighter" ^
  --hidden-import pynput.keyboard._win32 ^
  --hidden-import pynput.mouse._win32 ^
  mouse_pointer.py
```

빌드 완료 후 `dist\MouseHighlighter.exe` 파일 하나만 배포하면 Python 없이 바로 실행됩니다.

> ⚠️ 바이러스 백신이 오탐할 수 있습니다. PyInstaller + 키보드 훅 조합의 공통 현상이며 코드는 안전합니다.

## ⌨️ 단축키

| 키 | 동작 |
|---|---|
| F8 | 프로그램 종료 |

## 🛠️ 요구 사항

- Windows 10 / 11
- Python 3.8 이상
- PyQt5, pynput
