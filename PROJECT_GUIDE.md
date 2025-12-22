# 아파트 청약 공고문 챗봇 프로젝트 가이드

## 📋 프로젝트 개요

이 프로젝트는 아파트 청약 공고문 PDF를 자동으로 다운로드하고, RAG(Retrieval-Augmented Generation) 기술을 활용하여 사용자의 질문에 답변하는 챗봇 시스템입니다.

## 🏗️ 전체 시스템 아키텍처

```
사용자 → Flask API → RAG 서비스 → 벡터 DB (Chroma)
                              ↓
                         OpenAI GPT-4o-mini
```

## 🔄 프로젝트 구동 방식

### 1단계: 공고 선택 및 PDF 처리 파이프라인

#### 1.1 공고 클릭 (`/api/analyze` 엔드포인트)

- 사용자가 캘린더에서 공고를 클릭하면 `house_manage_no`, `pblanc_url`, `pblanc_no`, `house_secd` 정보가 전달됩니다.

#### 1.2 PDF 다운로드 URL 크롤링

- **서비스**: `CrawlUrlService`
- **클라이언트**: `ApplyhomeCrawlClient`
- 모집공고문 상세 페이지(`pblanc_url`)에서 PDF 다운로드 URL을 크롤링합니다.
- BeautifulSoup을 사용하여 HTML을 파싱하고 PDF 다운로드 링크를 추출합니다.

#### 1.3 PDF 파일 다운로드

- **서비스**: `DownloadPdfService`
- **클라이언트**: `ApplyhomeDownloadClient`
- 크롤링한 URL에서 PDF 파일을 다운로드하여 임시 디렉토리(`./tmp/pdfs`)에 저장합니다.
- 파일명 형식: `{house_manage_no}_{pblanc_no}_{house_secd}.pdf`

#### 1.4 PDF 내용 추출 (Extract)

- **모듈**: `PDFExtractor`
- **라이브러리**: `pdfplumber`
- PDF에서 다음을 추출합니다:
  - **텍스트 데이터**: 페이지의 일반 텍스트
  - **표 데이터**: 테이블 구조를 2차원 리스트로 추출
- 추출된 데이터는 순서를 보장하며 `[{"type": "text"|"table", "content": ..., "page": ..., "y_start": ..., "y_end": ...}]` 형식으로 반환됩니다.

#### 1.5 데이터 정제 및 Markdown 변환 (Transform)

- **모듈**: `DataProcessor`
- **처리 과정**:
  1. **텍스트 정제**: 페이지 번호 등 불필요한 텍스트 제거
  2. **제목 변환**: 알려진 제목(예: "공통 유의사항", "공급대상 및 공급금액")을 Markdown 헤더(`#`, `##`)로 변환
  3. **표 정제**:
     - 빈 행 제거
     - 병합된 셀 처리 (수평 방향 채우기)
     - 불필요한 텍스트 행(Garbage Row) 제거
  4. **Markdown 표 변환**: `tabulate` 라이브러리를 사용하여 표를 Markdown 형식으로 변환

#### 1.6 텍스트 청킹 (Chunking)

- **모듈**: `TextChunker`
- **1차 분할**: `MarkdownHeaderTextSplitter`를 사용하여 Markdown 헤더(`#`, `##`, `###`)를 기준으로 문서를 분할
- **2차 분할**: `RecursiveCharacterTextSplitter`를 사용하여 긴 청크를 추가로 분할
  - `chunk_size`: 500자 (비용 절감을 위해 최적화)
  - `chunk_overlap`: 50자 (문맥 유지를 위한 겹침)
- 각 청크는 LangChain의 `Document` 객체로 생성되며, 헤더 정보가 메타데이터에 포함됩니다.

#### 1.7 벡터 DB 저장 (Load)

