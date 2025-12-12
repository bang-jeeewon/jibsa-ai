# Render 배포용 Dockerfile
FROM python:3.10-slim

# 시스템 패키지 설치 (PDF 처리 라이브러리 의존성)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 코드 복사
COPY src/ src/
COPY templates/ templates/
COPY data/ data/

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=src.app:app

# Render는 $PORT 환경 변수를 자동으로 제공하므로 이를 사용
# 쉘을 통해 실행하여 환경 변수 치환 보장
CMD ["/bin/sh", "-c", "gunicorn src.app:app --bind 0.0.0.0:${PORT:-10000} --workers 2 --threads 4 --timeout 120"]

