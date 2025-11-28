# Flask 웹 애플리케이션 가이드

## Flask란?

Flask는 Python으로 웹 애플리케이션을 만들 수 있는 경량 웹 프레임워크입니다.

- **가볍고 간단함**: 최소한의 코드로 웹 서버 구동 가능
- **유연함**: 필요한 기능만 추가 가능
- **RESTful API**: API 서버로도 활용 가능

## 설치 방법

```bash
# 가상 환경 활성화 후
pip install flask flask-cors

# 또는 requirements.txt에서
pip install -r requirements.txt
```

## 기본 사용법

### 1. 간단한 Flask 앱

```python
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello World!'

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

### 2. 실행

```bash
python src/app.py
```

브라우저에서 `http://localhost:5000` 접속

## 프로젝트 구조

```
ai/
├── src/
│   └── app.py              # Flask 앱 메인 파일
├── templates/              # HTML 템플릿
│   └── index.html
├── static/                 # CSS, JS, 이미지 (선택사항)
│   ├── css/
│   └── js/
└── requirements.txt
```

## 주요 기능

### 1. 라우트 (Route)

```python
@app.route('/api/users', methods=['GET'])
def get_users():
    return jsonify({"users": []})
```

### 2. 요청 데이터 받기

```python
@app.route('/api/query', methods=['POST'])
def query():
    data = request.json  # JSON 데이터
    question = data.get('question', '')
    return jsonify({"answer": "답변"})
```

### 3. HTML 렌더링

```python
@app.route('/')
def index():
    return render_template('index.html')
```

## API 엔드포인트 예시

### GET 요청
```python
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})
```

### POST 요청
```python
@app.route('/api/query', methods=['POST'])
def query():
    data = request.json
    # 처리 로직
    return jsonify({"result": "..."})
```

## 개발 서버 실행

```bash
# 방법 1: 직접 실행
python src/app.py

# 방법 2: Flask 명령어
flask --app src.app run --debug
```

## 프로덕션 배포

개발용 서버(`app.run()`)는 프로덕션에 적합하지 않습니다.

프로덕션에서는 다음을 사용:
- **Gunicorn** (Linux/Mac)
- **Waitress** (Windows)
- **Docker** + **Nginx**

## CORS 설정

다른 도메인에서 API 호출 시:

```python
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 모든 도메인 허용
# 또는
CORS(app, origins=["http://localhost:3000"])  # 특정 도메인만
```

## 디버그 모드

```python
app.run(debug=True)  # 코드 변경 시 자동 재시작
```

⚠️ **주의**: 프로덕션에서는 `debug=False`로 설정!

## 다음 단계

1. RAG 파이프라인을 `app.py`에 연동
2. 프론트엔드와 API 통신 테스트
3. 에러 처리 및 로깅 추가
4. 사용자 인증 추가 (선택사항)

