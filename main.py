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
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mplfinance as mpf

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
    """美股大盤指數與關鍵總經先行指標"""
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
                
                if "殖利率" in name:
                    report.append(f"• {name}: {latest:.3f}% ({sign}{pct:.2f}%)")
                else:
                    report.append(f"• {name}: {latest:.2f} ({sign}{pct:.2f}%)")
    except Exception as e:
        report.append(f"• 美股/總經指標抓取異常: {e}")
    return "\n".join(report)

def get_tw_market_and_institutional():
    """台股加權指數與三大法人買賣超 (證交所 OpenAPI)"""
    report = ["【台股大盤走勢與籌碼動態】"]
    tw_summary = {"price": "--", "pct_str": "--", "pct_val": 0.0, "inst_net": "--"}
    
    # 台股指數
    try:
        tw_data = yf.download("^TWII", period="5d", progress=False)['Close']
        series = tw_data.dropna()
        if len(series) >= 2:
            latest = series.iloc[-1]
            prev = series.iloc[-2]
            pct = ((latest - prev) / prev) * 100
            sign = "+" if pct > 0 else ""
            tw_summary["price"] = f"{latest:.2f}"
            tw_summary["pct_str"] = f"{sign}{pct:.2f}%"
            tw_summary["pct_val"] = pct
            report.append(f"• 加權指數 (^TWII): {latest:.2f} ({sign}{pct:.2f}%)")
        else:
            report.append("• 台股大盤數據筆數不足")
    except Exception as e:
        report.append(f"• 台股指數擷取異常: {e}")

    # 三大法人買賣超
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
            tw_summary["inst_net"] = f"{total_sign}{total_net:.2f} 億"
            report.append(f"• 三大法人合計買賣超: {total_sign}{total_net:.2f} 億")
            report.extend(inst_details)
        else:
            report.append("• 三大法人資料取得失敗")
    except Exception as e:
        report.append(f"• 三大法人籌碼抓取異常: {e}")

    return "\n".join(report), tw_summary

def get_sector_performance():
    """題材族群輪動分析（AI、矽光子、散熱、重電）"""
    sectors = {
        "AI 伺服器": ["2382.TW", "3231.TW", "6669.TW"],
        "矽光子 CPO": ["3450.TW", "4977.TW", "3363.TW"],
        "散熱族群": ["3017.TW", "3324.TW", "2421.TW"],
        "重電能源": ["1519.TW", "1513.TW", "1503.TW"]
    }
    all_tickers = [ticker for group in sectors.values() for ticker in group]
    report = ["【盤面焦點概念族群輪動】"]
    sorted_sectors = []
    
    try:
        data = yf.download(all_tickers, period="5d", progress=False)['Close']
        sector_scores = {}
        for sector_name, tickers in sectors.items():
            pct_list = []
            for t in tickers:
                if t in data.columns and len(data[t].dropna()) >= 2:
                    s = data[t].dropna()
                    pct = ((s.iloc[-1] - s.iloc[-2]) / s.iloc[-2]) * 100
                    pct_list.append(pct)
            if pct_list:
                sector_scores[sector_name] = sum(pct_list) / len(pct_list)

        sorted_sectors = sorted(sector_scores.items(), key=lambda x: x[1], reverse=True)
        for name, avg_pct in sorted_sectors:
            sign = "+" if avg_pct > 0 else ""
            report.append(f"• {name}: 平均 {sign}{avg_pct:.2f}%")
    except Exception as e:
        report.append(f"• 族群計算異常: {e}")

    return "\n".join(report), sorted_sectors

def get_focus_stocks():
    """追蹤台股重點個股行情"""
    watch_list = {
        "台積電": "2330.TW",
        "鴻海": "2317.TW",
        "聯發科": "2454.TW"
    }
    report = ["【核心焦點個股】"]
    stocks_summary = []
    try:
        tickers = list(watch_list.values())
        data = yf.download(tickers, period="5d", progress=False)['Close']
        for name, ticker in watch_list.items():
            if ticker in data.columns and len(data[ticker].dropna()) >= 2:
                series = data[ticker].dropna()
                latest = series.iloc[-1]
                prev = series.iloc[-2]
                pct = ((latest - prev) / prev) * 100
                sign = "+" if pct > 0 else ""
                report.append(f"• {name} ({ticker.split('.')[0]}): {latest:.2f} 元 ({sign}{pct:.2f}%)")
                stocks_summary.append({
                    "name": name,
                    "code": ticker.split('.')[0],
                    "price": f"{latest:.2f}",
                    "pct": pct,
                    "pct_str": f"{sign}{pct:.2f}%"
                })
    except Exception as e:
        report.append(f"• 個股數據擷取異常: {e}")
        
    return "\n".join(report), stocks_summary

