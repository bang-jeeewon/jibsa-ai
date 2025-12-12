from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

class TextChunker:
    def __init__(self):

        pass


    def chunk_markdown(self, markdown_text):
        # 1. 제목 기준으로 1차 분할
        headers_to_split_on = [
            ("#", "header_1"),
            ("##", "header_2"),
            ("###", "header_3"),
        ]
        markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        header_splits = markdown_splitter.split_text(markdown_text)

        # 2. 내용이 너무 긴 경우를 대비해 토큰 단위로 2차 분할
        # 비용 절감: chunk_size를 500으로 줄여서 각 청크당 토큰 수 감소 (500 글자 ≈ 200-250 토큰)
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,     # 한 청크당 최대 글자 수 (기존 1000 → 500으로 감소)
            chunk_overlap=50    # 앞뒤 겹치는 구간 (기존 100 → 50으로 감소)
        )
        final_chunks = text_splitter.split_documents(header_splits)

        return final_chunks