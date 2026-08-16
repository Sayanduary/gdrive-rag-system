import json
import re
from collections import Counter
from typing import Generator

import requests

from config import settings
from app.services.vectorstore import VectorStore


class RAGService:

    def __init__(self):
        self.vector_store = VectorStore()

    # ==================================================
    # CONFIG
    # ==================================================

    def _final_k(self) -> int:
        try:
            value = int(
                getattr(
                    settings,
                    "TOP_K",
                    8,
                )
            )
        except (TypeError, ValueError):
            value = 8

        return max(1, min(value, 20))

    def _candidate_k(self) -> int:
        try:
            value = int(
                getattr(
                    settings,
                    "RETRIEVAL_CANDIDATES",
                    100,
                )
            )
        except (TypeError, ValueError):
            value = 100

        return max(20, min(value, 300))

    # ==================================================
    # EMPTY RESULTS
    # ==================================================

    @staticmethod
    def _empty_results() -> dict:
        return {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

    # ==================================================
    # BASIC RETRIEVAL
    # ==================================================

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        user_id: str | None = None,
        folder_id: str | None = None,
        file_id: str | None = None,
    ):

        if not user_id:
            raise ValueError(
                "user_id is required for RAG retrieval."
            )

        query = query.strip()

        if not query:
            return self._empty_results()

        if top_k is None or top_k <= 0:
            top_k = self._candidate_k()

        return self.vector_store.search(
            query=query,
            top_k=top_k,
            user_id=user_id,
            folder_id=folder_id,
            file_id=file_id,
        )

    # ==================================================
    # FOLLOW-UP DETECTION
    # ==================================================

    def is_follow_up_question(
        self,
        question: str,
    ) -> bool:

        normalized = (
            question
            .strip()
            .lower()
        )

        follow_up_phrases = {
            "tell more",
            "tell me more",
            "explain more",
            "explain further",
            "more",
            "continue",
            "go on",
            "what about that",
            "what about this",
            "can you elaborate",
            "elaborate",
            "more details",
            "give more details",
            "say more",
            "expand",
            "explain",
            "details",
        }

        if normalized in follow_up_phrases:
            return True

        return len(
            normalized.split()
        ) <= 3

    # ==================================================
    # CONVERSATION HISTORY
    # ==================================================

    def build_history(
        self,
        messages: list[dict] | None = None,
    ) -> str:

        if not messages:
            return ""

        parts = []

        for message in messages[-6:]:

            role = message.get(
                "role",
                "",
            )

            content = (
                message.get(
                    "content",
                    "",
                )
                .strip()
            )

            if not content:
                continue

            if role == "user":
                parts.append(
                    f"USER: {content}"
                )

            elif role == "assistant":
                parts.append(
                    f"ASSISTANT: {content}"
                )

        return "\n".join(parts)

    # ==================================================
    # PREVIOUS SOURCES
    # ==================================================

    def get_previous_sources(
        self,
        history: list[dict] | None = None,
    ) -> list[dict]:

        if not history:
            return []

        for message in reversed(history):

            if message.get("role") != "assistant":
                continue

            sources = message.get(
                "sources",
                [],
            )

            if isinstance(sources, list) and sources:
                return sources

        return []

    # ==================================================
    # HISTORY-AWARE RETRIEVAL QUERY
    # ==================================================

    def build_retrieval_query(
        self,
        question: str,
        history: list[dict] | None = None,
    ) -> str:

        question = question.strip()

        if not history:
            return question

        previous_user = ""
        previous_assistant = ""

        for message in reversed(history[-6:]):

            role = message.get(
                "role",
                "",
            )

            content = (
                message.get(
                    "content",
                    "",
                )
                .strip()
            )

            if not content:
                continue

            if (
                role == "assistant"
                and not previous_assistant
            ):
                previous_assistant = content

            elif (
                role == "user"
                and not previous_user
            ):
                previous_user = content

            if (
                previous_user
                and previous_assistant
            ):
                break

        parts = []

        if previous_user:
            parts.append(
                "Previous question:\n"
                + previous_user
            )

        if previous_assistant:
            parts.append(
                "Previous answer:\n"
                + previous_assistant[:1200]
            )

        parts.append(
            "Current question:\n"
            + question
        )

        return "\n\n".join(parts)

    # ==================================================
    # QUERY VARIANTS
    # ==================================================

    def build_query_variants(
        self,
        question: str,
        history: list[dict] | None = None,
    ) -> list[str]:

        question = question.strip()

        if not question:
            return []

        variants = [
            question
        ]

        # --------------------------------------------------
        # History-aware query
        # --------------------------------------------------

        if history:

            history_query = (
                self.build_retrieval_query(
                    question=question,
                    history=history,
                )
            )

            if (
                history_query
                and history_query not in variants
            ):
                variants.append(
                    history_query
                )

        # --------------------------------------------------
        # Normalized query
        # --------------------------------------------------

        normalized = re.sub(
            r"[&/,]+",
            " ",
            question,
        )

        normalized = re.sub(
            r"\s+",
            " ",
            normalized,
        ).strip()

        if (
            normalized
            and normalized not in variants
        ):
            variants.append(
                normalized
            )

        # --------------------------------------------------
        # Regulation / rule query
        # --------------------------------------------------

        regulation_numbers = re.findall(
            r"\b(?:regulation|rule)\s*(\d+)",
            question,
            flags=re.IGNORECASE,
        )

        if regulation_numbers:

            regulation_query = " ".join(
                f"Regulation {number}"
                for number in regulation_numbers
            )

            if (
                regulation_query
                not in variants
            ):
                variants.append(
                    regulation_query
                )

        return variants

    # ==================================================
    # MERGE RESULTS
    # ==================================================

    def _merge_results(
        self,
        merged: dict,
        results: dict,
    ):

        documents = results.get(
            "documents",
            [[]],
        )[0]

        metadatas = results.get(
            "metadatas",
            [[]],
        )[0]

        distances = results.get(
            "distances",
            [[]],
        )[0]

        ids = results.get(
            "ids",
            [[]],
        )[0]

        for index, document in enumerate(
            documents
        ):

            metadata = (
                metadatas[index]
                if index < len(metadatas)
                else {}
            ) or {}

            distance = (
                distances[index]
                if index < len(distances)
                else None
            )

            vector_id = (
                ids[index]
                if index < len(ids)
                else None
            )

            if not vector_id:
                vector_id = (
                    f"{metadata.get('file_id')}:"
                    f"{metadata.get('chunk_id')}"
                )

            current = {
                "id": vector_id,
                "document": document,
                "metadata": metadata,
                "distance": distance,
            }

            existing = merged.get(
                vector_id
            )

            if existing is None:
                merged[vector_id] = current
                continue

            if (
                distance is not None
                and (
                    existing["distance"] is None
                    or distance
                    < existing["distance"]
                )
            ):
                merged[vector_id] = current

    # ==================================================
    # FORMAT RESULTS
    # ==================================================

    def _format_results(
        self,
        results: list[dict],
    ) -> dict:

        return {
            "ids": [[
                item["id"]
                for item in results
            ]],
            "documents": [[
                item["document"]
                for item in results
            ]],
            "metadatas": [[
                item["metadata"]
                for item in results
            ]],
            "distances": [[
                item["distance"]
                for item in results
            ]],
        }

    # ==================================================
    # TOKENIZATION
    # ==================================================

    @staticmethod
    def _tokenize(
        text: str,
    ) -> list[str]:

        return re.findall(
            r"[a-zA-Z0-9]+",
            text.lower(),
        )

    # ==================================================
    # LEXICAL SCORE
    # ==================================================

    def _lexical_score(
        self,
        query: str,
        document: str,
    ) -> float:

        query_tokens = self._tokenize(query)
        document_tokens = self._tokenize(document)

        if (
            not query_tokens
            or not document_tokens
        ):
            return 0.0

        query_counts = Counter(query_tokens)
        document_counts = Counter(document_tokens)

        total = sum(
            query_counts.values()
        )

        if total <= 0:
            return 0.0

        matched = 0.0

        for token, count in query_counts.items():

            if token in document_counts:
                matched += min(
                    count,
                    document_counts[token],
                )

        return matched / total

    # ==================================================
    # IMPORTANT TERMS
    # ==================================================

    def _important_terms(
        self,
        query: str,
    ) -> set[str]:

        stop_words = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "what",
            "which",
            "who",
            "how",
            "does",
            "do",
            "can",
            "could",
            "would",
            "should",
            "about",
            "tell",
            "me",
            "more",
            "please",
            "of",
            "to",
            "in",
            "on",
            "for",
            "and",
            "or",
            "with",
            "this",
            "that",
        }

        return {
            token
            for token in self._tokenize(query)
            if (
                token not in stop_words
                and len(token) >= 3
            )
        }

    # ==================================================
    # PHRASE SCORE
    # ==================================================

    def _phrase_score(
        self,
        query: str,
        document: str,
    ) -> float:

        query_normalized = re.sub(
            r"\s+",
            " ",
            query.lower(),
        ).strip()

        document_normalized = re.sub(
            r"\s+",
            " ",
            document.lower(),
        ).strip()

        if (
            query_normalized
            and query_normalized in document_normalized
        ):
            return 1.0

        important_terms = (
            self._important_terms(
                query
            )
        )

        if not important_terms:
            return 0.0

        matched = sum(
            1
            for term in important_terms
            if term in document_normalized
        )

        return (
            matched
            / len(important_terms)
        )

    # ==================================================
    # RERANK SCORE
    # ==================================================

    def _rerank_score(
        self,
        query: str,
        item: dict,
    ) -> float:

        distance = item.get(
            "distance"
        )

        if distance is None:
            semantic_score = 0.0
        else:
            semantic_score = max(
                0.0,
                1.0 - float(distance),
            )

        document = item.get(
            "document",
            "",
        )

        lexical_score = (
            self._lexical_score(
                query,
                document,
            )
        )

        phrase_score = (
            self._phrase_score(
                query,
                document,
            )
        )

        return (
            semantic_score * 0.55
            + lexical_score * 0.25
            + phrase_score * 0.20
        )

    # ==================================================
    # RERANK
    # ==================================================

    def _rerank(
        self,
        query: str,
        results: list[dict],
    ) -> list[dict]:

        for item in results:

            item["_score"] = (
                self._rerank_score(
                    query=query,
                    item=item,
                )
            )

        results.sort(
            key=lambda item: (
                item["_score"],
                (
                    0.0
                    if item["distance"] is None
                    else -float(item["distance"])
                ),
            ),
            reverse=True,
        )

        return results

    # ==================================================
    # FINAL RESULT SELECTION
    # ==================================================

    def _select_final_results(
        self,
        results: list[dict],
        limit: int,
        max_chunks_per_file: int = 3,
    ) -> list[dict]:

        if not results:
            return []

        selected = []
        file_counts: dict[str, int] = {}

        for item in results:

            metadata = (
                item.get(
                    "metadata",
                    {},
                )
                or {}
            )

            file_id = (
                metadata.get("file_id")
                or metadata.get("file_name")
                or item["id"]
            )

            current_count = file_counts.get(
                file_id,
                0,
            )

            if current_count >= max_chunks_per_file:
                continue

            selected.append(item)

            file_counts[file_id] = (
                current_count + 1
            )

            if len(selected) >= limit:
                break

        for item in selected:
            item.pop(
                "_score",
                None,
            )

        return selected

    # ==================================================
    # RETRIEVE ALL USER FILES
    # ==================================================

    def retrieve_from_all_files(
        self,
        question: str,
        top_k: int,
        user_id: str,
        history: list[dict] | None = None,
    ) -> dict:

        candidate_k = self._candidate_k()

        merged = {}

        variants = (
            self.build_query_variants(
                question=question,
                history=history,
            )
        )

        for variant in variants:

            results = self.retrieve(
                query=variant,
                top_k=candidate_k,

                # Mandatory tenant boundary.
                user_id=user_id,

                # IMPORTANT:
                # Search all folders for this user.
                folder_id=None,
                file_id=None,
            )

            self._merge_results(
                merged=merged,
                results=results,
            )

        candidates = list(
            merged.values()
        )

        if not candidates:
            return self._format_results([])

        candidates = self._rerank(
            query=question,
            results=candidates,
        )

        final_results = (
            self._select_final_results(
                results=candidates,
                limit=top_k,
                max_chunks_per_file=3,
            )
        )

        return self._format_results(
            final_results
        )

    # ==================================================
    # FOLLOW-UP RETRIEVAL
    # ==================================================

    def retrieve_follow_up(
        self,
        question: str,
        history: list[dict] | None,
        top_k: int,
        user_id: str,
    ) -> dict:

        previous_sources = (
            self.get_previous_sources(
                history
            )
        )

        if not previous_sources:
            return self._format_results([])

        merged = {}

        candidate_k = max(
            top_k * 5,
            20,
        )

        file_ids = []

        for source in previous_sources:

            file_id = source.get(
                "file_id"
            )

            if (
                file_id
                and file_id not in file_ids
            ):
                file_ids.append(
                    file_id
                )

        for file_id in file_ids:

            results = self.retrieve(
                query=question,
                top_k=candidate_k,
                user_id=user_id,
                folder_id=None,
                file_id=file_id,
            )

            self._merge_results(
                merged=merged,
                results=results,
            )

        candidates = list(
            merged.values()
        )

        if not candidates:
            return self._format_results([])

        candidates = self._rerank(
            query=question,
            results=candidates,
        )

        final_results = (
            self._select_final_results(
                results=candidates,
                limit=top_k,
                max_chunks_per_file=3,
            )
        )

        return self._format_results(
            final_results
        )

    # ==================================================
    # HISTORY-AWARE RETRIEVAL
    # ==================================================

    def retrieve_with_history(
        self,
        question: str,
        history: list[dict] | None = None,
        top_k: int | None = None,
        user_id: str | None = None,
        folder_id: str | None = None,
    ):

        if not user_id:
            raise ValueError(
                "user_id is required for retrieval."
            )

        if (
            top_k is None
            or top_k <= 0
        ):
            top_k = self._final_k()

        # Follow-up: search previous files first.
        if self.is_follow_up_question(
            question
        ):

            follow_up_results = (
                self.retrieve_follow_up(
                    question=question,
                    history=history,
                    top_k=top_k,
                    user_id=user_id,
                )
            )

            if follow_up_results["ids"][0]:
                return follow_up_results

        # Normal question: search ALL user files.
        return self.retrieve_from_all_files(
            question=question,
            top_k=top_k,
            user_id=user_id,
            history=history,
        )

    # ==================================================
    # BUILD CONTEXT
    # ==================================================

    def build_context(
        self,
        results,
    ) -> str:

        documents = results.get(
            "documents",
            [[]],
        )[0]

        metadatas = results.get(
            "metadatas",
            [[]],
        )[0]

        context_parts = []

        for document, metadata in zip(
            documents,
            metadatas,
        ):

            metadata = metadata or {}

            context_parts.append(
                (
                    "FILE:\n"
                    f"{metadata.get('file_name')}\n\n"
                    "CONTENT:\n"
                    f"{document}"
                )
            )

        return "\n\n---\n\n".join(
            context_parts
        )

    # ==================================================
    # SYSTEM PROMPT
    # ==================================================

    def get_system_prompt(
        self,
    ) -> str:

        return """
You are a document question-answering assistant.

Answer the CURRENT USER QUESTION using ONLY the
DOCUMENT CONTEXT.

IMPORTANT ANSWER RULES:

1. Read ALL retrieved document content before answering.
2. Do not give an unnecessarily short answer.
3. Give a complete answer supported by the documents.
4. Include all relevant definitions, clauses, conditions,
   exceptions, notes, numbered items, and explanations
   that directly answer the question.
5. If the question asks about a regulation, rule, section,
   definition, or policy, explain the relevant details
   rather than giving only a one-line summary.
6. If the relevant information is spread across multiple
   chunks, combine the chunks into one coherent answer.
7. Preserve the terminology used in the documents.
8. Do not use outside knowledge.
9. Do not invent facts, numbers, dates, regulations,
   rules, definitions, or conclusions.
10. Conversation history is only for resolving references
    such as "this", "that", "it", "more", or
    "tell me more".
11. Never discuss the conversation history.
12. Never explain your reasoning.
13. Never mention RAG, ChromaDB, embeddings, vector search,
    retrieval, chunks, distances, candidate counts,
    internal metadata, or source numbering.
14. Never say "Source 1", "Source 2", "Source 3", etc.
15. Do not mention filenames unless the user asks for them
    or identifying the document is genuinely useful.
16. Use headings or numbered points when they make a
    detailed answer easier to read.
17. If the documents genuinely do not contain enough
    information, say exactly:

"I could not find the answer in the provided documents."

Return the answer directly.
""".strip()

    # ==================================================
    # LLM INPUT
    # ==================================================

    def build_user_input(
        self,
        query: str,
        context: str,
        history: list[dict] | None = None,
    ) -> str:

        history_text = (
            self.build_history(
                history
            )
        )

        if history_text:

            history_section = (
                "CONVERSATION HISTORY:\n"
                "---------------------\n"
                f"{history_text}\n"
                "---------------------"
            )

        else:

            history_section = (
                "CONVERSATION HISTORY:\n"
                "---------------------\n"
                "None.\n"
                "---------------------"
            )

        return f"""
{history_section}

DOCUMENT CONTEXT:
=================
{context}
=================

CURRENT USER QUESTION:
{query}

ANSWER REQUIREMENTS:

- Answer the current question directly.
- Use all relevant information in the document context.
- Do not stop after the first matching sentence.
- Include relevant definitions, sub-points, conditions,
  exceptions, and notes when they are present.
- Combine information from adjacent chunks when they
  belong to the same section.
- Do not mention source numbers or retrieval details.
- Do not use outside knowledge.

Provide a complete, document-grounded answer.
""".strip()

    # ==================================================
    # NORMAL GENERATION
    # ==================================================

    def generate_answer(
        self,
        query: str,
        context: str,
        history: list[dict] | None = None,
    ) -> str:

        user_input = self.build_user_input(
            query=query,
            context=context,
            history=history,
        )

        response = requests.post(
            f"{settings.LM_STUDIO_BASE_URL}/api/v1/chat",
            json={
                "model": settings.LM_STUDIO_MODEL,
                "system_prompt": self.get_system_prompt(),
                "input": user_input,
                "stream": False,
                "temperature": 0.1,
            },
            timeout=180,
        )

        if not response.ok:

            raise RuntimeError(
                "LM Studio request failed:\n"
                f"Status: {response.status_code}\n"
                f"Body: {response.text}"
            )

        data = response.json()

        output = data.get(
            "output",
            [],
        )

        if isinstance(output, list):

            for item in output:

                if (
                    item.get("type")
                    == "message"
                ):

                    content = item.get(
                        "content",
                        "",
                    )

                    if isinstance(
                        content,
                        str,
                    ):
                        return content.strip()

        fallback = data.get(
            "response"
        )

        if isinstance(
            fallback,
            str,
        ):
            return fallback.strip()

        return ""

    # ==================================================
    # STREAMING
    # ==================================================

    def stream_answer(
        self,
        query: str,
        context: str,
        history: list[dict] | None = None,
    ) -> Generator[dict, None, None]:

        user_input = self.build_user_input(
            query=query,
            context=context,
            history=history,
        )

        try:

            response = requests.post(
                f"{settings.LM_STUDIO_BASE_URL}/api/v1/chat",
                json={
                    "model": settings.LM_STUDIO_MODEL,
                    "system_prompt": self.get_system_prompt(),
                    "input": user_input,
                    "stream": True,
                    "temperature": 0.1,
                },
                stream=True,
                timeout=180,
            )

        except requests.RequestException as error:

            yield {
                "type": "error",
                "content": str(error),
            }

            return

        if not response.ok:

            yield {
                "type": "error",
                "content": (
                    "LM Studio request failed: "
                    f"{response.status_code} "
                    f"{response.text}"
                ),
            }

            response.close()
            return

        try:

            for raw_line in response.iter_lines(
                decode_unicode=True
            ):

                if not raw_line:
                    continue

                line = raw_line.strip()

                if not line.startswith("data:"):
                    continue

                payload = (
                    line[5:].strip()
                )

                if not payload:
                    continue

                try:
                    data = json.loads(
                        payload
                    )
                except json.JSONDecodeError:
                    continue

                event_type = data.get(
                    "type",
                    "",
                )

                # ------------------------------------------
                # TOKEN
                # ------------------------------------------

                if event_type == "message.delta":

                    content = data.get(
                        "content",
                        "",
                    )

                    if content:

                        yield {
                            "type": "token",
                            "content": content,
                        }

                # ------------------------------------------
                # ERROR
                # ------------------------------------------

                elif event_type == "error":

                    error_message = (
                        data.get("message")
                        or "LM Studio streaming error."
                    )

                    error_data = data.get(
                        "error"
                    )

                    if isinstance(
                        error_data,
                        dict,
                    ):

                        error_message = (
                            error_data.get(
                                "message",
                                error_message,
                            )
                        )

                    yield {
                        "type": "error",
                        "content": error_message,
                    }

                    return

                # ------------------------------------------
                # COMPLETE
                # ------------------------------------------

                elif event_type == "chat.end":

                    yield {
                        "type": "done",
                    }

                    return

        except requests.RequestException as error:

            yield {
                "type": "error",
                "content": str(error),
            }

        except Exception as error:

            yield {
                "type": "error",
                "content": str(error),
            }

        finally:

            response.close()

    # ==================================================
    # UNIQUE SOURCES
    # ==================================================

    def build_sources(
        self,
        results,
    ) -> list[dict]:

        metadatas = results.get(
            "metadatas",
            [[]],
        )[0]

        distances = results.get(
            "distances",
            [[]],
        )[0]

        sources = []
        seen_files = set()

        for index, metadata in enumerate(
            metadatas
        ):

            metadata = metadata or {}

            file_id = (
                metadata.get(
                    "file_id"
                )
                or metadata.get(
                    "file_name"
                )
            )

            if not file_id:
                continue

            if file_id in seen_files:
                continue

            seen_files.add(
                file_id
            )

            distance = None

            if index < len(distances):
                distance = distances[index]

            sources.append({
                "file_name":
                    metadata.get(
                        "file_name"
                    ),
                "file_id":
                    metadata.get(
                        "file_id"
                    ),
                "path":
                    metadata.get(
                        "path"
                    ),
                "distance":
                    distance,
            })

        return sources

    # ==================================================
    # COMPLETE QUERY
    # ==================================================

    def query(
        self,
        question: str,
        top_k: int | None = None,
        history: list[dict] | None = None,
        user_id: str | None = None,
        folder_id: str | None = None,
    ):

        if not user_id:
            raise ValueError(
                "user_id is required for RAG query."
            )

        final_k = (
            top_k
            if top_k is not None
            and top_k > 0
            else self._final_k()
        )

        results = (
            self.retrieve_with_history(
                question=question,
                history=history,
                top_k=final_k,
                user_id=user_id,
                folder_id=None,
            )
        )

        context = self.build_context(
            results
        )

        answer = self.generate_answer(
            query=question,
            context=context,
            history=history,
        )

        return {
            "answer": answer,
            "sources": self.build_sources(
                results
            ),
        }