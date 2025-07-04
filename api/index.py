from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from api.chatgpt import ChatGPT
import os
import logging



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ssssss = os.getenv("OPENAI_API_KEY")
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
line_handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
working_status = os.getenv("DEFAULT_TALKING", default="true").lower() == "true"

app = Flask(__name__)
chatgpt = ChatGPT()

@app.route('/')
def home():
    logger.info("Home endpoint accessed")
    return 'Hello, World!'

@app.route("/webhook", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    logger.info("Request body: %s", body)
    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError as e:
        logger.error("Invalid signature: %s", str(e))
        abort(400)
    except Exception as e:
        logger.error("Webhook handling error: %s", str(e))
        abort(500)
    return 'OK'

@line_handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global working_status
    logger.info("Handling message: type=%s, text='%s', working_status=%s", 
                event.message.type, event.message.text, working_status)
    
    if event.message.type != "text":
        logger.info("Non-text message, skipping")
        return
    
    message_text = event.message.text.strip()
    logger.info("Processed message text: '%s'", message_text)
    
    if message_text == "啟動":
        working_status = True
        logger.info("Bot activated")
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="我是時下流行的AI互動~"+ssssss))
            logger.info("Activation reply sent")
        except Exception as e:
            logger.error("Error sending activation reply: %s", str(e))
        return

    if message_text == "安靜":
        working_status = False
        logger.info("Bot deactivated")
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="感謝您的使用，若需要我的服務，請跟我說 「啟動」 謝謝~"))
            logger.info("Deactivation reply sent")
        except Exception as e:
            logger.error("Error sending deactivation reply: %s", str(e))
        return
    
    if working_status:
        logger.info("Processing AI response for: '%s'", message_text)
        try:
            chatgpt.add_msg(f"Human:{message_text}?\n")
            reply_msg = chatgpt.get_response().replace("AI:", "", 1)
            logger.info("AI response: '%s'", reply_msg)
            chatgpt.add_msg(f"AI:{reply_msg}\n")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply_msg))
            logger.info("AI reply sent successfully")
        except Exception as e:
            logger.error("Error in AI response or reply: %s", str(e))
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="抱歉，AI 回應失敗，請稍後再試！"))
    else:
        logger.info("Bot is inactive, no response sent")

if __name__ == "__main__":
    app.run()
