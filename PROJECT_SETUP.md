# Python 프로젝트 시작 가이드

## 1단계: 프로젝트 디렉토리 구조 만들기

```
ai/
├── src/                    # 소스 코드 디렉토리
│   └── __init__.py        # Python 패키지로 만들기 (빈 파일)
├── data/                  # 데이터 저장 디렉토리
│   └── pdfs/              # PDF 파일 저장
├── venv/                  # 가상 환경 (자동 생성됨)
├── .env                   # 환경 변수 (API 키 등)
├── .gitignore            # Git 제외 파일 목록
├── requirements.txt      # Python 패키지 목록
└── README.md             # 프로젝트 설명서
```

## 2단계: 가상 환경 생성 및 활성화

### Windows
```bash
# 가상 환경 생성
python -m venv venv

# 가상 환경 활성화
venv\Scripts\activate

# 활성화되면 프롬프트 앞에 (venv) 표시됨
```

### Linux/Mac
```bash
# 가상 환경 생성
python3 -m venv venv

# 가상 환경 활성화
source venv/bin/activate
```

## 3단계: 필요한 패키지 설치

### requirements.txt 파일 만들기
```txt
langchain>=0.1.0
langchain-community>=0.0.10
langchain-openai>=0.0.2
langchain-chroma>=0.1.0
pypdf>=3.17.0
pdfplumber>=0.10.0
PyMuPDF>=1.23.0
chromadb>=0.4.0
sentence-transformers>=2.2.0
openai>=1.10.0
python-dotenv>=1.0.0
```

### 패키지 설치
```bash
pip install -r requirements.txt
```

## 4단계: 기본 파일 구조 만들기

### src/__init__.py (빈 파일)
```python
# 빈 파일이어도 됨 - Python 패키지로 인식
```

### src/config.py
```python
"""설정 파일"""
import os
from dotenv import load_dotenv

load_dotenv()

# API 키
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# 디렉토리 경로
DATA_DIR = "./data"
PDF_DIR = os.path.join(DATA_DIR, "pdfs")
```

### .env 파일
```env
OPENAI_API_KEY=your_api_key_here
```

### .gitignore
```
venv/
.env
__pycache__/
*.pyc
data/pdfs/*
chroma_db/
```

## 5단계: 간단한 테스트 파일 만들기

### src/main.py
```python
"""메인 파일"""
import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import PDF_DIR

def main():
    print("프로젝트가 정상적으로 작동합니다!")
    print(f"PDF 디렉토리: {PDF_DIR}")

if __name__ == "__main__":
    main()
```

## 6단계: 실행 테스트

```bash
# 방법 1: 직접 실행
python src/main.py

# 방법 2: 모듈로 실행
python -m src.main
```

## 7단계: 프로젝트 개발 시작

이제 필요한 모듈들을 하나씩 추가하면서 개발하면 됩니다:

1. **PDF 로더 모듈** (`src/pdf_loader.py`)
2. **텍스트 분할 모듈** (`src/text_splitter.py`)
3. **벡터 스토어 모듈** (`src/vector_store.py`)
4. **RAG 파이프라인** (`src/rag_pipeline.py`)

## 팁

### 패키지 설치 확인
```bash
pip list
```

### 가상 환경 비활성화
```bash
deactivate
```

### 새 패키지 추가 시
```bash
pip install 패키지명
pip freeze > requirements.txt  # requirements.txt 업데이트
```

### Python 경로 문제 해결
- `src/main.py`에서 `sys.path.insert(0, str(project_root))` 추가
- 또는 프로젝트 루트에서 `python -m src.main` 형태로 실행