- **모듈**: `VectorStoreService`
- **벡터 DB**: Chroma (LangChain 통합)
- **저장 위치**: `persist_directory` 파라미터로 지정 (기본값: `./data/chroma_db`)
- **임베딩 모델**:
  - **기본값**: OpenAI `text-embedding-3-small` (더 안정적이고 rate limit이 높음)
  - **선택 가능**: Google Generative AI `models/gemini-embedding-001` (설정 시 사용)
- **배치 처리**:
  - 청크를 5개씩 묶어서 처리 (rate limit 방지)
  - 각 배치 처리 후 4초 대기 (분당 약 15 요청 제한 준수)
  - 예: 467개 청크 → 약 8~9분 소요
- **재시도 로직**:
  - 429 에러 발생 시 최대 3회 재시도 (exponential backoff)
  - 차원 불일치 에러 시 자동으로 벡터 DB 재생성
- **컬렉션 이름**: `apt_notices`
- **메타데이터**: 각 청크에 `doc_id` (house_manage_no)가 메타데이터로 추가되어 특정 공고 내에서만 검색 가능하도록 구성
- 처리 완료 후 임시 PDF 파일은 자동으로 삭제됩니다.

### 2단계: 질의응답 파이프라인

#### 2.1 질문 입력 (`/api/query` 엔드포인트)

- 사용자가 질문을 입력하면 `question`, `house_manage_no`, `model` (GPT/Gemini 선택), `conversation_history` (대화 히스토리)가 전달됩니다.
- **대화 히스토리**: 최근 3턴(질문+답변)만 전송하여 이전 대화 맥락 유지

#### 2.2 관련 문서 검색 (Retrieve)

- **모듈**: `VectorStoreService.search()`
- 질문을 임베딩하여 벡터 DB에서 유사한 문서를 검색합니다.
- **검색 파라미터**:
  - `k=5`: 상위 5개의 관련 청크를 검색 (정확도 향상)
  - `filter={"doc_id": house_manage_no}`: 특정 공고 내에서만 검색하도록 필터링
- 검색 결과가 없으면 "관련 정보를 찾을 수 없습니다" 메시지를 반환합니다.

#### 2.3 컨텍스트 생성 (Augment)

- 검색된 문서들의 `page_content`를 `\n\n`으로 연결하여 하나의 컨텍스트 문자열을 생성합니다.

#### 2.4 프롬프트 구성

- **시스템 프롬프트**:

  ```
  아파트 청약 공고문 전문 분석 AI입니다. 아래 내용만 참고하여 질문에 답변하세요.
  없는 정보는 "찾을 수 없습니다"라고 답변하세요.
  이전 대화 내용을 참고하여 맥락을 이해하고 답변하세요.

  [공고문 내용]
  {context}

  [이전 대화 내용]
  {conversation_history}
  ```

- **사용자 메시지**: 사용자가 입력한 질문
- **대화 히스토리**: 이전 대화 내용이 있으면 프롬프트에 포함하여 맥락 유지

#### 2.5 답변 생성 (Generate)

- **모델 선택**: 사용자가 GPT 또는 Gemini 중 선택 가능
  - **GPT-4o-mini** (기본값): 비용 효율적, 안정적, 대화 히스토리를 `messages` 배열로 관리
  - **Gemini Pro**: 무료 티어 제공, 대화 히스토리를 프롬프트 텍스트에 포함
- **파라미터**:
  - `temperature=0`: 사실 기반 답변을 위해 일관성 유지
  - `max_tokens=500`: 답변 길이 제한
- **재시도 로직**:
  - 429 에러 발생 시 최대 3회 재시도
  - 에러 메시지에서 retry delay 추출하여 대기
- 생성된 답변을 사용자에게 반환합니다.

| 구분          | OpenAI               | Google Generative AI         |
| ------------- | -------------------- | ---------------------------- |
| 플랫폼/회사   | OpenAI               | Google AI Studio             |
| Python 패키지 | openai               | google-generativeai          |
| 초기화 방식   | 클라이언트 객체 생성 | configure() 함수 사용        |
| 사용 예시     | OpenAI(api_key=...)  | genai.configure(api_key=...) |

