import re
from collections import Counter
from typing import Generator

from app.services.groq import GroqService
from app.services.vectorstore import VectorStore
from config import settings


class RAGService:

    def __init__(self):

        self.vector_store = VectorStore()
        self.groq = GroqService()

    # ==================================================
    # CONFIG
    # ==================================================

    def _final_k(self) -> int:
        try:
            value = int(
                getattr(
                    settings,
                    "TOP_K",
                    5,
                )
            )
        except (TypeError, ValueError):
            value = 5

        return max(
            1,
            min(value, 10),
        )

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

        return max(
            20,
            min(value, 300),
        )

    def _max_context_chars(self) -> int:
        """
        Keeps the final Groq request below the
        current TPM constraint.
        """
        return 12000

    def _max_history_chars(self) -> int:
        return 3000

    def _max_output_tokens(self) -> int:
        return 1200

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

        if (
            top_k is None
            or top_k <= 0
        ):

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
            "why",
            "why is that",
            "how so",
        }

        return normalized in follow_up_phrases

    # ==================================================
    # HISTORY
    # ==================================================

    def build_history(
        self,
        messages: list[dict] | None = None,
    ) -> str:

        if not messages:
            return ""

        recent = messages[-4:]

        parts = []
        total_chars = 0

        for message in recent:

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

            content = self._trim_text(
                content,
                800,
            )

            block = (
                f"{role.upper()}: "
                f"{content}"
            )

            if (
                total_chars
                + len(block)
                > self._max_history_chars()
            ):
                break

            parts.append(
                block
            )

            total_chars += len(
                block
            )

        return "\n".join(
            parts
        )

    def _build_compact_history(
        self,
        messages: list[dict] | None = None,
    ) -> str:

        return self.build_history(
            messages
        )

    # ==================================================
    # TRIM
    # ==================================================

    @staticmethod
    def _trim_text(
        text: str,
        max_chars: int,
    ) -> str:

        if not text:
            return ""

        if len(text) <= max_chars:
            return text

        return (
            text[:max_chars]
            + "\n\n[truncated]"
        )

    # ==================================================
    # PREVIOUS SOURCES
    # ==================================================

    def get_previous_sources(
        self,
        history: list[dict] | None = None,
    ) -> list[dict]:

        if not history:
            return []

        for message in reversed(
            history
        ):

            if (
                message.get("role")
                != "assistant"
            ):
                continue

            sources = message.get(
                "sources",
                [],
            )

            if (
                isinstance(
                    sources,
                    list,
                )
                and sources
            ):
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

        for message in reversed(
            history[-4:]
        ):

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

            content = self._trim_text(
                content,
                800,
            )

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
                + previous_assistant
            )

        parts.append(
            "Current question:\n"
            + question
        )

        return "\n\n".join(
            parts
        )

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

        # ------------------------------------------
        # History-aware variant
        # ------------------------------------------

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

        # ------------------------------------------
        # Normalized variant
        # ------------------------------------------

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

        # ------------------------------------------
        # Regulation / rule variant
        # ------------------------------------------

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

        query_tokens = (
            self._tokenize(
                query
            )
        )

        document_tokens = (
            self._tokenize(
                document
            )
        )

        if (
            not query_tokens
            or not document_tokens
        ):

            return 0.0

        query_counts = Counter(
            query_tokens
        )

        document_counts = Counter(
            document_tokens
        )

        total = sum(
            query_counts.values()
        )

        if total <= 0:
            return 0.0

        matched = 0.0

        for token, count in (
            query_counts.items()
        ):

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
            for token in self._tokenize(
                query
            )
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
            and query_normalized
            in document_normalized
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
                    else -float(
                        item["distance"]
                    )
                ),
            ),
            reverse=True,
        )

        return results

    # ==================================================
    # FINAL SEMANTIC SELECTION
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
                metadata.get(
                    "file_id"
                )
                or metadata.get(
                    "file_name"
                )
                or item["id"]
            )

            current_count = (
                file_counts.get(
                    file_id,
                    0,
                )
            )

            if (
                current_count
                >= max_chunks_per_file
            ):
                continue

            selected.append(
                item
            )

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

        candidate_k = (
            self._candidate_k()
        )

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

                # Normal chat searches all folders.
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

            return self._format_results(
                []
            )

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

            return self._format_results(
                []
            )

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

            return self._format_results(
                []
            )

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
    # ADJACENT CHUNK EXPANSION
    # ==================================================

    def _expand_adjacent_chunks(
        self,
        results: dict,
        user_id: str,
        radius: int = 1,
    ) -> dict:
        """
        Expand each semantic result with neighboring chunks
        from the same file.

        Example:

            semantic result: chunk 5

            expansion:
                4
                5
                6

        This helps documents where a regulation/section
        continues across chunk boundaries.
        """

        metadatas = results.get(
            "metadatas",
            [[]],
        )[0]

        if not metadatas:

            return results

        grouped: dict[str, list[int]] = {}

        for metadata in metadatas:

            metadata = metadata or {}

            file_id = metadata.get(
                "file_id"
            )

            chunk_id = metadata.get(
                "chunk_id"
            )

            if (
                not file_id
                or chunk_id is None
            ):
                continue

            grouped.setdefault(
                file_id,
                []
            ).append(
                int(chunk_id)
            )

        merged = {}

        documents = results.get(
            "documents",
            [[]],
        )[0]

        ids = results.get(
            "ids",
            [[]],
        )[0]

        distances = results.get(
            "distances",
            [[]],
        )[0]

        # ------------------------------------------
        # Keep original semantic results
        # ------------------------------------------

        for index, metadata in enumerate(
            metadatas
        ):

            metadata = metadata or {}

            if index >= len(ids):
                continue

            vector_id = ids[index]

            merged[vector_id] = {
                "id": vector_id,

                "document":
                    documents[index],

                "metadata":
                    metadata,

                "distance": (
                    distances[index]
                    if index < len(distances)
                    else None
                ),
            }

        # ------------------------------------------
        # Load adjacent chunks
        # ------------------------------------------

        for file_id, chunk_ids in (
            grouped.items()
        ):

            adjacent = (
                self.vector_store.get_adjacent_chunks(
                    user_id=user_id,
                    file_id=file_id,
                    chunk_ids=chunk_ids,
                    radius=radius,
                )
            )

            adjacent_ids = adjacent.get(
                "ids",
                [],
            )

            adjacent_docs = adjacent.get(
                "documents",
                [],
            )

            adjacent_meta = adjacent.get(
                "metadatas",
                [],
            )

            for index, vector_id in enumerate(
                adjacent_ids
            ):

                if vector_id in merged:
                    continue

                if (
                    index >= len(adjacent_docs)
                    or index >= len(adjacent_meta)
                ):
                    continue

                merged[vector_id] = {
                    "id": vector_id,

                    "document":
                        adjacent_docs[index],

                    "metadata":
                        adjacent_meta[index],

                    # Neighboring chunks do not have
                    # semantic distances because they were
                    # retrieved by adjacency rather than
                    # vector search.
                    "distance": None,
                }

        # ------------------------------------------
        # Document order
        # ------------------------------------------

        ordered = list(
            merged.values()
        )

        ordered.sort(
            key=lambda item: (
                item["metadata"].get(
                    "file_id",
                    "",
                ),

                int(
                    item["metadata"].get(
                        "chunk_id",
                        0,
                    )
                ),
            )
        )

        return self._format_results(
            ordered
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

        # ------------------------------------------
        # Explicit follow-up
        # ------------------------------------------

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

                return (
                    self._expand_adjacent_chunks(
                        results=follow_up_results,
                        user_id=user_id,
                        radius=1,
                    )
                )

        # ------------------------------------------
        # Normal question
        #
        # Searches ALL files owned by this user.
        # ------------------------------------------

        results = (
            self.retrieve_from_all_files(
                question=question,
                top_k=top_k,
                user_id=user_id,
                history=history,
            )
        )

        return (
            self._expand_adjacent_chunks(
                results=results,
                user_id=user_id,
                radius=1,
            )
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

        remaining = (
            self._max_context_chars()
        )

        for document, metadata in zip(
            documents,
            metadatas,
        ):

            if remaining <= 0:
                break

            metadata = metadata or {}

            block = (
                "FILE:\n"
                f"{metadata.get('file_name')}\n\n"
                "CHUNK {chunk_id}:\n"
                f"{metadata.get('chunk_id')}\n\n"
                "CONTENT:\n"
                f"{document}"
            )

            if len(block) > remaining:

                block = (
                    block[:remaining]
                    + "\n\n[truncated]"
                )

            context_parts.append(
                block
            )

            remaining -= len(block)

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

Rules:

1. Read all provided document context before answering.
2. Use only information supported by the documents.
3. Combine information from multiple chunks when necessary.
4. Preserve the original order and meaning of numbered
   clauses, definitions, rules, and regulations.
5. Do not use outside knowledge.
6. Do not invent facts, dates, numbers, regulations,
   rules, definitions, or conclusions.
7. Conversation history is only for resolving references
   such as "this", "that", "it", "more", or
   "tell me more".
8. Never discuss conversation history.
9. Never explain your reasoning.
10. Never mention RAG, ChromaDB, PostgreSQL, pgvector,
    embeddings, vector search, retrieval, chunks,
    distances, candidate counts, or internal metadata.
11. Never say "Source 1", "Source 2", "Source 3", etc.
12. Do not mention filenames unless useful or explicitly
    requested.
13. Do not stop at the first matching sentence when the
    context contains additional relevant details.
14. For regulations, rules, policies, and definitions,
    include relevant sub-points, conditions, exceptions,
    notes, and numbered clauses.
15. Adjacent chunks may contain continuations of the same
    section. Combine them into one coherent answer.
16. If the documents genuinely do not contain enough
    information, say:

"I could not find the answer in the provided documents."

Answer directly and naturally.
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
            self._build_compact_history(
                history
            )
        )

        if not history_text:

            history_text = "None."

        return f"""
RECENT CONVERSATION:
{history_text}

DOCUMENT CONTEXT:
{context}

CURRENT USER QUESTION:
{query}

Answer the current question using the document context.

Use all relevant information available.
Combine adjacent chunks when they belong to the
same section or regulation.

Do not stop after the first matching sentence.

Do not mention retrieval, RAG, embeddings, chunks,
distances, source numbers, or internal metadata.

Do not use outside knowledge.

Return a complete, document-grounded answer.
""".strip()

    # ==================================================
    # GROQ GENERATION
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

        try:

            return self.groq.generate_text(
                system_prompt=
                    self.get_system_prompt(),

                user_prompt=
                    user_input,

                temperature=0.1,

                max_tokens=
                    self._max_output_tokens(),
            )

        except Exception as error:

            raise RuntimeError(
                "Groq generation failed: "
                f"{error}"
            ) from error

    # ==================================================
    # GROQ STREAMING
    # ==================================================

    def stream_answer(
        self,
        query: str,
        context: str,
        history: list[dict] | None = None,
    ) -> Generator[
        dict,
        None,
        None,
    ]:

        user_input = self.build_user_input(
            query=query,
            context=context,
            history=history,
        )

        try:

            for token in (
                self.groq.stream_text(
                    system_prompt=
                        self.get_system_prompt(),

                    user_prompt=
                        user_input,

                    temperature=0.1,

                    max_tokens=
                        self._max_output_tokens(),
                )
            ):

                if token:

                    yield {
                        "type": "token",
                        "content": token,
                    }

            yield {
                "type": "done",
            }

        except Exception as error:

            yield {
                "type": "error",
                "content": str(error),
            }

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

            if index < len(
                distances
            ):

                distance = distances[
                    index
                ]

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
            if (
                top_k is not None
                and top_k > 0
            )
            else self._final_k()
        )

        results = (
            self.retrieve_with_history(
                question=question,
                history=history,
                top_k=final_k,
                user_id=user_id,

                # Normal chat searches all user files.
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

            "sources":
                self.build_sources(
                    results
                ),
        }