def get_curated_news():
    """抓取 Yahoo 股市頭條與 PTT 焦點，並標記重大關鍵字"""
    keywords = ["營收", "新高", "法說", "擴產", "獲利", "外資", "晶圓", "AI", "停損", "反彈", "重挫", "大漲"]
    report = ["【精選重大財經焦點與社群熱點】"]
    selected_news = []
    
    try:
        url = "https://tw.stock.yahoo.com/news/"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        for a in soup.select("ul li h3 a"):
            title = a.text.strip()
            if title:
                is_hot = any(k in title for k in keywords)
                prefix = "🔥 [Yahoo] " if is_hot else "• [Yahoo] "
                selected_news.append((is_hot, f"{prefix}{title}"))
    except Exception:
        pass

    try:
        ptt_url = "https://www.ptt.cc/bbs/Stock/index.html"
        ptt_headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(ptt_url, headers=ptt_headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        for tag in soup.select("div.r-ent div.title a"):
            t = tag.text.strip()
            if not t.startswith("[公告]"):
                is_hot = any(k in t for k in keywords)
                prefix = "🔥 [PTT] " if is_hot else "• [PTT] "
                selected_news.append((is_hot, f"{prefix}{t}"))
    except Exception:
        pass

    selected_news.sort(key=lambda x: x[0], reverse=True)
    news_titles = [text for _, text in selected_news[:5]]
    report.extend(news_titles if news_titles else ["• 暫無即時篩選新聞"])
    return "\n".join(report), news_titles

# ----------------- 2. K 線圖繪製模組 -----------------

def generate_kline_chart(ticker="^TWII", output_path="stock_chart.png"):
    """繪製台股近 35 日 K 線圖（含 MA5、MA20 均線與成交量）"""
    try:
        df = yf.download(ticker, period="3mo", progress=False)
        if df.empty or len(df) < 10:
            return None

        if hasattr(df.columns, 'levels') and len(df.columns.levels) > 1:
            df.columns = df.columns.get_level_values(0)

        df = df.tail(35)
        market_colors = mpf.make_marketcolors(
            up='#eb4d4b', down='#2ecc71', edge='inherit', wick='inherit', volume='inherit'
        )
        custom_style = mpf.make_mpf_style(
            base_mpf_style='nightclouds',
            marketcolors=market_colors,
            rc={
                'font.family': ['Noto Sans CJK TC', 'Noto Sans TC', 'Microsoft JhengHei', 'sans-serif'],
                'axes.unicode_minus': False
            }
        )

        mpf.plot(
            df,
            type='candle',
            mav=(5, 20),
            volume=True,
            style=custom_style,
            title="\n台股加權指數 (^TWII) 近期日 K 線與成交量",
            ylabel="指數點位",
            ylabel_lower="成交量",
            savefig=output_path,
            figsize=(9, 5),
            dpi=150
        )
        return output_path
    except Exception as e:
        print(f"❌ 繪製 K 線圖失敗: {e}")
        return None

# ----------------- 3. LINE Flex Message 卡片產製 -----------------

def create_flex_card(today_str, tw_summary, stocks_summary, sector_summary, news_summary):
    """產製結構化美觀的 LINE Flex 卡片 JSON 結構"""
    idx_color = "#eb4d4b" if tw_summary["pct_val"] >= 0 else "#2ecc71"

    # 1. 焦點個股 row 結構
    stock_rows = []
    for s in stocks_summary:
        c = "#eb4d4b" if s["pct"] >= 0 else "#2ecc71"
        stock_rows.append({
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {"type": "text", "text": f"{s['name']} ({s['code']})", "size": "sm", "color": "#555555", "flex": 4},
                {"type": "text", "text": s["price"], "size": "sm", "color": "#111111", "align": "end", "weight": "bold", "flex": 3},
                {"type": "text", "text": s["pct_str"], "size": "sm", "color": c, "align": "end", "weight": "bold", "flex": 3}
            ]
        })

    # 2. 概念族群 row 結構
    sector_rows = []
    for name, avg_pct in sector_summary[:4]:
        c = "#eb4d4b" if avg_pct >= 0 else "#2ecc71"
        sign = "+" if avg_pct > 0 else ""
        sector_rows.append({
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {"type": "text", "text": name, "size": "xs", "color": "#666666", "flex": 6},
                {"type": "text", "text": f"{sign}{avg_pct:.2f}%", "size": "xs", "color": c, "align": "end", "weight": "bold", "flex": 4}
            ]
        })

    # 3. 頭條新聞列表
    news_rows = []
    for n in news_summary[:3]:
        clean_n = n.replace("🔥 ", "").replace("• ", "")
        news_rows.append({
            "type": "text",
            "text": f"• {clean_n}",
            "size": "xxs",
            "color": "#666666",
            "wrap": True
        })

    bubble = {
        "type": "bubble",
        "size": "giga",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#1e272e",
            "paddingAll": "15px",
            "contents": [
                {
                    "type": "text",
                    "text": "📊 晨間台股速報",
                    "weight": "bold",
                    "color": "#00d2d3",
                    "size": "lg"
                },
                {
                    "type": "text",
                    "text": f"交易結算日：{today_str}",
                    "size": "xs",
                    "color": "#a4b0be",
                    "margin": "xs"
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                # 加權指數大字塊
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {"type": "text", "text": "加權指數", "size": "xs", "color": "#888888"},
                                {"type": "text", "text": tw_summary["price"], "size": "xl", "weight": "bold", "color": "#222222"}
                            ],
                            "flex": 5
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {"type": "text", "text": "三大法人買賣", "size": "xs", "color": "#888888", "align": "end"},
                                {"type": "text", "text": tw_summary["inst_net"], "size": "sm", "weight": "bold", "color": "#222222", "align": "end"}
                            ],
                            "flex": 5
                        }
                    ]
                },
                {"type": "separator"},
                # 核心個股
                {
                    "type": "text",
                    "text": "📌 核心權值股追蹤",
                    "weight": "bold",
                    "size": "xs",
                    "color": "#2c3e50"
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "xs",
                    "contents": stock_rows
                },
                {"type": "separator"},
                # 概念題材輪動
                {
                    "type": "text",
                    "text": "⚡ 盤面焦點族群表現",
                    "weight": "bold",
                    "size": "xs",
                    "color": "#2c3e50"
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "xs",
                    "contents": sector_rows
                },
                {"type": "separator"},
                # 重點熱門新聞
                {
                    "type": "text",
                    "text": "🔥 重大即時頭條",
                    "weight": "bold",
                    "size": "xs",
                    "color": "#2c3e50"
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "xs",
                    "contents": news_rows
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "action": {
                        "type": "uri",
                        "label": "查看 Yahoo 股市即時行情",
                        "uri": "https://tw.stock.yahoo.com/"
                    },
                    "style": "primary",
                    "color": "#0984e3",
                    "height": "sm"
                }
            ]
        }
    }
    return bubble

