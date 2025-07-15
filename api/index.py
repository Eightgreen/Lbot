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
    # 根路由，返回簡單問候語
    return 'Hello, World!'

@app.route("/webhook", methods=['POST'])
def callback():
    # 處理 LINE Webhook 請求
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
        logger.error("Webhook 錯誤: {}".format(str(e)))
        abort(500)
    return 'OK'

@line_handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # 處理 LINE 文字訊息
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

    if message_text.startswith("停車"):
        # 處理停車查詢指令
        address = message_text.replace("停車", "").strip()
        if not address:
            # 若無地址，返回提示
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請提供路段地址，例如：停車 明德路337巷"))
            return
        try:
            # 調用 ParkingFinder 查詢分組車位
            reply_msg, error_msg = parking_finder.find_grouped_parking_spots(address)
            # 分段發送訊息
            MAX_LINE_MESSAGE_LENGTH = 5000
            messages = []
            while reply_msg:
                messages.append(TextSendMessage(text=reply_msg[:MAX_LINE_MESSAGE_LENGTH]))
                reply_msg = reply_msg[MAX_LINE_MESSAGE_LENGTH:]
            if not messages:
                messages.append(TextSendMessage(text="無回應內容"))
            # 如果有錯誤訊息，作為最後一條發送
            if error_msg:
                messages.append(TextSendMessage(text=error_msg))
            # LINE 限制最多 5 條訊息
            line_bot_api.reply_message(event.reply_token, messages[:5])
        except Exception as e:
            # 處理錯誤，返回友善提示
            logger.error("查詢停車位錯誤: {}".format(str(e)))
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="查詢停車位失敗，請稍後再試！\n錯誤訊息：{}".format(str(e))))
        return

    if working_status:
        # 處理一般 AI 回應
        try:
            chatgpt.add_msg("Human: {}?\n".format(message_text))
            reply_msg = chatgpt.get_response().replace("AI:", "", 1)
            chatgpt.add_msg("AI: {}\n".format(reply_msg))
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_msg))
        except Exception as e:
            logger.error("AI 回應錯誤: {}".format(str(e)))
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="AI回應失敗，請稍後再試！"))

if __name__ == "__main__":
    app.run()