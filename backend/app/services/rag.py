import json
import re
from typing import Generator

import requests

from config import settings
from app.services.vectorstore import VectorStore


class RAGService:

    def __init__(self):

        self.vector_store = VectorStore()

    # ==================================================
    # BASIC RETRIEVAL
    # ==================================================

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        user_id: str | None = None,
        folder_id: str | None = None
    ):

        if top_k is None or top_k <= 0:
            top_k = settings.TOP_K

        return self.vector_store.search(
            query=query,
            top_k=top_k,
            user_id=user_id,
            folder_id=folder_id
        )

    # ==================================================
    # BUILD HISTORY FOR RETRIEVAL
    # ==================================================

    def build_retrieval_query(
        self,
        question: str,
        history: list[dict] | None = None
    ) -> str:

        question = question.strip()

        if not history:
            return question

        # Only previous USER questions are useful for
        # resolving follow-up references.
        previous_questions = []

        for message in history:

            if message.get("role") != "user":
                continue

            content = (
                message.get(
                    "content",
                    ""
                )
                .strip()
            )

            if not content:
                continue

            previous_questions.append(
                content
            )

        # Keep only the latest few.
        previous_questions = (
            previous_questions[-3:]
        )

        if not previous_questions:
            return question

        return (
            "Current question: "
            f"{question}\n"
            "Previous user questions: "
            + " | ".join(
                previous_questions
            )
        )

    # ==================================================
    # QUERY VARIANTS
    # ==================================================

    def build_query_variants(
        self,
        question: str,
        history: list[dict] | None = None
    ) -> list[str]:

        variants = []

        question = question.strip()

        if question:
            variants.append(
                question
            )

        retrieval_query = (
            self.build_retrieval_query(
                question=question,
                history=history
            )
        )

        if (
            retrieval_query
            and retrieval_query
            not in variants
        ):

            variants.append(
                retrieval_query
            )

        # --------------------------------------------------
        # Normalized variant.
        #
        # Example:
        # "Regulation 38 & 39"
        #
        # becomes:
        # "Regulation 38 39"
        # --------------------------------------------------

        normalized = re.sub(
            r"[&/,]+",
            " ",
            question
        )

        normalized = re.sub(
            r"\s+",
            " ",
            normalized
        ).strip()

        if (
            normalized
            and normalized not in variants
        ):

            variants.append(
                normalized
            )

        # --------------------------------------------------
        # Regulation-specific variant.
        #
        # "Regulation 38 & 39"
        #
        # becomes:
        # "Regulation 38 Regulation 39"
        # --------------------------------------------------

        regulation_numbers = re.findall(
            r"\b(?:regulation|rule)\s*(\d+)",
            question,
            flags=re.IGNORECASE
)

        if len(
            regulation_numbers
        ) >= 1:

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
    # MULTI-QUERY RETRIEVAL
    # ==================================================

    def retrieve_with_history(
        self,
        question: str,
        history: list[dict] | None = None,
        top_k: int | None = None,
        user_id: str | None = None,
        folder_id: str | None = None
    ):

        if top_k is None or top_k <= 0:
            top_k = settings.TOP_K

        # Use a little more retrieval internally.
        retrieval_k = max(
            top_k,
            5
        )

        variants = (
            self.build_query_variants(
                question=question,
                history=history
            )
        )

        merged = {}

        # ==================================================
        # SEARCH EACH VARIANT
        # ==================================================

        for variant in variants:

            results = self.retrieve(
                query=variant,
                top_k=retrieval_k,
                user_id=user_id,
                folder_id=folder_id
            )

            documents = results.get(
                "documents",
                [[]]
            )[0]

            metadatas = results.get(
                "metadatas",
                [[]]
            )[0]

            distances = results.get(
                "distances",
                [[]]
            )[0]

            ids = results.get(
                "ids",
                [[]]
            )[0]

            for index, document in enumerate(
                documents
            ):

                metadata = {}

                if index < len(
                    metadatas
                ):
                    metadata = (
                        metadatas[index]
                        or {}
                    )

                distance = None

                if index < len(
                    distances
                ):
                    distance = (
                        distances[index]
                    )

                vector_id = None

                if index < len(ids):
                    vector_id = ids[index]

                # Chroma normally gives IDs.
                # Fallback prevents crashes if unavailable.
                if not vector_id:

                    vector_id = (
                        f"{metadata.get('file_id')}:"
                        f"{metadata.get('chunk_id')}"
                    )

                # Keep the strongest score.
                old = merged.get(
                    vector_id
                )

                if (
                    old is None
                    or (
                        distance is not None
                        and (
                            old["distance"] is None
                            or distance <
                            old["distance"]
                        )
                    )
                ):

                    merged[
                        vector_id
                    ] = {
                        "id": vector_id,
                        "document": document,
                        "metadata": metadata,
                        "distance": distance,
                    }

        # ==================================================
        # SORT BY DISTANCE
        # ==================================================

        merged_results = list(
            merged.values()
        )

        merged_results.sort(
            key=lambda item: (
                item["distance"]
                if item["distance"] is not None
                else 999999
            )
        )

        merged_results = merged_results[
            :top_k
        ]

        # ==================================================
        # REBUILD CHROMA-LIKE RESULT
        # ==================================================

        return {
            "ids": [[
                item["id"]
                for item in merged_results
            ]],

            "documents": [[
                item["document"]
                for item in merged_results
            ]],

            "metadatas": [[
                item["metadata"]
                for item in merged_results
            ]],

            "distances": [[
                item["distance"]
                for item in merged_results
            ]]
        }

    # ==================================================
    # BUILD CONTEXT
    # ==================================================

    def build_context(
        self,
        results
    ):

        documents = results.get(
            "documents",
            [[]]
        )[0]

        metadatas = results.get(
            "metadatas",
            [[]]
        )[0]

        distances = results.get(
            "distances",
            [[]]
        )[0]

        context_parts = []

        for index, document in enumerate(
            documents,
            start=1
        ):

            metadata = {}

            if index - 1 < len(
                metadatas
            ):

                metadata = (
                    metadatas[
                        index - 1
                    ]
                    or {}
                )

            distance = None

            if index - 1 < len(
                distances
            ):

                distance = (
                    distances[
                        index - 1
                    ]
                )

            context_parts.append(
                f"""
SOURCE {index}

FILE:
{metadata.get("file_name")}

PATH:
{metadata.get("path")}

CHUNK:
{metadata.get("chunk_id")}

CONTENT:
{document}
""".strip()
            )

        return "\n\n".join(
            context_parts
        )

    # ==================================================
    # BUILD CONVERSATION HISTORY
    # ==================================================

    def build_history(
        self,
        messages: list[dict] | None = None
    ) -> str:

        if not messages:
            return ""

        parts = []

        # Only keep a small recent window.
        recent_messages = (
            messages[-6:]
        )

        for message in recent_messages:

            role = message.get(
                "role",
                ""
            )

            content = (
                message.get(
                    "content",
                    ""
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

        return "\n".join(
            parts
        )

    # ==================================================
    # SYSTEM PROMPT
    # ==================================================

    def get_system_prompt(self):

        return """
You are a document question-answering assistant.

Answer ONLY the user's current question.

The DOCUMENT CONTEXT is the only source of factual
information.

Rules:

1. Use the document context for factual answers.
2. Do not use outside knowledge.
3. Do not invent facts, numbers, dates,
   regulations, rules, definitions, or conclusions.
4. Conversation history is ONLY for understanding
   references in the current question.
5. Never discuss conversation history in your answer.
6. Never say "based on the conversation history".
7. Never describe your reasoning process.
8. Never talk about retrieval, embeddings, chunks,
   vector databases, or the RAG system.
9. Do not invent source names.
10. If the document context contains the answer,
    answer directly.
11. If the document context genuinely does not
    contain enough information, say exactly:

"I could not find the answer in the provided documents."

Keep the answer concise and factual.
""".strip()

    # ==================================================
    # BUILD LLM INPUT
    # ==================================================

    def build_user_input(
        self,
        query: str,
        context: str,
        history: list[dict] | None = None
    ) -> str:

        history_text = self.build_history(
            history
        )

        if history_text:

            history_section = f"""
CONVERSATION HISTORY:
---------------------
{history_text}
---------------------
""".strip()

        else:

            history_section = """
CONVERSATION HISTORY:
---------------------
None.
---------------------
""".strip()

        return f"""
{history_section}

DOCUMENT CONTEXT:
=================
{context}
=================

CURRENT USER QUESTION:
{query}

Answer the CURRENT USER QUESTION using only
the DOCUMENT CONTEXT.

Do not explain how you interpreted the history.
""".strip()

    # ==================================================
    # NORMAL GENERATION
    # ==================================================

    def generate_answer(
        self,
        query: str,
        context: str,
        history: list[dict] | None = None
    ) -> str:

        user_input = self.build_user_input(
            query=query,
            context=context,
            history=history
        )

        response = requests.post(
            f"{settings.LM_STUDIO_BASE_URL}/api/v1/chat",
            json={
                "model":
                    settings.LM_STUDIO_MODEL,

                "system_prompt":
                    self.get_system_prompt(),

                "input":
                    user_input,

                "stream":
                    False,

                "temperature":
                    0.1,
            },
            timeout=180
        )

        response.raise_for_status()

        data = response.json()

        output = data.get(
            "output",
            []
        )

        if isinstance(
            output,
            list
        ):

            for item in output:

                if (
                    item.get("type")
                    == "message"
                ):

                    content = item.get(
                        "content",
                        ""
                    )

                    if isinstance(
                        content,
                        str
                    ):

                        return content.strip()

        fallback = data.get(
            "response"
        )

        if isinstance(
            fallback,
            str
        ):

            return fallback.strip()

        return ""

    # ==================================================
    # STREAMING GENERATION
    # ==================================================

    def stream_answer(
        self,
        query: str,
        context: str,
        history: list[dict] | None = None
    ) -> Generator[dict, None, None]:

        user_input = self.build_user_input(
            query=query,
            context=context,
            history=history
        )

        response = requests.post(
            f"{settings.LM_STUDIO_BASE_URL}/api/v1/chat",
            json={
                "model":
                    settings.LM_STUDIO_MODEL,

                "system_prompt":
                    self.get_system_prompt(),

                "input":
                    user_input,

                "stream":
                    True,

                "temperature":
                    0.1,
            },
            stream=True,
            timeout=180
        )

        response.raise_for_status()

        streamed_text = ""

        try:

            for raw_line in response.iter_lines(
                decode_unicode=True
            ):

                if not raw_line:
                    continue

                line = raw_line.strip()

                if not line.startswith(
                    "data:"
                ):
                    continue

                payload = (
                    line[5:]
                    .strip()
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
                    ""
                )

                # ------------------------------------------
                # Delta
                # ------------------------------------------

                if event_type == (
                    "message.delta"
                ):

                    content = data.get(
                        "content",
                        ""
                    )

                    if content:

                        streamed_text += content

                        yield {
                            "type":
                                "token",

                            "content":
                                content
                        }

                # ------------------------------------------
                # Error
                # ------------------------------------------

                elif event_type == "error":

                    error_message = (
                        data.get(
                            "message"
                        )
                        or
                        "LM Studio streaming error."
                    )

                    error_data = data.get(
                        "error"
                    )

                    if isinstance(
                        error_data,
                        dict
                    ):

                        error_message = (
                            error_data.get(
                                "message",
                                error_message
                            )
                        )

                    yield {
                        "type":
                            "error",

                        "content":
                            error_message
                    }

                    return

                # ------------------------------------------
                # Chat completed
                # ------------------------------------------

                elif event_type == "chat.end":

                    final_text = ""

                    result = data.get(
                        "result"
                    )

                    if isinstance(
                        result,
                        dict
                    ):

                        output = (
                            result.get(
                                "output",
                                []
                            )
                        )

                        if isinstance(
                            output,
                            list
                        ):

                            for item in output:

                                if (
                                    item.get(
                                        "type"
                                    )
                                    == "message"
                                ):

                                    content = (
                                        item.get(
                                            "content",
                                            ""
                                        )
                                    )

                                    if isinstance(
                                        content,
                                        str
                                    ):

                                        final_text = (
                                            content
                                        )

                                    break

                    # --------------------------------------
                    # Fallback to top-level output
                    # --------------------------------------

                    if not final_text:

                        output = data.get(
                            "output",
                            []
                        )

                        if isinstance(
                            output,
                            list
                        ):

                            for item in output:

                                if (
                                    item.get(
                                        "type"
                                    )
                                    == "message"
                                ):

                                    content = (
                                        item.get(
                                            "content",
                                            ""
                                        )
                                    )

                                    if isinstance(
                                        content,
                                        str
                                    ):

                                        final_text = (
                                            content
                                        )

                                    break

                    # --------------------------------------
                    # If no delta arrived, send final text.
                    # --------------------------------------

                    if (
                        final_text
                        and not streamed_text
                    ):

                        yield {
                            "type":
                                "token",

                            "content":
                                final_text
                        }

                    yield {
                        "type":
                            "done"
                    }

                    return

        except requests.RequestException as error:

            yield {
                "type":
                    "error",

                "content":
                    str(error)
            }

        except Exception as error:

            yield {
                "type":
                    "error",

                "content":
                    str(error)
            }

        finally:

            response.close()

    # ==================================================
    # COMPLETE RAG QUERY
    # ==================================================

    def query(
        self,
        question: str,
        top_k: int | None = None,
        history: list[dict] | None = None,
        user_id: str | None = None,
        folder_id: str | None = None
    ):

        # ----------------------------------------------
        # IMPORTANT:
        # History-aware multi-query retrieval
        # ----------------------------------------------

        results = (
            self.retrieve_with_history(
                question=question,
                history=history,
                top_k=top_k,
                user_id=user_id,
                folder_id=folder_id
            )
        )

        context = self.build_context(
            results
        )

        answer = self.generate_answer(
            query=question,
            context=context,
            history=history
        )

        sources = []

        metadatas = results.get(
            "metadatas",
            [[]]
        )[0]

        distances = results.get(
            "distances",
            [[]]
        )[0]

        for index, metadata in enumerate(
            metadatas
        ):

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

                "chunk_id":
                    metadata.get(
                        "chunk_id"
                    ),

                "path":
                    metadata.get(
                        "path"
                    ),

                "distance":
                    distance
            })

        return {
            "answer":
                answer,

            "sources":
                sources
        }