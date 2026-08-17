import base64

from groq import Groq

from config import settings


FALLBACK_LLM_MODEL = "openai/gpt-oss-120b"
FALLBACK_VISION_MODEL = "qwen/qwen3.6-27b"

REQUEST_TIMEOUT = 60.0


class GroqService:

    def __init__(self):

        if not settings.GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY is not configured."
            )

        self.client = Groq(
            api_key=settings.GROQ_API_KEY,
            timeout=REQUEST_TIMEOUT,
        )

        # ------------------------------------------
        # Models
        # ------------------------------------------

        self.llm_model = (
            settings.GROQ_LLM_MODEL.strip()
            or FALLBACK_LLM_MODEL
        )

        self.vision_model = (
            settings.GROQ_VISION_MODEL.strip()
            or FALLBACK_VISION_MODEL
        )

        print("=" * 60)
        print("GROQ SERVICE INITIALIZED")
        print("=" * 60)
        print(
            f"LLM model: {self.llm_model}"
        )
        print(
            f"Vision model: {self.vision_model}"
        )
        print(
            f"Request timeout: {REQUEST_TIMEOUT}s"
        )
        print("=" * 60)

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

        try:

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
                    timeout=REQUEST_TIMEOUT,
                )
            )

        except Exception as error:

            print(
                f"Groq generate_text failed "
                f"with {self.llm_model}: "
                f"{type(error).__name__}: {error}"
            )

            print(
                f"Retrying with "
                f"{FALLBACK_LLM_MODEL}"
            )

            response = (
                self.client.chat.completions.create(
                    model=FALLBACK_LLM_MODEL,
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
                    timeout=REQUEST_TIMEOUT,
                )
            )

        content = (
            response
            .choices[0]
            .message
            .content
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

        model_to_use = self.llm_model

        try:

            stream = (
                self.client.chat.completions.create(
                    model=model_to_use,
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
                    timeout=REQUEST_TIMEOUT,
                )
            )

        except Exception as error:

            print(
                f"Groq stream_text failed "
                f"with {model_to_use}: "
                f"{type(error).__name__}: {error}"
            )

            print(
                f"Retrying with "
                f"{FALLBACK_LLM_MODEL}"
            )

            # IMPORTANT:
            # Your old code incorrectly used
            # FALLBACK_VISION_MODEL here.
            stream = (
                self.client.chat.completions.create(
                    model=FALLBACK_LLM_MODEL,
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
                    timeout=REQUEST_TIMEOUT,
                )
            )

        for chunk in stream:

            if not chunk.choices:
                continue

            content = (
                chunk
                .choices[0]
                .delta
                .content
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

        # ------------------------------------------
        # Validate image
        # ------------------------------------------

        if not image_bytes:
            raise ValueError(
                "image_bytes cannot be empty."
            )

        if not mime_type:
            mime_type = "image/png"

        print("=" * 60)
        print("GROQ VISION REQUEST")
        print("=" * 60)

        print(
            f"Vision model: "
            f"{self.vision_model}"
        )

        print(
            f"MIME type: "
            f"{mime_type}"
        )

        print(
            f"Image bytes: "
            f"{len(image_bytes)}"
        )

        # ------------------------------------------
        # Base64
        # ------------------------------------------

        encoded = (
            base64
            .b64encode(image_bytes)
            .decode("utf-8")
        )

        data_url = (
            f"data:{mime_type};base64,{encoded}"
        )

        print(
            f"Base64 characters: "
            f"{len(encoded)}"
        )

        # ------------------------------------------
        # Message
        # ------------------------------------------

        messages = [
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
        ]

        model_to_use = self.vision_model

        # ==========================================
        # PRIMARY VISION MODEL
        # ==========================================

        try:

            print(
                f"Sending image to "
                f"{model_to_use}..."
            )

            response = (
                self.client
                .chat
                .completions
                .create(
                    model=model_to_use,
                    messages=messages,
                    temperature=temperature,
                    max_completion_tokens=max_tokens,
                    stream=False,
                    timeout=REQUEST_TIMEOUT,
                )
            )

            print(
                "Groq Vision request succeeded."
            )

        except Exception as error:

            print("=" * 60)
            print("GROQ VISION PRIMARY MODEL FAILED")
            print("=" * 60)

            print(
                f"Model: {model_to_use}"
            )

            print(
                f"Error type: "
                f"{type(error).__name__}"
            )

            print(
                f"Error: {error}"
            )

            print("=" * 60)

            # ======================================
            # FALLBACK
            # ======================================

            if (
                model_to_use
                == FALLBACK_VISION_MODEL
            ):

                # Do not retry the exact same
                # model if it already failed.
                raise

            print(
                f"Retrying with "
                f"{FALLBACK_VISION_MODEL}..."
            )

            response = (
                self.client
                .chat
                .completions
                .create(
                    model=FALLBACK_VISION_MODEL,
                    messages=messages,
                    temperature=temperature,
                    max_completion_tokens=max_tokens,
                    stream=False,
                    timeout=REQUEST_TIMEOUT,
                )
            )

            print(
                "Fallback Vision request succeeded."
            )

        # ------------------------------------------
        # Extract response
        # ------------------------------------------

        content = (
            response
            .choices[0]
            .message
            .content
        )

        if not isinstance(
            content,
            str,
        ):
            return ""

        content = content.strip()

        print(
            f"Vision output characters: "
            f"{len(content)}"
        )

        return content

    # ==================================================
    # OCR
    # ==================================================

    def ocr_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/png",
    ) -> str:

        print("=" * 60)
        print("OCR REQUEST")
        print("=" * 60)

        print(
            f"MIME: {mime_type}"
        )

        print(
            f"Image size: "
            f"{len(image_bytes)} bytes"
        )

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
- subclauses
- tables
- numerical values
- punctuation
- original reading order
- page structure where possible

This may be a scanned legal, regulatory,
administrative, or government document.

Preserve the wording as accurately as possible.

Do NOT:

- summarize
- explain
- interpret
- correct
- rewrite
- add commentary
- invent missing text

If a word is genuinely unreadable,
do not fabricate it.

Return ONLY the extracted document text.
""".strip()

        try:

            text = self.analyze_image(
                image_bytes=image_bytes,
                mime_type=mime_type,
                prompt=prompt,
                temperature=0.0,
                max_tokens=4096,
            )

            print(
                f"OCR completed: "
                f"{len(text)} characters"
            )

            return text.strip()

        except Exception as error:

            print("=" * 60)
            print("OCR FAILED")
            print("=" * 60)

            print(
                f"Error type: "
                f"{type(error).__name__}"
            )

            print(
                f"Error: {error}"
            )

            print("=" * 60)

            raise