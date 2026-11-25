import csv
import os
from typing import List, Tuple
from langchain_core.documents import Document
import pypdf
import docx2txt

from app.config import settings

class DocumentLoaderService:
    def __init__(self, chunk_words: int = 20, chunk_overlap_words: int = 5):
        # Word-based chunking: each chunk holds at most chunk_words
        # words, and consecutive chunks share chunk_overlap_words words.
        try:
            chunk_words = int(chunk_words)
        except (TypeError, ValueError):
            chunk_words = 20
        if chunk_words < 1:
            chunk_words = 20
        try:
            chunk_overlap_words = int(chunk_overlap_words)
        except (TypeError, ValueError):
            chunk_overlap_words = 5
        if not 0 <= chunk_overlap_words < chunk_words:
            # Misconfigured overlap must never crash ingestion; fall
            # back to the default 5-word overlap (or just below the
            # chunk size for very small chunks).
            chunk_overlap_words = 5 if chunk_words > 5 else max(0, chunk_words - 1)
        self.chunk_words = chunk_words
        self.chunk_overlap_words = chunk_overlap_words

    def _split_documents(self, docs: List[Document]) -> List[Document]:
        """Split source documents into word-based chunks.

        Each source document is split independently (so a PDF page or a
        CSV row never bleeds into the next one): its text is cut into
        windows of at most chunk_words words, stepping by
        chunk_words - chunk_overlap_words so consecutive chunks share
        the configured overlap. The last chunk of a document may be
        shorter. Source metadata is preserved on every chunk.
        """
        step = self.chunk_words - self.chunk_overlap_words
        chunks = []
        for doc in docs:
            words = doc.page_content.split()
            if not words:
                continue
            for start in range(0, len(words), step):
                window = words[start:start + self.chunk_words]
                if not window:
                    break
                chunks.append(Document(
                    page_content=" ".join(window),
                    metadata=dict(doc.metadata),
                ))
        return chunks

    def split_text(self, text: str, document_id: str, original_filename: str, extra_metadata: dict = None) -> List[Document]:
        """Split raw text (for example from a website URL) into chunks."""
        docs = [
            Document(
                page_content=text.strip(),
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

        # Split into chunks while preserving metadata
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
                text = page.extract_text()
                if text and text.strip():
                    docs.append(
                        Document(
                            page_content=text.strip(),
                            metadata={
                                "document_id": document_id,
                                "document_name": original_filename,
                                "page": page_num
                            }
                        )
                    )
        if not docs:
            # Handle empty PDF or scanned PDF with no direct text
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
        text = docx2txt.process(file_path)
        return [
            Document(
                page_content=text.strip() if text else "",
                metadata={
                    "document_id": document_id,
                    "document_name": original_filename,
                    "page": 1
                }
            )
        ]

    def _load_csv(self, file_path: str, document_id: str, original_filename: str) -> List[Document]:
        """Load a CSV as one document per row, rendered as 'column: value' lines."""
        try:
            with open(file_path, "r", encoding="utf-8", newline="") as f:
                raw = f.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="latin-1", newline="") as f:
                raw = f.read()
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
                lines.append(f"{col}: {value}")
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
        # Try UTF-8 first, fallback to latin-1
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="latin-1") as f:
                text = f.read()

        return [
            Document(
                page_content=text.strip() if text else "",
                metadata={
                    "document_id": document_id,
                    "document_name": original_filename,
                    "page": 1
                }
            )
        ]

# The shared ingestion service uses the configured chunking so an
# operator can tune the chunk word count and overlap via CHUNK_WORDS
# and CHUNK_WORD_OVERLAP in the backend .env without touching code.
document_loader_service = DocumentLoaderService(
    chunk_words=settings.CHUNK_WORDS,
    chunk_overlap_words=settings.CHUNK_WORD_OVERLAP,
)

