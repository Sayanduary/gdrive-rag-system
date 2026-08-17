import base64

from groq import Groq

from config import settings


FALLBACK_LLM_MODEL = "openai/gpt-oss-120b"
FALLBACK_VISION_MODEL = "qwen/qwen3.6-27b"


class GroqService:

    def __init__(self):

        if not settings.GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY is not configured."
            )

        self.client = Groq(
            api_key=settings.GROQ_API_KEY
        )

        # Set configured or fallback models
        self.llm_model = settings.GROQ_LLM_MODEL.strip() or FALLBACK_LLM_MODEL
        self.vision_model = settings.GROQ_VISION_MODEL.strip() or FALLBACK_VISION_MODEL

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
            response = self.client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_completion_tokens=max_tokens,
                stream=False,
            )
        except Exception as err:
            print(f"Groq generate_text failed with {self.llm_model}: {err}. Retrying with {FALLBACK_LLM_MODEL}")
            response = self.client.chat.completions.create(
                model=FALLBACK_LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_completion_tokens=max_tokens,
                stream=False,
            )

        content = response.choices[0].message.content
        return content.strip() if isinstance(content, str) else ""

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
            stream = self.client.chat.completions.create(
                model=model_to_use,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_completion_tokens=max_tokens,
                stream=True,
            )
        except Exception as err:
            print(f"Groq stream_text failed with {model_to_use}: {err}. Retrying with {FALLBACK_LLM_MODEL}")
            stream = self.client.chat.completions.create(
                model=FALLBACK_VISION_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_completion_tokens=max_tokens,
                stream=True,
            )

        for chunk in stream:
            if not chunk.choices:
                continue
            content = chunk.choices[0].delta.content
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
            raise ValueError("image_bytes cannot be empty.")

        encoded = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:{mime_type};base64,{encoded}"

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": data_url},
                    },
                ],
            }
        ]

        model_to_use = self.vision_model

        try:
            response = self.client.chat.completions.create(
                model=model_to_use,
                messages=messages,
                temperature=temperature,
                max_completion_tokens=max_tokens,
                stream=False,
            )
        except Exception as err:
            print(f"Groq vision OCR failed with {model_to_use}: {err}. Retrying with {FALLBACK_VISION_MODEL}")
            response = self.client.chat.completions.create(
                model=FALLBACK_VISION_MODEL,
                messages=messages,
                temperature=temperature,
                max_completion_tokens=max_tokens,
                stream=False,
            )

        content = response.choices[0].message.content
        return content.strip() if isinstance(content, str) else ""

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