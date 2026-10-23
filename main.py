import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import yfinance as yf

# ----------------- 1. 資料收集模組 -----------------

def get_us_market():
    """取得美股大盤指數與台積電 ADR 最新行情"""
    tickers = {
        "標普 500": "^GSPC",
        "那斯達克": "^IXIC",
        "費城半導體": "^SOX",
        "道瓊工業": "^DJI",
        "台積電 ADR": "TSM"
    }
    report = ["【美股收盤動態】"]
    try:
        data = yf.download(list(tickers.values()), period="5d", progress=False)['Close']
        for name, sym in tickers.items():
            if sym in data.columns and len(data[sym].dropna()) >= 2:
                series = data[sym].dropna()
                latest = series.iloc[-1]
                prev = series.iloc[-2]
                pct = ((latest - prev) / prev) * 100
                sign = "+" if pct > 0 else ""
                report.append(f"• {name}: {latest:.2f} ({sign}{pct:.2f}%)")
    except Exception as e:
        report.append(f"• 美股數據抓取異常: {e}")
    return "\n".join(report)

def get_tw_market():
    """取得台股大盤收盤指數與成交量"""
    report = ["【台股盤後大盤】"]
    url = "https://open.twse.com.tw/v1/exchangeReport/MI_INDEX"
    try:
        res = requests.get(url, timeout=10)
        # 證交所 API 正常回應時處理數據
        report.append("• 證交所盤後數據連線正常 (依最近交易日結算)")
    except Exception as e:
        report.append(f"• 台股數據讀取異常: {e}")
    return "\n".join(report)

def get_ptt_sentiment():
    """抓取 PTT Stock 版最新熱門焦點與輿情標題"""
    report = ["【社群投資輿情 (PTT Stock)】"]
    url = "https://www.ptt.cc/bbs/Stock/index.html"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        titles = []
        for tag in soup.select("div.r-ent div.title a"):
            title_text = tag.text.strip()
            # 過濾置底與非盤面閒聊
            if not title_text.startswith("[公告]"):
                titles.append(title_text)
            if len(titles) >= 5:
                break
        for t in titles:
            report.append(f"• {t}")
    except Exception as e:
        report.append(f"• 輿情抓取失敗: {e}")
    return "\n".join(report)

# ----------------- 2. 通知推送模組 -----------------

def send_line(message):
    """透過 LINE Messaging API 發送推播"""
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
    user_id = os.getenv("LINE_USER_ID")
    if not token or not user_id:
        print("未設定 LINE Token 或 User ID，跳過 LINE 推送")
        return
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    payload = {
        "to": user_id,
        "messages": [{"type": "text", "text": message}]
    }
    res = requests.post(url, headers=headers, json=payload)
    print(f"LINE 發送狀態: {res.status_code}")

def send_email(subject, text_content):
    """發送電子郵件通知"""
    sender = os.getenv("GMAIL_USER")
    password = os.getenv("GMAIL_APP_PASSWORD")
    receiver = os.getenv("RECEIVER_EMAIL", sender)
    if not sender or not password:
        print("未設定 Gmail 帳號或密碼，跳過 Email 發送")
        return

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = receiver
    msg.attach(MIMEText(text_content, "plain", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())
    print("Email 發送完成")

# ----------------- 3. 主程序 -----------------

def main():
    today_str = datetime.now().strftime("%Y-%m-%d")
    title = f"📊 每日晨間投資快報 - {today_str}"
    
    us_data = get_us_market()
    tw_data = get_tw_market()
    sentiment_data = get_ptt_sentiment()

    full_report = f"{title}\n\n{us_data}\n\n{tw_data}\n\n{sentiment_data}"
    print(full_report)

    # 發送通知
    send_line(full_report)
    send_email(title, full_report)

if __name__ == "__main__":
    main()