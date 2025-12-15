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

