import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import matplotlib
matplotlib.use('Agg')  # 無介面雲端伺服器繪圖專用模式
import matplotlib.pyplot as plt

# ----------------- 0. 字型與圖表全域設定 -----------------
# 解決負號無法正常顯示問題
plt.rcParams['axes.unicode_minus'] = False
# 設定繁體中文字型優先順序（配合 GitHub Actions 安裝的 fonts-noto-cjk）
plt.rcParams['font.sans-serif'] = [
    'Noto Sans CJK TC',
    'Noto Sans TC',
    'PingFang TC',
    'Microsoft JhengHei',
    'sans-serif'
]

# ----------------- 1. 資料收集與分析模組 -----------------

def get_focus_stocks():
    """追蹤台股重點個股行情（台積電、鴻海、聯發科）"""
    watch_list = {
        "台積電": "2330.TW",
        "鴻海": "2317.TW",
        "聯發科": "2454.TW"
    }
    report = ["【核心焦點個股】"]
    stock_data = {}
    
    try:
        tickers = list(watch_list.values())
        data = yf.download(tickers, period="5d", progress=False)['Close']
        for name, ticker in watch_list.items():
            if ticker in data.columns and len(data[ticker].dropna()) >= 2:
                series = data[ticker].dropna()
                latest = series.iloc[-1]
                prev = series.iloc[-2]
                pct = ((latest - prev) / prev) * 100
                stock_data[name] = pct
                sign = "+" if pct > 0 else ""
                report.append(f"• {name} ({ticker.split('.')[0]}): {latest:.2f} 元 ({sign}{pct:.2f}%)")
    except Exception as e:
        report.append(f"• 個股數據擷取異常: {e}")
        
    return "\n".join(report), stock_data

def get_market_news():
    """抓取 Yahoo 奇摩股市首頁焦點新聞"""
    report = ["【財經即時頭條與市場焦點】"]
    url = "https://tw.stock.yahoo.com/news/"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        news_items = soup.select("ul li h3 a")
        count = 0
        for item in news_items:
            title = item.text.strip()
            if title:
                report.append(f"• {title}")
                count += 1
            if count >= 5:
                break
    except Exception as e:
        report.append(f"• 新聞數據擷取異常: {e}")
    return "\n".join(report)

def get_us_and_tw_indices():
    """大盤指數概況"""
    tickers = {
        "加權指數": "^TWII",
        "標普 500": "^GSPC",
        "那斯達克": "^IXIC",
        "費城半導體": "^SOX",
        "台積電 ADR": "TSM"
    }
    report = ["【美股／台股大盤走勢】"]
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
        report.append(f"• 大盤抓取異常: {e}")
    return "\n".join(report)

# ----------------- 2. 圖表產製模組 -----------------

def generate_stock_chart(stock_data, output_path="stock_chart.png"):
    """產製焦點個股漲跌長條圖"""
    if not stock_data:
        return None
    
    names = list(stock_data.keys())
    values = list(stock_data.values())
    colors = ['#eb4d4b' if v >= 0 else '#2ecc71' for v in values]  # 紅漲綠跌

    plt.figure(figsize=(6, 3.5), dpi=150)
    bars = plt.bar(names, values, color=colors, width=0.45)
    plt.axhline(0, color='gray', linewidth=0.8, linestyle='--')
    plt.ylabel("漲跌幅 (%)", fontsize=10)
    plt.title("焦點個股日漲跌統計", fontsize=12)

    # 動態設定數值標籤位置，避免與長條柱重疊
    for bar in bars:
        yval = bar.get_height()
        sign = "+" if yval > 0 else ""
        va_setting = 'bottom' if yval >= 0 else 'top'
        plt.text(bar.get_x() + bar.get_width() / 2.0, yval, f"{sign}{yval:.2f}%", 
                 ha='center', va=va_setting, fontsize=9)

    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    return output_path

# ----------------- 3. 通知推播模組 -----------------

def send_line(message):
    """透過 LINE Messaging API 發送文字摘要"""
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
    user_id = os.getenv("LINE_USER_ID")
    if not token or not user_id:
        print("❌ 未設定 LINE Token 或 User ID")
        return
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    payload = {"to": user_id, "messages": [{"type": "text", "text": message[:4000]}]}
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"📡 [LINE 回應碼]: {res.status_code}")
    except Exception as e:
        print(f"❌ [LINE 連線異常]: {e}")

def send_email_with_image(subject, text_content, image_path):
    """發送內嵌圖表的 HTML 電子郵件"""
    sender = os.getenv("GMAIL_USER")
    password = os.getenv("GMAIL_APP_PASSWORD")
    receiver = os.getenv("RECEIVER_EMAIL", sender)
    if not sender or not password:
        print("⚠️ 未設定 Gmail 帳號或密碼，跳過 Email 發送")
        return

    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = receiver

    html_content = f"""
    <html>
      <body style="font-family: Arial, 'Microsoft JhengHei', sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #2c3e50;">{subject}</h2>
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px;">
          <pre style="font-size: 14px; font-family: inherit; white-space: pre-wrap;">{text_content}</pre>
        </div>
        <br>
        <h3>📊 視覺化漲跌圖表：</h3>
        <img src="cid:chart_image" style="max-width: 100%; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
      </body>
    </html>
    """
    msg_alternative = MIMEMultipart("alternative")
    msg.attach(msg_alternative)
    msg_alternative.attach(MIMEText(html_content, "html", "utf-8"))

    if image_path and os.path.exists(image_path):
        with open(image_path, "rb") as f:
            img = MIMEImage(f.read())
            img.add_header("Content-ID", "<chart_image>")
            msg.attach(img)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())
        print("📧 圖文 Email 發送成功！")
    except Exception as e:
        print(f"❌ Email 發送異常: {e}")

# ----------------- 4. 主程序 -----------------

def main():
    today_str = datetime.now().strftime("%Y-%m-%d")
    title = f"📊 每日晨間投資快報 - {today_str}"
    
    indices = get_us_and_tw_indices()
    focus_stocks_text, stock_dict = get_focus_stocks()
    news = get_market_news()

    full_report = f"{title}\n\n{indices}\n\n{focus_stocks_text}\n\n{news}"
    print(full_report)

    chart_file = generate_stock_chart(stock_dict)
    
    send_line(full_report)
    send_email_with_image(title, full_report, chart_file)

if __name__ == "__main__":
    main()