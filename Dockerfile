# Render 배포용 Dockerfile
FROM python:3.10-slim

# 시스템 패키지 설치 (PDF 처리 라이브러리 의존성)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 설치 (캐시 활용을 위해 먼저 복사)
COPY requirements.txt .
# --no-cache-dir 옵션은 빌드 이미지 용량을 줄여줍니다.
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 코드 및 필요한 데이터 복사
COPY . .

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=src.app:app
# 파이썬 메모리 할당 최적화 (MALLOC_ARENA_MAX)
ENV MALLOC_ARENA_MAX=2

# 포트 설정 (기본값 10000)
ENV PORT=10000

# 실행 명령  
# 1. 512MB (Render 무료) 에서는 workers 1
CMD ["/bin/sh", "-c", "gunicorn src.app:app --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 120 --access-logfile - --error-logfile -"]