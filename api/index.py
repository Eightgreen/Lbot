import os
import logging
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from api.chatgpt import ChatGPT
from api.parking import ParkingFinder

# 設置日誌記錄，方便除錯
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化 Flask 應用和 LINE Bot
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
line_handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
working_status = os.getenv("DEFAULT_TALKING", default="true").lower() == "true"
app = Flask(__name__)
chatgpt = ChatGPT()
parking_finder = ParkingFinder()


@app.route('/')
def home():
    """根路由，返回簡單問候語"""
    return 'Hello, World!'


@app.route("/webhook", methods=['POST'])
def callback():
    """處理 LINE Webhook 請求"""
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        # 驗證並處理 Webhook 請求
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        # 簽名驗證失敗，返回 400
        abort(400)
    except Exception as e:
        # 記錄其他錯誤並返回 500
        logger.error(f"Webhook 錯誤: {str(e)}")
        abort(500)
    return 'OK'


@line_handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """處理 LINE 文字訊息"""
    global working_status
    message_text = event.message.text.strip()

    if message_text == "啟動":
        # 啟動 AI 回應模式
        working_status = True
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="AI智能已啟動，歡迎互動~"))
        return

    if message_text == "安靜":
        # 關閉 AI 回應模式
        working_status = False
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="感謝使用，請說「啟動」重新開啟~"))
        return

    if message_text.startswith("查分組車位"):
        # 處理查詢分組車位指令
        address = message_text.replace("查分組車位", "").strip()
        if not address:
            # 若無地址，返回提示
            line_bot_api.reply_message(event.reply_token,
                                       TextSendMessage(text="請提供路段地址，例如：查分組車位 明德路337巷"))
            return
        try:
            # 調用 ParkingFinder 查詢分組車位
            reply_msg = parking_finder.find_grouped_parking_spots(address)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_msg))
        except Exception as e:
            # 處理錯誤，返回友善提示
            logger.error(f"查詢分組車位錯誤: {str(e)}")
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="查詢分組車位失敗，請稍後再試！"))
        return

    if working_status:
        # 處理一般 AI 回應
        try:
            chatgpt.add_msg(f"Human:{message_text}?\n")
            reply_msg = chatgpt.get_response().replace("AI:", "", 1)
            chatgpt.add_msg(f"AI:{reply_msg}\n")
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_msg))
        except Exception as e:
            logger.error(f"AI 回應錯誤: {str(e)}")
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="AI回應失敗，請稍後再試！"))


if __name__ == "__main__":
    app.run()