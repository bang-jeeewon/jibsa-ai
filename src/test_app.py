#!/usr/bin/env python
"""간단한 테스트 앱 - 포트 바인딩 확인용"""
from flask import Flask
import os

app = Flask(__name__)


@app.route('/')
def index():
    return 'Hello from Render!'


if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    print(f"🚀 테스트 앱 시작: 포트 {port}")
    print(f"📁 작업 디렉토리: {os.getcwd()}")
    app.run(host='0.0.0.0', port=port, debug=False)

# python test_app.py -> can't open file '/opt/render/project/src/test_app.py': [Errno 2] No such file or directory
# python -m src.test_app -> 로컬이랑 똑같이 실행, development로 배포 -> 배포 성공  
# gunicorn src.test_app:app -> production 환경에서 배포 성공
# gunicorn src.app:app -> production 환경에서 배포 성공
# gunicorn src.test_app:app --bind 0.0.0.0:${PORT:-10000}