## 📁 프로젝트 구조

```
ai/
├── src/
│   ├── app.py                    # Flask 메인 애플리케이션
│   ├── services/
│   │   ├── rag_service.py        # RAG 파이프라인 총괄 서비스
│   │   ├── crawl_url.py          # PDF URL 크롤링 서비스
│   │   ├── download_pdf.py       # PDF 다운로드 서비스
│   │   └── rag/
│   │       ├── pdf_extractor.py  # PDF 내용 추출
│   │       ├── data_processor.py # 데이터 정제 및 Markdown 변환
│   │       ├── text_chunker.py   # 텍스트 청킹
│   │       └── vector_store.py   # 벡터 DB 관리
│   ├── client/
│   │   ├── crawl_client.py       # 크롤링 클라이언트
│   │   ├── download_client.py    # 다운로드 클라이언트
│   │   └── api_client.py         # 공고 정보 API 클라이언트
│   └── config/
│       └── config.py             # 설정 파일
├── data/
│   └── chroma_db/               # Chroma 벡터 DB 저장 위치
├── tmp/
│   └── pdfs/                    # 임시 PDF 저장 위치
└── requirements.txt             # Python 패키지 의존성
```

## 🔑 주요 기술 스택

### 백엔드

- **Flask**: 웹 프레임워크
- **LangChain**: RAG 파이프라인 구축
- **Chroma**: 벡터 데이터베이스
- **pdfplumber**: PDF 텍스트 및 표 추출

### AI/ML

- **임베딩 모델**:
  - **OpenAI** `text-embedding-3-small` (기본값, 1536 차원): 더 안정적이고 rate limit이 높음
  - **Google Generative AI** `gemini-embedding-001` (선택 시, 3072 차원): 무료 티어 제공
- **LLM 답변 생성**:
  - **OpenAI** `gpt-4o-mini` (기본값): 비용 효율적, 안정적
  - **Google Gemini** `gemini-2.0-flash-exp` (선택 시): 무료 티어 제공

### 데이터 처리

- **pandas**: 데이터 처리
- **tabulate**: 표를 Markdown 형식으로 변환

### 웹 크롤링

- **BeautifulSoup4**: HTML 파싱
- **requests**: HTTP 요청

## 💡 주요 특징

1. **ETL 구조**: Extract(추출) → Transform(변환) → Load(저장) 파이프라인으로 명확히 분리
2. **문서별 필터링**: `doc_id` 메타데이터를 활용하여 특정 공고 내에서만 검색
3. **비용 최적화**:
   - 청크 크기 최적화 (500자)
   - 가성비 좋은 모델 사용 (`gpt-4o-mini`)
   - 프롬프트 간소화
4. **지연 초기화**: 무거운 서비스(RAG, 크롤링 등)는 실제 사용 시점에만 초기화하여 서버 시작 시간 단축
5. **임시 파일 관리**: PDF 처리 후 자동 삭제하여 디스크 공간 절약
6. **배치 처리 및 Rate Limit 방지**:
   - 임베딩 API 호출을 5개씩 배치로 처리
   - 배치 간 4초 대기로 rate limit 준수
   - 429 에러 발생 시 자동 재시도 (최대 3회)
7. **대화 히스토리 지원**: 이전 대화 내용을 참고하여 맥락을 유지한 답변 생성
8. **임베딩 모델 선택**: OpenAI(기본값) 또는 Gemini 임베딩 선택 가능
9. **LLM 모델 선택**: 사용자가 GPT 또는 Gemini 중 선택 가능 (프론트엔드 라디오 버튼)

## 🔄 API 엔드포인트

### `POST /api/analyze`

공고 PDF를 다운로드하고 벡터 DB에 저장합니다.

**요청 본문**:

