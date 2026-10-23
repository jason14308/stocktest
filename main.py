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
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.sans-serif'] = [
    'Noto Sans CJK TC',
    'Noto Sans TC',
    'PingFang TC',
    'Microsoft JhengHei',
    'sans-serif'
]

# ----------------- 1. 資料收集與分析模組 -----------------

def get_us_and_macro_market():
    """美股大盤指數與關鍵總經先行指標 (VIX、美債殖利率、美元指數)"""
    tickers = {
        "標普 500": "^GSPC",
        "那斯達克": "^IXIC",
        "費城半導體": "^SOX",
        "道瓊工業": "^DJI",
        "台積電 ADR": "TSM",
        "恐慌指數 VIX": "^VIX",
        "美 10 年債殖利率": "^TNX",
        "美元指數": "DX-Y.NYB"
    }
    report = ["【美股動態與宏觀先行指標】"]
    try:
        data = yf.download(list(tickers.values()), period="5d", progress=False)['Close']
        for name, sym in tickers.items():
            if sym in data.columns and len(data[sym].dropna()) >= 2:
                series = data[sym].dropna()
                latest = series.iloc[-1]
                prev = series.iloc[-2]
                pct = ((latest - prev) / prev) * 100
                sign = "+" if pct > 0 else ""
                
                # 特殊單位呈現
                if "殖利率" in name:
                    report.append(f"• {name}: {latest:.3f}% ({sign}{pct:.2f}%)")
                else:
                    report.append(f"• {name}: {latest:.2f} ({sign}{pct:.2f}%)")
    except Exception as e:
        report.append(f"• 美股/總經指標抓取異常: {e}")
    return "\n".join(report)

def get_tw_market_and_institutional():
    """台股大盤指數與三大法人買賣超 (證交所 OpenAPI)"""
    report = ["【台股大盤走勢與籌碼動態】"]
    
    # 1. 台股加權指數
    try:
        tw_data = yf.download("^TWII", period="5d", progress=False)['Close']
        series = tw_data.dropna()
        if len(series) >= 2:
            latest = series.iloc[-1]
            prev = series.iloc[-2]
            pct = ((latest - prev) / prev) * 100
            sign = "+" if pct > 0 else ""
            report.append(f"• 加權指數 (^TWII): {latest:.2f} ({sign}{pct:.2f}%)")
        else:
            report.append("• 台股大盤數據筆數不足")
    except Exception as e:
        report.append(f"• 台股指數擷取異常: {e}")

    # 2. 三大法人買賣超日報
    try:
        url = "https://openapi.twse.com.tw/v1/fund/BFI82U"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            total_net = 0
            inst_details = []
            for item in data:
                name = item.get("Name", "").strip()
                diff_str = item.get("Difference", "0").replace(",", "")
                try:
                    diff_val = int(diff_str) / 100000000  # 轉為億元
                    total_net += diff_val
                    sign = "+" if diff_val > 0 else ""
                    if "外資" in name:
                        inst_details.append(f"  - 外資及陸資: {sign}{diff_val:.2f} 億")
                    elif "投信" in name:
                        inst_details.append(f"  - 投信: {sign}{diff_val:.2f} 億")
                    elif "自營商" in name and "避險" not in name:
                        inst_details.append(f"  - 自營商(自行買賣): {sign}{diff_val:.2f} 億")
                except ValueError:
                    continue
            
            total_sign = "+" if total_net > 0 else ""
            report.append(f"• 三大法人合計買賣超: {total_sign}{total_net:.2f} 億")
            report.extend(inst_details)
        else:
            report.append("• 三大法人資料取得失敗 (非開盤日或伺服器回應異常)")
    except Exception as e:
        report.append(f"• 三大法人籌碼抓取異常: {e}")

    return "\n".join(report)

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
    """抓取 Yahoo 奇摩股市首頁即時焦點新聞"""
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

def get_ptt_sentiment():
    """抓取 PTT Stock 版熱門焦點標題"""
    report = ["【社群投資焦點 (PTT Stock)】"]
    url = "https://www.ptt.cc/bbs/Stock/index.html"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        titles = []
        for tag in soup.select("div.r-ent div.title a"):
            title_text = tag.text.strip()
            if not title_text.startswith("[公告]"):
                titles.append(title_text)
            if len(titles) >= 5:
                break
        for t in titles:
            report.append(f"• {t}")
    except Exception as e:
        report.append(f"• PTT 輿情抓取失敗: {e}")
    return "\n".join(report)

# ----------------- 2. 圖表產製模組 -----------------

def generate_stock_chart(stock_data, output_path="stock_chart.png"):
    """產製焦點個股漲跌長條圖"""
    if not stock_data:
        return None
    
    names = list(stock_data.keys())
    values = list(stock_data.values())
    colors = ['#eb4d4b' if v >= 0 else '#2ecc71' for v in values]  # 台股紅漲綠跌

    plt.figure(figsize=(6, 3.5), dpi=150)
    bars = plt.bar(names, values, color=colors, width=0.45)
    plt.axhline(0, color='gray', linewidth=0.8, linestyle='--')
    plt.ylabel("漲跌幅 (%)", fontsize=10)
    plt.title("焦點個股日漲跌統計", fontsize=12)

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
    """透過 LINE API 推送訊息（支援單人 push 與多人 multicast 清單）"""
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
    raw_user_ids = os.getenv("LINE_USER_ID", "")
    
    if not token or not raw_user_ids:
        print("❌ [LINE 錯誤] 未設定 LINE_CHANNEL_ACCESS_TOKEN 或 LINE_USER_ID")
        return

    user_list = [uid.strip() for uid in raw_user_ids.split(",") if uid.strip()]
    if not user_list:
        print("❌ [LINE 錯誤] LINE_USER_ID 清單為空")
        return

    if len(message) > 4000:
        message = message[:4000] + "\n...(篇幅過長已截斷)"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    if len(user_list) == 1:
        url = "https://api.line.me/v2/bot/message/push"
        payload = {
            "to": user_list[0],
            "messages": [{"type": "text", "text": message}]
        }
    else:
        url = "https://api.line.me/v2/bot/message/multicast"
        payload = {
            "to": user_list,
            "messages": [{"type": "text", "text": message}]
        }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        print(f"📡 [LINE 回應碼]: {res.status_code}")
        if res.status_code != 200:
            print(f"❌ [LINE 詳細訊息]: {res.text}")
        else:
            print(f"✅ LINE 成功推送給 {len(user_list)} 位好友")
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
    
    macro_data = get_us_and_macro_market()
    tw_data = get_tw_market_and_institutional()
    focus_stocks_text, stock_dict = get_focus_stocks()
    news = get_market_news()
    ptt_data = get_ptt_sentiment()

    full_report = f"{title}\n\n{macro_data}\n\n{tw_data}\n\n{focus_stocks_text}\n\n{news}\n\n{ptt_data}"
    print(full_report)

    chart_file = generate_stock_chart(stock_dict)
    
    send_line(full_report)
    send_email_with_image(title, full_report, chart_file)

if __name__ == "__main__":
    main()