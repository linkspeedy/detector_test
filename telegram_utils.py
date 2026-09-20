import os
import requests

def _send_message(bot_token: str, chat_id: str, message: str):
    if not bot_token or not chat_id:
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to send telegram message to chat {chat_id}: {e}")

def send_deposit_notification(pretty_msg: str, raw_msg: str):
    # Send formatted message to Bot 1 (Primary)
    bot1_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    bot1_chat = os.environ.get("TELEGRAM_CHAT_ID")
    if bot1_token and bot1_chat:
        _send_message(bot1_token, bot1_chat, pretty_msg)
    
    # Send raw message to Bot 2 (Terminal/Monitoring)
    send_log(raw_msg)

def send_error_notification(message: str):
    send_log(f"🚨 SYSTEM ERROR 🚨\n{message}")

def send_log(message: str):
    # Print to actual terminal
    print(message)
    
    # Send to Bot 2
    bot2_token = os.environ.get("TELEGRAM_BOT_TOKEN_2")
    bot2_chat = os.environ.get("TELEGRAM_CHAT_ID_2")
    if bot2_token and bot2_chat:
        _send_message(bot2_token, bot2_chat, f"🖥️ [LOG] {message}")
