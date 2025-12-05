from flask import Flask, jsonify, render_template, request
import json
import os
from src.services.crawl_url import CrawlUrlService
from src.services.download_pdf import DownloadPdfService
from src.services.rag_service import RAGService

# Flask 앱 인스턴스
app = Flask(__name__, template_folder='../templates')


# RAG 서비스 전역 인스턴스 (앱 시작 시 초기화)
crawl_url_service = CrawlUrlService()
download_pdf_service = DownloadPdfService()
rag_service = RAGService()



# TODO 캘린더 UI 연결해서 데이터 로드   
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


@app.route('/api/analyze', methods=['POST'])
def analyze_apt():
    """특정 공고 분석 요청 처리 (PDF 다룬로드 및 분석)"""
    data = request.json 
    pblanc_url = data.get('pblanc_url') # 모집공고 상세 URL
    house_manage_no = data.get('house_manage_no') # 주택관리번호
    pblanc_no = data.get('pblanc_no') # 공고번호
    house_secd = data.get('house_secd') # 주택구분코드

    # 1. 모집공고문 다운로드 URL 크롤링
    download_url = crawl_url_service.crawl_url(pblanc_url=pblanc_url)
    if not download_url:
        return jsonify({"status": "error", "message": "모집공고문 다운로드 URL 크롤링 실패"}), 500

    # 2. 모집공고문 PDF 다운로드
    pdf_path = download_pdf_service.download_pdf(download_url=download_url, file_name=f"{house_manage_no}_{pblanc_no}_{house_secd}.pdf")
    if not pdf_path:
        return jsonify({"status": "error", "message": "모집공고문 PDF 다운로드 실패"}), 500

    # 3. RAG 서비스에 PDF 등록 (ETF 구조)
    # house_manage_no를 문서 ID로 사용하여 메타데이터 저장
    rag_service.process_pdf_for_rag(pdf_path=pdf_path, doc_id=str(house_manage_no))
    
    return jsonify({"status": "success", "message": "PDF 등록 완료"})


@app.route('/api/query', methods=['POST'])
def query():
    """챗봇 질의응답"""
    data = request.json
    question = data.get('question', '')
    house_manage_no = data.get('house_manage_no') # 프론트에서 전달받은 공고 ID
    
    if not question:
        return jsonify({"answer": "질문을 입력해주세요."})

    # RAG 모델을 통해 답변 생성
    try:
        # doc_id 필터를 적용하여 해당 공고 내에서만 검색
        answer = rag_service.answer_question(question, doc_id=str(house_manage_no))
        return jsonify({"answer": answer})
    except Exception as e:
        print(f"Error generating answer: {e}")
        return jsonify({"answer": "죄송합니다. 답변을 생성하는 중에 오류가 발생했습니다."}), 500


@app.route('/api/reset', methods=['POST'])
def reset_db():
    """벡터 DB 초기화"""
    try:
        rag_service.clear_database()
        return jsonify({"status": "success", "message": "DB가 초기화되었습니다."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


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
                    'pblanc_url': apt.get('PBLANC_URL'),
                    'house_manage_no': apt.get('HOUSE_MANAGE_NO'),
                    'pblanc_no': apt.get('PBLANC_NO'),
                    'house_secd': apt.get('HOUSE_SECD'),
                    'house_secd_nm': apt.get('HOUSE_SECD_NM'),
                    'subscrpt_area_code_nm': apt.get('SUBSCRPT_AREA_CODE_NM'),
                    'startDate': apt.get('RCEPT_BGNDE'),
                    'endDate': apt.get('RCEPT_ENDDE')
                }
            })
            
    return jsonify(events)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
