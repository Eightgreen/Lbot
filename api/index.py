import os
import logging
import json
import asyncio  # 導入 asyncio 用於非同步監控
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
    user_id = event.source.user_id

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
        address = message_text[2:].strip()
        if not address:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請提供路段地址，例如：停車 明德路337巷"))
            return
        try:
            # 調用 ParkingFinder 查詢分組車位
            response_text, error_msgs, api_responses, _ = parking_finder.find_grouped_parking_spots(address)
            # 分段發送訊息
            MAX_LINE_MESSAGE_LENGTH = 5000
            messages = []
            # 分段發送主要回應
            if response_text:
                while response_text:
                    messages.append(TextSendMessage(text=response_text[:MAX_LINE_MESSAGE_LENGTH]))
                    response_text = response_text[MAX_LINE_MESSAGE_LENGTH:]
            else:
                messages.append(TextSendMessage(text="無停車位或異常狀態資訊"))
            # 分段發送 API 回應
            for api_response in api_responses:
                api_text = json.dumps(api_response, ensure_ascii=False, indent=2)
                while api_text:
                    messages.append(TextSendMessage(text=api_text[:MAX_LINE_MESSAGE_LENGTH]))
                    api_text = api_text[MAX_LINE_MESSAGE_LENGTH:]
            # 最後發送錯誤訊息
            if error_msgs:
                for error_msg in error_msgs:
                    messages.append(TextSendMessage(text=error_msg))
            # LINE 限制最多 5 條訊息
            line_bot_api.reply_message(event.reply_token, messages[:5])
        except Exception as e:
            # 處理未預期的錯誤
            logger.error("查詢停車位錯誤: {}".format(str(e)))
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="查詢停車位失敗，請稍後再試！\n錯誤訊息：{}".format(str(e))))
        return

    if message_text.startswith("監控停車"):
        # 處理監控停車指令
        address = message_text[4:].strip()
        if not address:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請提供路段地址，例如：監控停車 青年公園"))
            return
        try:
            # 啟動監控任務（非同步）
            asyncio.run(parking_finder.monitor_parking_spots(address, user_id, max_duration=60))
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="開始監控 {} 的停車位，將在發現新空車位時通知您".format(address)))
        except Exception as e:
            logger.error("啟動監控失敗: {}".format(str(e)))
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="監控啟動失敗，請稍後再試！\n錯誤訊息：{}".format(str(e))))
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
    app.run(debug=True)