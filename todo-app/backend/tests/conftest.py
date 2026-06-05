"""pytest 설정 파일.

backend 디렉터리를 import 경로에 추가하여, 테스트에서 `from models...`
처럼 패키지를 절대 경로로 import할 수 있도록 한다.
"""

import os
import sys

# backend/ (이 파일의 상위의 상위) 를 sys.path에 추가
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
