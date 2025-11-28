from flask import Flask, jsonify, render_template, request
import json
import os

app = Flask(__name__, template_folder='../templates')

# JSON 데이터 로드 함수
def load_apt_data():
    json_path = os.path.join(os.path.dirname(__file__), '../data/response/get_detail.json')
    try:
        # 파일을 읽어서 JSON 파싱 
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"data": []}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/calendar-data')
def get_calendar_data():
    """캘린더에 표시할 데이터 반환"""
    data = load_apt_data()
    events = []
    
    for apt in data.get('data', []):
        # 접수 시작일을 이벤트 날짜로 사용
        if apt.get('RCEPT_BGNDE'):
            events.append({
                'title': apt.get('HOUSE_NM'),
                'start': apt.get('RCEPT_BGNDE'),
                'end': apt.get('RCEPT_ENDDE'), # FullCalendar는 end 날짜의 00:00까지를 의미하므로 실제로는 하루 더해야 꽉 차게 나오지만 일단 그대로 둠
                'color': '#667eea', # 기본 색상
                # 추가 정보 (상세 화면용)
                'extendedProps': {
                    'houseNo': apt.get('HOUSE_MANAGE_NO'),
                    'pblancNo': apt.get('PBLANC_NO'),
                    'area': apt.get('SUBSCRPT_AREA_CODE_NM'),
                    'startDate': apt.get('RCEPT_BGNDE'),
                    'endDate': apt.get('RCEPT_ENDDE'),
                    'houseType': apt.get('HOUSE_SECD_NM')
                }
            })
            
    return jsonify(events)

@app.route('/api/analyze', methods=['POST'])
def analyze_apt():
    """특정 공고 분석 요청 처리 (PDF 다운로드 및 분석)"""
    data = request.json
    # 여기서 실제 분석 로직(PDF 다운로드 -> RAG)을 호출하면 됨
    # 지금은 성공했다는 더미 응답만 보냄
    return jsonify({"status": "success", "message": "Analysis completed"})

@app.route('/api/query', methods=['POST'])
def query():
    """챗봇 질의응답"""
    data = request.json
    question = data.get('question', '')
    
    # TODO: 실제 RAG 모델 연결 필요
    return jsonify({
        "answer": f"'{question}'에 대한 AI 답변입니다. (아직 실제 AI가 연결되지 않았습니다.)"
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
