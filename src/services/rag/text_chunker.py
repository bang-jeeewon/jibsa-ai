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
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,    # 한 청크당 최대 글자 수
            chunk_overlap=100   # 앞뒤 겹치는 구간 (문맥 끊김 방지)
        )
        final_chunks = text_splitter.split_documents(header_splits)

        return final_chunks