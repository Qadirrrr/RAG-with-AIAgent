import csv
import os
import re
from typing import List, Optional
from langchain_core.documents import Document
import pypdf

from app.config import settings


class DocumentLoaderService:
    def __init__(self, chunk_words: int = 80, chunk_overlap_words: int = 15):
        """Sentence-aware semantic small-chunk loader.

        Chunks are sized at chunk_words (~80 words / ~400-500 characters)
        with chunk_overlap_words overlap, split along natural semantic
        boundaries (paragraphs and sentences) rather than cutting mid-sentence.
        """
        try:
            chunk_words = int(chunk_words)
        except (TypeError, ValueError):
            chunk_words = 80
        if chunk_words < 10:
            chunk_words = 80

        try:
            chunk_overlap_words = int(chunk_overlap_words)
        except (TypeError, ValueError):
            chunk_overlap_words = 15
        if not 0 <= chunk_overlap_words < chunk_words:
            chunk_overlap_words = min(15, max(0, chunk_words // 4))

        self.chunk_words = chunk_words
        self.chunk_overlap_words = chunk_overlap_words

    def _clean_text(self, text: str) -> str:
        """Clean null bytes, normalize carriage returns and excess whitespace."""
        if not text:
            return ""
        text = text.replace("\x00", "")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Replace 3 or more newlines with two newlines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences while preserving sentence endings."""
        # Split on sentence boundaries (. ! ?) followed by space or newline
        raw = re.split(r"(?<=[.!?])\s+", text)
        sentences = [s.strip() for s in raw if s and s.strip()]
        return sentences

    def _split_text_to_chunks(self, text: str) -> List[str]:
        """Split text into small, coherent, sentence-aligned chunks."""
        text = self._clean_text(text)
        if not text:
            return []

        words_in_text = text.split()
        if len(words_in_text) <= self.chunk_words:
            return [text]

        # First, split into paragraphs
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks: List[str] = []
        current_chunk_words: List[str] = []

        for para in paragraphs:
            para_words = para.split()
            # If paragraph fits in remaining space of current chunk
            if len(current_chunk_words) + len(para_words) <= self.chunk_words:
                if current_chunk_words:
                    current_chunk_words.append("\n\n")
                current_chunk_words.extend(para_words)
                continue

            # If current chunk has content, flush it
            if current_chunk_words:
                chunks.append(" ".join(current_chunk_words).replace(" \n\n ", "\n\n").strip())
                # Keep overlap from the end of current chunk
                overlap = current_chunk_words[-self.chunk_overlap_words:] if self.chunk_overlap_words > 0 else []
                current_chunk_words = list(overlap)

            # If paragraph itself is smaller than chunk_words, add it
            if len(para_words) <= self.chunk_words:
                if current_chunk_words:
                    current_chunk_words.append("\n\n")
                current_chunk_words.extend(para_words)
                continue

            # Paragraph is larger than chunk_words: split by sentences
            sentences = self._split_into_sentences(para)
            for sent in sentences:
                sent_words = sent.split()
                if not sent_words:
                    continue

                if len(current_chunk_words) + len(sent_words) <= self.chunk_words:
                    current_chunk_words.extend(sent_words)
                else:
                    if current_chunk_words:
                        chunks.append(" ".join(current_chunk_words).replace(" \n\n ", "\n\n").strip())
                        overlap = current_chunk_words[-self.chunk_overlap_words:] if self.chunk_overlap_words > 0 else []
                        current_chunk_words = list(overlap)

                    # If sentence itself is longer than chunk_words, split by word window
                    if len(sent_words) > self.chunk_words:
                        step = max(1, self.chunk_words - self.chunk_overlap_words)
                        for start in range(0, len(sent_words), step):
                            window = sent_words[start:start + self.chunk_words]
                            if not window:
                                break
                            if start + self.chunk_words < len(sent_words):
                                chunks.append(" ".join(window).strip())
                            else:
                                current_chunk_words.extend(window)
                    else:
                        current_chunk_words.extend(sent_words)

        if current_chunk_words:
            chunks.append(" ".join(current_chunk_words).replace(" \n\n ", "\n\n").strip())

        # Filter out empty or duplicate trailing fragments
        cleaned_chunks = []
        for c in chunks:
            c = c.strip()
            if len(c) > 10 and (not cleaned_chunks or c != cleaned_chunks[-1]):
                cleaned_chunks.append(c)

        return cleaned_chunks if cleaned_chunks else [text]

    def _split_documents(self, docs: List[Document]) -> List[Document]:
        """Split source documents into small, high-precision semantic chunks."""
        chunks: List[Document] = []
        for doc in docs:
            raw_content = doc.page_content or ""
            text_chunks = self._split_text_to_chunks(raw_content)
            for piece in text_chunks:
                chunks.append(Document(
                    page_content=piece,
                    metadata=dict(doc.metadata or {}),
                ))
        return chunks

    def split_text(self, text: str, document_id: str, original_filename: str, extra_metadata: dict = None) -> List[Document]:
        """Split raw text (for example from a website URL) into chunks."""
        docs = [
            Document(
                page_content=self._clean_text(text),
                metadata={
                    "document_id": document_id,
                    "document_name": original_filename,
                    "page": 1,
                    **(extra_metadata or {}),
                },
            )
        ]
        chunks = self._split_documents(docs)
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = i
            chunk.metadata["document_id"] = document_id
            chunk.metadata["document_name"] = original_filename
        return chunks

    def load_and_split(self, file_path: str, document_id: str, original_filename: str) -> List[Document]:
        ext = os.path.splitext(original_filename)[1].lower()
        docs = []

        if ext == ".pdf":
            docs = self._load_pdf(file_path, document_id, original_filename)
        elif ext in [".docx", ".doc"]:
            docs = self._load_docx(file_path, document_id, original_filename)
        elif ext in [".txt", ".md"]:
            docs = self._load_txt(file_path, document_id, original_filename)
        elif ext == ".csv":
            docs = self._load_csv(file_path, document_id, original_filename)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

        chunks = self._split_documents(docs)
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = i
            chunk.metadata["document_id"] = document_id
            chunk.metadata["document_name"] = original_filename
            
        return chunks

    def _load_pdf(self, file_path: str, document_id: str, original_filename: str) -> List[Document]:
        docs = []
        with open(file_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            for page_num, page in enumerate(reader.pages, start=1):
                try:
                    text = page.extract_text() or ""
                except Exception:
                    text = ""
                if text and text.strip():
                    # De-hyphenate words broken across lines: e.g. "com-\nmittee" -> "committee"
                    cleaned = re.sub(r"(\b\w+)-\n(\w+\b)", r"\1\2", text)
                    # Preserve double newlines for paragraphs, replace single newlines with space
                    cleaned = re.sub(r"(?<!\n)\n(?!\n)", " ", cleaned)
                    cleaned = self._clean_text(cleaned)
                    if cleaned:
                        docs.append(
                            Document(
                                page_content=cleaned,
                                metadata={
                                    "document_id": document_id,
                                    "document_name": original_filename,
                                    "page": page_num
                                }
                            )
                        )
        if not docs:
            docs.append(Document(
                page_content="",
                metadata={
                    "document_id": document_id,
                    "document_name": original_filename,
                    "page": 1
                }
            ))
        return docs

    def _load_docx(self, file_path: str, document_id: str, original_filename: str) -> List[Document]:
        text = ""
        try:
            import docx2txt
            text = docx2txt.process(file_path) or ""
        except ImportError:
            try:
                import docx
                d = docx.Document(file_path)
                text = "\n\n".join(p.text for p in d.paragraphs if p.text)
            except Exception:
                text = ""
        except Exception:
            text = ""
        cleaned = self._clean_text(text)
        return [
            Document(
                page_content=cleaned,
                metadata={
                    "document_id": document_id,
                    "document_name": original_filename,
                    "page": 1
                }
            )
        ]

    def _load_csv(self, file_path: str, document_id: str, original_filename: str) -> List[Document]:
        """Load a CSV as structured documents per row, rendered as 'column: value' lines."""
        raw = ""
        for encoding in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
            try:
                with open(file_path, "r", encoding=encoding, newline="") as f:
                    raw = f.read()
                break
            except (UnicodeDecodeError, Exception):
                continue

        rows = list(csv.reader(raw.splitlines()))
        if not rows:
            return [Document(page_content="", metadata={
                "document_id": document_id, "document_name": original_filename, "page": 1})]

        headers = [h.strip() for h in rows[0]]
        docs = []
        for row_num, row in enumerate(rows[1:], start=2):
            lines = []
            for i, value in enumerate(row):
                col = headers[i] if i < len(headers) and headers[i] else f"column_{i + 1}"
                v_clean = value.strip()
                if v_clean:
                    lines.append(f"{col}: {v_clean}")
            text = "\n".join(lines).strip()
            if text:
                docs.append(Document(
                    page_content=text,
                    metadata={
                        "document_id": document_id,
                        "document_name": original_filename,
                        "page": row_num,
                    }
                ))
        if not docs:
            docs.append(Document(page_content="", metadata={
                "document_id": document_id, "document_name": original_filename, "page": 1}))
        return docs

    def _load_txt(self, file_path: str, document_id: str, original_filename: str) -> List[Document]:
        text = ""
        for encoding in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    text = f.read()
                break
            except (UnicodeDecodeError, Exception):
                continue

        return [
            Document(
                page_content=self._clean_text(text),
                metadata={
                    "document_id": document_id,
                    "document_name": original_filename,
                    "page": 1
                }
            )
        ]


document_loader_service = DocumentLoaderService(
    chunk_words=settings.CHUNK_WORDS,
    chunk_overlap_words=settings.CHUNK_WORD_OVERLAP,
)