```json
{
  "pblanc_url": "https://...",
  "house_manage_no": "2025000486",
  "pblanc_no": "2025000486",
  "house_secd": "01"
}
```

**응답**:

```json
{
  "status": "success",
  "message": "PDF 등록 완료"
}
```

### `POST /api/query`

사용자 질문에 대해 RAG 방식으로 답변을 생성합니다.

**요청 본문**:

```json
{
  "question": "공급대상은 무엇인가요?",
  "house_manage_no": "2025000486",
  "model": "openai",
  "conversation_history": [
    { "role": "user", "content": "전매제한 기간은?" },
    { "role": "assistant", "content": "전매제한 기간은 10년입니다." }
  ]
}
```

**응답**:

```json
{
  "answer": "공급대상은 다음과 같습니다..."
}
```

### `POST /api/reset`

벡터 DB를 초기화합니다.

**응답**:

```json
{
  "status": "success",
  "message": "DB가 초기화되었습니다."
}
```

### `GET /api/calendar-data`

캘린더에 표시할 공고 정보를 반환합니다.

**쿼리 파라미터**:

- `start`: 시작 날짜 (YYYY-MM-DD)
- `end`: 종료 날짜 (YYYY-MM-DD)

## 📝 사용자 설명 검증 결과

사용자가 설명한 프로젝트 구조는 **모두 정확**합니다:

✅ 유저가 공고를 클릭하면 해당 공고의 PDF를 크롤링으로 다운받음  
✅ PDF에서 텍스트와 표 데이터를 추출  
✅ 추출된 raw content를 정제해서 markdown으로 변환  
✅ Markdown의 header를 기준으로 청크 생성  
✅ 벡터 DB(Chroma)에 청크 저장, `persist_directory` 사용  
✅ 유저 질문 입력 시 벡터 DB에서 관련 문서 검색  
✅ 검색된 문서로 context 생성 후 프롬프트 구성  
✅ GPT-4o-mini 또는 Gemini Pro 모델로 답변 생성 (사용자 선택)

**추가로 확인된 세부사항**:

- `doc_id` 필터링으로 특정 공고 내에서만 검색
- PDF 처리 후 임시 파일 자동 삭제
- 청크에 메타데이터로 `doc_id` 추가
- 2차 청킹(RecursiveCharacterTextSplitter)으로 긴 청크 추가 분할
- 비용 최적화를 위한 청크 크기 및 모델 선택
- **배치 처리**: 청크를 5개씩 묶어서 처리하고 배치 간 4초 대기 (rate limit 방지)
- **재시도 로직**: 429 에러 발생 시 자동 재시도 (최대 3회)
- **차원 불일치 처리**: 임베딩 모델 변경 시 자동으로 벡터 DB 재생성
- **대화 히스토리**: 이전 대화 내용을 참고하여 맥락 유지
- **임베딩 모델 선택**: OpenAI(기본값, 1536차원) 또는 Gemini(3072차원) 선택 가능

## 🚀 실행 방법

1. **의존성 설치**:

```bash
pip install -r requirements.txt
```

2. **환경 변수 설정**:
   `.env` 파일에 다음을 설정:

- `OPENAI_API_KEY`: OpenAI API 키
- `GOOGLE_API_KEY`: Google Generative AI API 키

3. **서버 실행**:

```bash
python src/app.py
```

4. **브라우저 접속**:

```
http://localhost:10000
```

## 📊 비용 분석 (참고)

한 번의 질문 처리 비용 (k=5 기준):

- 질문 임베딩: 약 50 토큰
- 검색된 컨텍스트: 약 1,250 토큰
- 시스템 프롬프트: 약 50 토큰
- 총 입력: 약 1,350 토큰
- 출력: 약 500 토큰
- **예상 비용**: 약 $0.0005 (약 0.65원)
- **한 달 10,000원 예산**: 하루 약 512개 질문 가능

---

**작성일**: 2024년  
**프로젝트**: 아파트 청약 공고문 챗봇
