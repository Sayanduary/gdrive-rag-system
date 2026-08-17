import base64

from groq import Groq

from config import settings


class GroqService:

    def __init__(self):

        if not settings.GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY is not configured."
            )

        self.client = Groq(
            api_key=settings.GROQ_API_KEY
        )

        self.llm_model = (
            settings.GROQ_LLM_MODEL
        )

        self.vision_model = (
            settings.GROQ_VISION_MODEL
        )

    # ==================================================
    # TEXT / RAG GENERATION
    # ==================================================

    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> str:

        response = (
            self.client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                temperature=temperature,
                max_completion_tokens=max_tokens,
                stream=False,
            )
        )

        content = (
            response.choices[0]
            .message.content
        )

        return (
            content.strip()
            if isinstance(content, str)
            else ""
        )

    # ==================================================
    # TEXT STREAMING
    # ==================================================

    def stream_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ):

        stream = (
            self.client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                temperature=temperature,
                max_completion_tokens=max_tokens,
                stream=True,
            )
        )

        for chunk in stream:

            if not chunk.choices:
                continue

            content = (
                chunk.choices[0]
                .delta.content
            )

            if content:
                yield content

    # ==================================================
    # VISION
    # ==================================================

    def analyze_image(
        self,
        image_bytes: bytes,
        mime_type: str,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> str:

        if not image_bytes:
            raise ValueError(
                "image_bytes cannot be empty."
            )

        encoded = base64.b64encode(
            image_bytes
        ).decode("utf-8")

        data_url = (
            f"data:{mime_type};base64,"
            f"{encoded}"
        )

        response = (
            self.client.chat.completions.create(
                model=self.vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt,
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": data_url,
                                },
                            },
                        ],
                    }
                ],
                temperature=temperature,
                max_completion_tokens=max_tokens,
                stream=False,
            )
        )

        content = (
            response.choices[0]
            .message.content
        )

        return (
            content.strip()
            if isinstance(content, str)
            else ""
        )

    # ==================================================
    # OCR
    # ==================================================

    def ocr_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/png",
    ) -> str:

        prompt = """
Extract ALL readable text from this document image.

This is OCR, not summarization.

Preserve:

- headings
- section numbers
- regulation numbers
- rule numbers
- paragraphs
- dates
- names
- bullet points
- numbered clauses
- tables
- numerical values
- punctuation
- original reading order

Do not summarize.
Do not explain.
Do not add commentary.
Do not invent missing text.

Return only the extracted document text.
""".strip()

        return self.analyze_image(
            image_bytes=image_bytes,
            mime_type=mime_type,
            prompt=prompt,
            temperature=0.0,
            max_tokens=4096,
        )