import io
import json
import uuid
import gc
from datetime import datetime, timezone, timedelta
from src.config.config import AWS_S3_BUCKET, AWS_REGION

KST = timezone(timedelta(hours=9))

class ArchiveService:
    """
    공고문 PDF, 추출 결과, 청크, 질의응답 로그를 S3에 쌓는 서비스
    - AWS_S3_BUCKET이 없으면 아무것도 하지 않음 (로컬에서 AWS 설정 없이 실행 가능)
    - 업로드 실패는 로그만 남기고 넘어감 (공고 분석/답변 기능에 영향 없음)
    """
    def __init__(self):
        self.bucket = AWS_S3_BUCKET
        self.enabled = bool(self.bucket)
        self._client = None
        if not self.enabled:
            print("ℹ️ AWS_S3_BUCKET 미설정: S3 아카이브 비활성화")

    @property # 메서드를 변수처럼 쓸 수 있게 해줌. 괄호 없이 읽기만 해도 함수가 실행됨.
    def client(self):
        # boto3는 메모리를 많이 쓰므로 첫 업로드 시점에 import
        if self._client is None:
            import boto3 # 서버가 켜질 때 boto3를 바로 불러오면 메모리를 수십 MB를 차지하는데, 실제로 S3에 첫 업로드 하는 순간에만 boto3를 불러옴.
            gc.collect()
            self._client = boto3.client("s3", region_name=AWS_REGION)
        return self._client # 사용할 때 self.client.put_object(...) -> 괄호 없이 변수처럼

    @staticmethod # `self`가 필요 없는 메서드라는 표시.
    def now(): # self 인자가 없음. 사용할 때 self.now() - 객체에서 호출, ArchiveService.now() - 객체 없이 클래스에서 바로 호출 둘 다 가능
        return datetime.now(KST)

    def notice_prefix(self, doc_id):
        """공고 1건의 파일들이 들어갈 폴더 (처리한 날짜 기준)"""
        return f"notices/dt={self.now():%Y-%m-%d}/{doc_id}/"

    def qa_key(self, doc_id):
        """질문 1건의 로그 파일 경로"""
        now = self.now()
        return f"qa/dt={now:%Y-%m-%d}/{doc_id}/{now:%H%M%S}_{uuid.uuid4().hex[:6]}.json"

    def _put(self, key, body, content_type):
        if not self.enabled:
            return False
        try:
            self.client.put_object(Bucket=self.bucket, Key=key, Body=body, ContentType=content_type)
            print(f"☁️ S3 업로드: {key}")
            return True
        except Exception as e:
            print(f"⚠️ S3 업로드 실패(계속 진행): {key} - {e}")
            return False

    def put_file(self, local_path, key, content_type="application/octet-stream"):
        if not self.enabled:
            return False
        try:
            with open(local_path, "rb") as f:
                return self._put(key, f, content_type)
        except OSError as e:
            print(f"⚠️ 파일 읽기 실패(계속 진행): {local_path} - {e}")
            return False

    def put_text(self, text, key, content_type="text/plain; charset=utf-8"):
        return self._put(key, text.encode("utf-8"), content_type)

    def put_json(self, data, key):
        body = json.dumps(data, ensure_ascii=False, indent=2, default=str)
        return self.put_text(body, key, "application/json; charset=utf-8")

    def put_chunks(self, chunks, prefix):
        """청크 목록을 chunks.jsonl(분석용)과 chunks.xlsx(사람이 보기용)로 저장"""
        if not self.enabled:
            return
        rows = [
            {"index": i, "length": len(c.page_content), "metadata": c.metadata, "content": c.page_content}
            for i, c in enumerate(chunks)
        ]
        jsonl = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows)
        self.put_text(jsonl, prefix + "chunks.jsonl", "application/x-ndjson; charset=utf-8")

        try:
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "chunks"
            ws.append(["index", "length", "metadata", "content"])
            for r in rows:
                # 엑셀 셀 최대 글자 수 (32, 767) 초과 방지
                ws.append([r["index"], r["length"], json.dumps(r["metadata"], ensure_ascii=False), r["content"][:32000]])
            buf = io.BytesIO()
            wb.save(buf)
            self._put(prefix + "chunks.xlsx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except Exception as e:
            print(f"⚠️ chunks.xlsx 생성 실패(계속 진행): {e}")

    
    