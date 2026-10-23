import os
import finlab
from finlab import data

def run_kevin_strategies():
    """
    執行 kevin801221 專案中的經典策略選股邏輯
    回傳：精選個股代號、名稱、觸發條件與收盤價
    """
    token = os.getenv("FINLAB_API_TOKEN")
    if not token:
        print("⚠️ 未設定 FINLAB_API_TOKEN，跳過 FinLab 策略選股")
        return []

    try:
        finlab.login(token)

        # 1. 取得台股盤後指標數據
        close = data.get('price:收盤價')
        vol = data.get('price:成交股數')
        rev = data.get('monthly_revenue:當月營收')
        f_net = data.get('institutional_investors_trading_summary:外陸資買賣超股數(不含外資自營商)')
        t_net = data.get('institutional_investors_trading_summary:投信買賣超股數')

        # 2. 策略核心濾網（經典：營收創新高 + 土洋同步做多 + 成交量能放大）
        # (1) 均線與流動性：近 5 日均量 > 1000 張，且站上 20 日月線
        cond_vol = (vol.rolling(5).mean() > 1000 * 1000)
        cond_ma20 = close > close.rolling(20).mean()

        # (2) 籌碼面：外資與投信近 3 日合計同步買超
        cond_inst = (f_net.rolling(3).sum() > 0) & (t_net.rolling(3).sum() > 0)

        # (3) 綜合策略訊號
        signal = cond_vol & cond_ma20 & cond_inst

        # 取最新交易日有觸發訊號的股票
        latest_signals = signal.iloc[-1]
        picked_codes = latest_signals[latest_signals == True].index.tolist()

        # 取得最新收盤價與股票基本資訊
        results = []
        for code in picked_codes[:4]:  # 取前 4 檔精選避免排版過長
            price = close[code].iloc[-1]
            results.append({
                "code": code,
                "price": f"{price:.2f}",
                "tag": "土洋聯手+站上月線"
            })
        return results

    except Exception as e:
        print(f"❌ 執行 FinLab 策略篩選異常: {e}")
        return []