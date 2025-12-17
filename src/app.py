from flask import Flask, jsonify, render_template, request
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 프로젝트 루트를 sys.path에 추가 (Render 배포 시 경로 문제 해결)
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Flask 앱 인스턴스
app = Flask(__name__, template_folder='../templates')

# 서비스 전역 인스턴스 (지연 초기화 - 앱 시작 속도 향상)
crawl_url_service = None
download_pdf_service = None
rag_service = None
api_client = None


def init_services():
    """서비스를 지연 초기화 (앱 시작 후 백그라운드에서 초기화)"""
    global crawl_url_service, download_pdf_service, rag_service, api_client
    if crawl_url_service is None:
        try:
            print("🔄 서비스 초기화 시작...")
            # 무거운 의존성 로드를 초기화 시점으로 미룸
            from src.services.crawl_url import CrawlUrlService
            from src.services.download_pdf import DownloadPdfService
            from src.services.rag_service import RAGService
            from src.client.api_client import ApplyhomeAPIClient

            crawl_url_service = CrawlUrlService()
            download_pdf_service = DownloadPdfService()
            rag_service = RAGService()
            api_client = ApplyhomeAPIClient()
            print("✅ 서비스 초기화 완료")
        except Exception as e:
            print(f"⚠️ 서비스 초기화 중 에러 발생: {e}")
            crawl_url_service = None
            download_pdf_service = None
            rag_service = None
            api_client = None

# 앱 시작 시 서비스 초기화 (백그라운드)
import threading
threading.Thread(target=init_services, daemon=True).start()



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
    # 서비스 초기화 확인
    if crawl_url_service is None or download_pdf_service is None or rag_service is None:
        return jsonify({"status": "error", "message": "서비스가 아직 초기화 중입니다. 잠시 후 다시 시도해주세요."}), 503
    
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
    try:
        rag_service.process_pdf_for_rag(pdf_path=pdf_path, doc_id=str(house_manage_no))
        
        # 4. RAG 처리 완료 후 임시 PDF 파일 삭제
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
            print(f"🗑️ 임시 PDF 파일 삭제 완료: {pdf_path}")
        
        return jsonify({"status": "success", "message": "PDF 등록 완료"})
    except Exception as e:
        # 에러 발생 시에도 임시 파일 삭제 시도
        if os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
                print(f"🗑️ 에러 발생 후 임시 PDF 파일 삭제 완료: {pdf_path}")
            except:
                pass
        raise e


@app.route('/api/query', methods=['POST'])
def query():
    """챗봇 질의응답"""
    # 서비스 초기화 확인
    if rag_service is None:
        return jsonify({"answer": "서비스가 아직 초기화 중입니다. 잠시 후 다시 시도해주세요."}), 503
    
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
    # 서비스 초기화 확인
    if rag_service is None:
        return jsonify({"status": "error", "message": "서비스가 아직 초기화 중입니다."}), 503
    
    try:
        rag_service.clear_database()
        return jsonify({"status": "success", "message": "DB가 초기화되었습니다."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/calendar-data')
def get_calendar_data():
    """캘린더에 표시할 데이터 반환 (실시간 API 연동)"""
    start_str = request.args.get('start') # 예: 2024-05-01
    end_str = request.args.get('end')     # 예: 2024-06-02
    
    # FullCalendar 날짜 포맷 (YYYY-MM-DD)을 API 날짜 포맷으로 변환 필요 시 처리
    # 여기서는 그대로 사용 (API가 YYYY-MM-DD도 받을 수 있다고 가정)
    
    print(f"📅 캘린더 데이터 요청: {start_str} ~ {end_str}")

    # 서비스 초기화 확인
    if api_client is None:
        return jsonify([])
    
    try:
        # 민영(01) + 국민(03) 데이터를 모두 가져와야 함 (필요하다면)
        # 일단 기본은 '01'(민영)만 가져오거나, 두 번 호출해서 합칠 수도 있음.
        # 여기서는 '01'만 먼저 테스트
        response_data = api_client.get_detail(
            houseDtlSecd="01", 
            start_date=start_str, 
            end_date=end_str,
            page=1
        )

        print(f"response_data: {response_data}")
        
        items = response_data.get('data', [])
        
        # 국민주택('03')도 필요하면 추가 호출해서 items에 extend
        # response_data_03 = api_client.get_detail(houseDtlSecd="03", start_date=start_str, end_date=end_str)
        # items.extend(response_data_03.get('data', []))

        events = []
        for apt in items:
            # 접수 시작일을 이벤트 날짜로 사용
            if apt.get('RCEPT_BGNDE'):
                end_date = apt.get('RCEPT_ENDDE')
                # FullCalendar는 end 날짜가 exclusive하므로 캘린더 표시용으로 하루를 더함
                adjusted_end_date = end_date
                if end_date:
                    try:
                        dt = datetime.strptime(end_date, '%Y-%m-%d')
                        dt_plus_one = dt + timedelta(days=1)
                        adjusted_end_date = dt_plus_one.strftime('%Y-%m-%d')
                    except ValueError:
                        pass  # 날짜 형식이 안맞으면 그대로 사용
                
                events.append({
                    'title': apt.get('HOUSE_NM'),
                    'start': apt.get('RCEPT_BGNDE'),
                    'end': adjusted_end_date,  # 캘린더 표시용: 하루 더한 값 (12/18)
                    'color': '#667eea',
                    'extendedProps': {
                        'pblanc_url': apt.get('PBLANC_URL'),
                        'house_manage_no': apt.get('HOUSE_MANAGE_NO'),
                        'pblanc_no': apt.get('PBLANC_NO'),
                        'house_secd': apt.get('HOUSE_SECD'),
                        'house_secd_nm': apt.get('HOUSE_SECD_NM'),
                        'subscrpt_area_code_nm': apt.get('SUBSCRPT_AREA_CODE_NM'),
                        'startDate': apt.get('RCEPT_BGNDE'),
                        'endDate': end_date  # 헤더/팝업 표시용: 원래 날짜 (12/17)
                    }
                })
        
        return jsonify(events)

    except Exception as e:
        print(f"❌ 캘린더 데이터 조회 실패: {e}")
        return jsonify([])

if __name__ == '__main__':
    # Windows에서 소켓 오류 방지를 위해 use_reloader=False 설정
    # 0.0.0.0으로 설정하여 모든 인터페이스에서 접속 허용
    # Render에서는 PORT 환경변수를 사용, 없으면 기본값 10000
    port = int(os.getenv('PORT', 10000))
    print(f"🚀 Flask 앱 시작 중... 포트: {port}, 호스트: 0.0.0.0")
    print(f"📁 작업 디렉토리: {os.getcwd()}")
    print(f"📁 프로젝트 루트: {project_root}")
    try:
        app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)
    except Exception as e:
        print(f"❌ 앱 시작 실패: {e}")
        import traceback
        traceback.print_exc()
        raise