# ----------------- 4. 通知推播模組 -----------------

def send_line_flex(flex_content, fallback_text):
    """發送卡片式 LINE Flex Message（失敗時自動以純文字推播降級相容）"""
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
    raw_user_ids = os.getenv("LINE_USER_ID", "")
    if not token or not raw_user_ids:
        return

    user_list = [uid.strip() for uid in raw_user_ids.split(",") if uid.strip()]
    if not user_list:
        return

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    
    # 封裝 Flex Message Payload
    flex_message = {
        "type": "flex",
        "altText": "📊 今日台股晨間精選速報",
        "contents": flex_content
    }

    if len(user_list) == 1:
        url = "https://api.line.me/v2/bot/message/push"
        payload = {"to": user_list[0], "messages": [flex_message]}
    else:
        url = "https://api.line.me/v2/bot/message/multicast"
        payload = {"to": user_list, "messages": [flex_message]}

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        print(f"📡 [LINE Flex 回應碼]: {res.status_code}")
        if res.status_code != 200:
            print(f"⚠️ Flex 推送未成功 ({res.text})，切換降級為純文字推播...")
            # 降級純文字重試
            text_payload = {"messages": [{"type": "text", "text": fallback_text[:4000]}]}
            if len(user_list) == 1:
                text_payload["to"] = user_list[0]
            else:
                text_payload["to"] = user_list
            requests.post(url, headers=headers, json=text_payload, timeout=15)
        else:
            print(f"✅ LINE Flex 卡片成功推送給 {len(user_list)} 位好友")
    except Exception as e:
        print(f"❌ [LINE 連線異常]: {e}")

def send_email_with_image(subject, text_content, image_path):
    """發送內嵌圖表的 HTML 電子郵件"""
    sender = os.getenv("GMAIL_USER")
    password = os.getenv("GMAIL_APP_PASSWORD")
    receiver = os.getenv("RECEIVER_EMAIL", sender)
    if not sender or not password:
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
        <h3>📊 大盤技術走勢 (日 K 線、MA5/MA20 均線與成交量)：</h3>
        <img src="cid:chart_image" style="max-width: 100%; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.15);">
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

# ----------------- 5. 主程序 -----------------

def main():
    today_str = datetime.now().strftime("%Y-%m-%d")
    title = f"📊 每日晨間投資快報 - {today_str}"
    
    macro_data = get_us_and_macro_market()
    tw_data, tw_summary = get_tw_market_and_institutional()
    sector_data, sector_summary = get_sector_performance()
    focus_stocks_text, stocks_summary = get_focus_stocks()
    curated_news, news_summary = get_curated_news()

    # 純文字報表（備用推播與 Email 內文使用）
    full_report = f"{title}\n\n{macro_data}\n\n{tw_data}\n\n{sector_data}\n\n{focus_stocks_text}\n\n{curated_news}"
    print(full_report)

    # 1. 產製 K 線圖
    chart_file = generate_kline_chart("^TWII")
    
    # 2. 產製 LINE Flex 卡片
    flex_card = create_flex_card(today_str, tw_summary, stocks_summary, sector_summary, news_summary)

    # 3. 發送推播
    send_line_flex(flex_card, full_report)
    send_email_with_image(title, full_report, chart_file)

if __name__ == "__main__":
    main()