from typing import List, Dict, Any

# Marker 라이브러리는 설치가 필요합니다: pip install marker-pdf
# 또한 PyTorch가 설치되어 있어야 합니다.
try:
    from marker.models import create_model_dict
    from marker.converters.pdf import PdfConverter
except ImportError:
    print("Marker library not found. Please install with `pip install marker-pdf`")
    create_model_dict = None
    PdfConverter = None

class PDFExtractorMarker:
    def __init__(self):
        if not create_model_dict:
            raise ImportError("Marker library is not installed.")
            
        print("Loading Marker models... (This may take a while and requires GPU/CPU memory)")
        # 모델 로드 (최초 1회 실행 시 시간이 걸림)
        # GPU가 있으면 자동으로 사용, 없으면 CPU 사용
        self.model_lst = create_model_dict()

    def extract_content(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Marker를 사용하여 PDF를 고품질 Markdown으로 변환합니다.
        복잡한 표, 수식 처리에 강점이 있습니다.
        """
        try:
            # Converter 초기화
            converter = PdfConverter(
                artifact_dict=self.model_lst,
            )
            
            # 변환 실행
            rendered = converter(pdf_path)
            
            # rendered는 MarkdownOutput 객체 (markdown, images, metadata 속성 보유)
            full_text = rendered.markdown
            metadata = rendered.metadata
            images = rendered.images
            
            return [{
                "type": "marker_markdown",
                "content": full_text,
                "page": None, # Marker는 문서를 통으로 처리함
                "metadata": metadata,
                "images": images
            }]
            
        except Exception as e:
            print(f"Error in Marker extraction: {e}")
            return []
