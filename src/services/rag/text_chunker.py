from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
import gc

class TextChunker:
    def chunk_markdown(self, markdown_text):
        # 1. 제목 기준으로 1차 분할
        headers_to_split_on = [
            ("#", "header_1"),
            ("##", "header_2"),
            ("###", "header_3"),
        ]
        # MarkdownHeaderTextSplitter: 자동으로 헤더 뒤의 텍스트를 추출해서 metadata에 추가함  
        markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        header_splits = markdown_splitter.split_text(markdown_text)

        # 2. 내용이 너무 긴 경우를 대비해 토큰 단위로 2차 분할 (테스트를 위해 비활성화)
        # text_splitter = RecursiveCharacterTextSplitter(
        #     chunk_size=500,
        #     chunk_overlap=50
        # )
        # final_chunks = text_splitter.split_documents(header_splits)

        gc.collect()
        return header_splits # 우선은 헤더 단위로만 청크 생성  