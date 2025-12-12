# 1. Python 베이스 이미지 사용 (3.10 버전 권장)
FROM python:3.10-slim

# 2. 시스템 패키지 업데이트 및 필수 빌드 도구 설치
# PyMuPDF, ChromaDB 등 의존성을 위해 build-essential 필요할 수 있음
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 3. 작업 디렉토리 설정
WORKDIR /app

# 4. 의존성 파일 복사 및 설치
COPY requirements.txt .
# 캐시 없이 설치하여 이미지 크기 최적화 및 최신 버전 보장
RUN pip install --no-cache-dir -r requirements.txt

# 5. 프로젝트 소스 코드 복사
COPY src/ src/
COPY templates/ templates/
COPY data/ data/
# 설정 파일 등 기타 필요한 파일이 있다면 추가 복사
# 예: COPY .env . (보통 환경변수는 Fly.io Secrets로 관리하므로 제외)

# 6. 환경 변수 설정
# Python 출력 버퍼링 비활성화 (로그 즉시 출력)
ENV PYTHONUNBUFFERED=1
# 기본 포트 설정 (Fly.io 기본값 8080)
ENV PORT=8080
# Flask 앱 위치 지정
ENV FLASK_APP=src.app:app

# 7. 포트 개방 선언
EXPOSE 8080

# 8. 실행 명령어 (Gunicorn 사용)
# -w 2: 워커 프로세스 2개 (CPU 코어 수에 따라 조정)
# --threads 4: 스레드 4개 (I/O 작업이 많으므로 스레드 활용)
# --timeout 120: RAG 처리/PDF 다운로드가 오래 걸릴 수 있으므로 타임아웃 넉넉히 설정
CMD ["gunicorn", "src.app:app", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "4", "--timeout", "120"]

