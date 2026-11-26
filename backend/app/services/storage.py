import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

class MetadataStorage:
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.docs_file = os.path.join(self.data_dir, "documents.json")
        self.activity_file = os.path.join(self.data_dir, "activity.json")
        self.stats_file = os.path.join(self.data_dir, "stats.json")
        
        self._init_files()

    def _init_files(self):
        if not os.path.exists(self.docs_file):
            with open(self.docs_file, "w", encoding="utf-8") as f:
                json.dump({}, f)
        if not os.path.exists(self.activity_file):
            with open(self.activity_file, "w", encoding="utf-8") as f:
                json.dump([], f)
        if not os.path.exists(self.stats_file):
            with open(self.stats_file, "w", encoding="utf-8") as f:
                json.dump({"total_questions_asked": 0}, f)

    def get_all_documents(self) -> List[Dict[str, Any]]:
        try:
            with open(self.docs_file, "r", encoding="utf-8") as f:
                docs = json.load(f)
                return sorted(list(docs.values()), key=lambda x: x.get("upload_date", ""), reverse=True)
        except Exception:
            return []

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        docs = self.get_all_documents()
        for doc in docs:
            if doc["id"] == doc_id:
                return doc
        return None

    def save_document(self, doc_data: Dict[str, Any]):
        try:
            with open(self.docs_file, "r", encoding="utf-8") as f:
                docs = json.load(f)
        except Exception:
            docs = {}
        docs[doc_data["id"]] = doc_data
        with open(self.docs_file, "w", encoding="utf-8") as f:
            json.dump(docs, f, indent=2, default=str)

    def delete_document(self, doc_id: str) -> bool:
        try:
            with open(self.docs_file, "r", encoding="utf-8") as f:
                docs = json.load(f)
            if doc_id in docs:
                del docs[doc_id]
                with open(self.docs_file, "w", encoding="utf-8") as f:
                    json.dump(docs, f, indent=2, default=str)
                return True
        except Exception:
            pass
        return False

    def log_activity(self, activity_type: str, title: str, details: str = ""):
        try:
            with open(self.activity_file, "r", encoding="utf-8") as f:
                activity = json.load(f)
        except Exception:
            activity = []
        
        item = {
            "id": str(len(activity) + 1),
            "type": activity_type,
            "title": title,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
        activity.insert(0, item)
        # Keep latest 50
        activity = activity[:50]
        with open(self.activity_file, "w", encoding="utf-8") as f:
            json.dump(activity, f, indent=2)

    def get_recent_activity(self, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            with open(self.activity_file, "r", encoding="utf-8") as f:
                activity = json.load(f)
                return activity[:limit]
        except Exception:
            return []

    def increment_questions(self):
        try:
            with open(self.stats_file, "r", encoding="utf-8") as f:
                stats = json.load(f)
        except Exception:
            stats = {"total_questions_asked": 0}
        stats["total_questions_asked"] = stats.get("total_questions_asked", 0) + 1
        with open(self.stats_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)

    def get_stats(self) -> Dict[str, Any]:
        docs = self.get_all_documents()
        total_docs = len(docs)
        processed_docs = len([d for d in docs if d.get("status") == "processed"])
        total_chunks = sum([d.get("chunks_count", 0) for d in docs])
        try:
            with open(self.stats_file, "r", encoding="utf-8") as f:
                stats = json.load(f)
                questions = stats.get("total_questions_asked", 0)
        except Exception:
            questions = 0

        return {
            "total_documents": total_docs,
            "processed_documents": processed_docs,
            "total_chunks": total_chunks,
            "total_questions_asked": questions,
            "recent_activity": self.get_recent_activity(6)
        }

storage_service = MetadataStorage()

