from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
import re


TOKEN_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]+")


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    title: str
    content: str
    score: float
    allowed_roles: list[str]


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def chunk_text(text: str, max_words: int = 90) -> list[str]:
    words = text.split()
    if not words:
        return []
    return [" ".join(words[index : index + max_words]) for index in range(0, len(words), max_words)]


def role_allowed(user_role: str, allowed_roles: list[str]) -> bool:
    normalized = {role.strip().lower() for role in allowed_roles}
    return "all" in normalized or user_role.lower() in normalized


def cosine_score(question: str, content: str) -> float:
    question_counts = Counter(tokenize(question))
    content_counts = Counter(tokenize(content))
    if not question_counts or not content_counts:
        return 0.0
    overlap = set(question_counts) & set(content_counts)
    numerator = sum(question_counts[token] * content_counts[token] for token in overlap)
    q_norm = math.sqrt(sum(value * value for value in question_counts.values()))
    c_norm = math.sqrt(sum(value * value for value in content_counts.values()))
    return numerator / (q_norm * c_norm) if q_norm and c_norm else 0.0


