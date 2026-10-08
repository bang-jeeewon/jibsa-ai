import gc

class TextChunker:
    def chunk_markdown(self, markdown_text):
        from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
        gc.collect()

        # 1. 제목 기준으로 1차 분할
        headers_to_split_on = [
            ("#", "header_1"),
            ("##", "header_2"),
            ("###", "header_3"),
        ]
        # MarkdownHeaderTextSplitter: 자동으로 헤더 뒤의 텍스트를 추출해서 metadata에 추가함  
        markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        header_splits = markdown_splitter.split_text(markdown_text)

        # 2. 제목 단위 청크가 너무 긴 경우 글자 수 기준으로 2차 분할
        #    (공고문은 '#' 섹션 하나가 수만 자인 경우가 있어, 그대로 두면 검색 정확도와 답변 비용이 나빠짐)
        #    문단(\n\n) → 줄(\n) → 공백 순서로 최대한 자연스러운 위치에서 자름
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,    # 청크 최대 글자 수
            chunk_overlap=100,  # 앞뒤 청크와 겹치는 글자 수 (문장이 잘려도 맥락 유지)
        )
        final_chunks = text_splitter.split_documents(header_splits)

        gc.collect()
        return final_chunks
