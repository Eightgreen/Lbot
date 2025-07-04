import os
import openai
import logging
from api.prompt import Prompt

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")

class ChatGPT:
    def __init__(self):
        self.prompt = Prompt()
        self.model = os.getenv("OPENAI_MODEL", default="gpt-3.5-turbo")
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", default=0.7))
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", default=50))

    def get_response(self):
        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": self.prompt.generate_prompt()}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                proxies=None  # 顯式禁用代理
            )
            return response.choices[0].message.content.strip()
        except openai.OpenAIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return "抱歉，我現在無法回應，請稍後再試。"
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return "抱歉，發生未知錯誤，請稍後再試。"

    def add_msg(self, text):
        self.prompt.add_msg(text)
