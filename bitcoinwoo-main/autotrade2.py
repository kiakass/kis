import os
from dotenv import load_dotenv
import pyupbit
import pandas as pd
import json
from openai import OpenAI
import ta
from ta.utils import dropna
import time
import requests
import logging
import sqlite3
from datetime import datetime, timedelta
import re
import schedule
import numpy as np

# .env 파일에 저장된 환경 변수를 불러오기 (API 키 등)
load_dotenv()

# 로깅 설정 - 로그 레벨을 INFO로 설정하여 중요 정보 출력
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Upbit 객체 생성
access = os.getenv("UPBIT_ACCESS_KEY")
secret = os.getenv("UPBIT_SECRET_KEY")
if not access or not secret:
    logger.error("API keys not found. Please check your .env file.")
    raise ValueError("Missing API keys. Please check your .env file.")
upbit = pyupbit.Upbit(access, secret)

# SQLite 데이터베이스 초기화 함수 - 거래 내역을 저장할 테이블을 생성
def init_db():
    logger.info("Initializing database...")
    conn = sqlite3.connect('bitcoin_trades.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS trades
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT,
                  decision TEXT,
                  percentage INTEGER,
                  reason TEXT,
                  gpt_response TEXT,
                  btc_balance REAL,
                  krw_balance REAL,
                  btc_avg_buy_price REAL,
                  btc_krw_price REAL,
                  reflection TEXT)''')
    conn.commit()
    logger.info("Database initialized successfully.")
    return conn

# 거래 기록을 DB에 저장하는 함수
def log_trade(conn, decision, percentage, reason, gpt_response, btc_balance, krw_balance, btc_avg_buy_price, btc_krw_price, reflection=''):
    logger.info("Logging trade to database...")
    c = conn.cursor()
    timestamp = datetime.now().isoformat()
    c.execute("""INSERT INTO trades 
                 (timestamp, decision, percentage, reason, gpt_response, btc_balance, krw_balance, btc_avg_buy_price, btc_krw_price, reflection) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (timestamp, decision, percentage, reason, gpt_response, btc_balance, krw_balance, btc_avg_buy_price, btc_krw_price, reflection))
    conn.commit()
    logger.info("Trade logged successfully.")

# 최근 투자 기록 조회
def get_recent_trades(conn, days=7):
    logger.info("Fetching recent trades from database...")
    c = conn.cursor()
    seven_days_ago = (datetime.now() - timedelta(days=days)).isoformat()
    c.execute("SELECT * FROM trades WHERE timestamp > ? ORDER BY timestamp DESC", (seven_days_ago,))
    columns = [column[0] for column in c.description]
    recent_trades = pd.DataFrame.from_records(data=c.fetchall(), columns=columns)
    logger.info("Recent trades fetched successfully.")
    return recent_trades

# 최근 수익성 평가 함수
def evaluate_performance(conn):
    trades_df = get_recent_trades(conn, days=30)
    if trades_df.empty:
        logger.info("No trades available for evaluation.")
        return None

    # 매매 기록을 기반으로 수익률 계산
    initial_balance = trades_df.iloc[-1]['krw_balance'] + trades_df.iloc[-1]['btc_balance'] * trades_df.iloc[-1]['btc_krw_price']
    final_balance = trades_df.iloc[0]['krw_balance'] + trades_df.iloc[0]['btc_balance'] * trades_df.iloc[0]['btc_krw_price']

    performance = (final_balance - initial_balance) / initial_balance * 100
    logger.info(f"30-day Performance: {performance:.2f}%")
    return performance

# 최근 거래 반성 및 평가를 생성하는 함수
def generate_reflection(trades_df, current_market_data):
    logger.info("Generating reflection based on recent trades and current market data...")
    
    performance = evaluate_performance(init_db())  # 30일 수익률 평가
    if performance is None:
        reflection = "No recent trading activity for reflection."
    else:
        if performance > 0:
            reflection = f"Performance over the last 30 days is positive: {performance:.2f}%. Strategy has been effective."
        else:
            reflection = f"Performance over the last 30 days is negative: {performance:.2f}%. Consider adjusting the strategy."
    
    logger.info(f"Reflection generated: {reflection}")
    return reflection

# GPT-4 API를 사용하여 매매 판단 요청
def get_gpt_decision(reflection, current_market_data):
    logger.info("Requesting trading decision from GPT...")
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    if not client.api_key:
        logger.error("OpenAI API key is missing or invalid.")
        return None

    # GPT에게 작업을 지시하는 구체적인 instruction 추가
    instruction = """
You are an expert Bitcoin investment advisor. Analyze the provided data and determine the optimal trading action (buy, sell, or hold). Follow these guidelines:

1. **Technical Indicators**: Analyze indicators such as RSI, MACD, moving averages, Bollinger Bands, and Stochastic Oscillators.
2. **Market Sentiment and News**: Consider the intensity of recent news headlines and market sentiment (Fear and Greed Index) to understand potential price movements.
3. **Risk Management**: When uncertain, prioritize minimizing risk (e.g., "hold" or low-percentage trades). If news suggests a strong positive/negative impact, reflect that in percentage.
4. **Reflection on Past Trading**: Use recent performance to avoid overly conservative or aggressive strategies.

Provide your response as JSON:
{
  "decision": "buy" or "sell" or "hold",
  "percentage": integer (1-100) for buy/sell, 0 for hold,
  "reason": "Reason for decision"
}
"""

    # GPT 요청 메시지
    messages = [
        {
            "role": "system",
            "content": instruction
        },
        {
            "role": "user",
            "content": f"""
Reflection: {reflection}
Current Market Data: {json.dumps(current_market_data, indent=2)}

Provide your response in the following JSON format:

{{
  "decision": "buy" or "sell" or "hold",
  "percentage": integer,
  "reason": "Your reasoning here"
}}
"""
        }
    ]

    # GPT 요청 데이터 로그 파일로 저장
    log_filename = datetime.now().strftime("%Y%m%d%H%M%S") + "_gpt_decision_input.log"
    try:
        with open(log_filename, 'w', encoding='utf-8') as log_file:
            json.dump(messages, log_file, ensure_ascii=False, indent=2)
        logger.info(f"Saved GPT decision input to log file: {log_filename}")
    except Exception as e:
        logger.error(f"Failed to save GPT decision input to log file: {e}")

    try:
        response = client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=messages,
            max_tokens=500
        )
        response_content = response.choices[0].message.content
        logger.info("GPT-4 decision received successfully.")
        logger.info(f"GPT-4 Response: {response_content}")
        return response_content
    except Exception as e:
        logger.error(f"Error requesting decision from GPT: {e}", exc_info=True)
        return None

# GPT-4 응답 파싱 함수
def parse_gpt_response(response_content):
    try:
        clean_content = response_content.replace("```json", "").replace("```", "").strip()
        response_json = json.loads(clean_content)
        decision = response_json.get("decision")
        percentage = response_json.get("percentage")
        reason = response_json.get("reason")
        return decision, percentage, reason
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing GPT response: {e}")
        return None, None, None

# 데이터프레임에 보조 지표를 추가하는 함수
def add_indicators(df):
    logger.info("Adding technical indicators to DataFrame...")
    indicator_bb = ta.volatility.BollingerBands(close=df['close'], window=20, window_dev=2)
    df['bb_bbm'] = indicator_bb.bollinger_mavg()
    df['bb_bbh'] = indicator_bb.bollinger_hband()
    df['bb_bbl'] = indicator_bb.bollinger_lband()
    
    df['rsi'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()
    macd = ta.trend.MACD(close=df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    
    df['sma_50'] = ta.trend.SMAIndicator(close=df['close'], window=50).sma_indicator()
    df['sma_200'] = ta.trend.SMAIndicator(close=df['close'], window=200).sma_indicator()
    
    stoch = ta.momentum.StochasticOscillator(high=df['high'], low=df['low'], close=df['close'], window=14, smooth_window=3)
    df['stoch_k'] = stoch.stoch()
    df['stoch_d'] = stoch.stoch_signal()
    
    logger.info("Technical indicators added successfully.")
    return df

# 공포 탐욕 지수 조회
def get_fear_and_greed_index():
    logger.info("Fetching Fear and Greed Index...")
    url = "https://api.alternative.me/fng/"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        logger.info("Fear and Greed Index fetched successfully.")
        return data['data'][0]
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching Fear and Greed Index: {e}", exc_info=True)
        return None

# 뉴스 데이터 가져오기
def get_bitcoin_news():
    logger.info("Fetching Bitcoin news headlines...")
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    if not serpapi_key:
        logger.error("SERPAPI API key is missing.")
        return []
    url = "https://serpapi.com/search.json"
    params = {"engine": "google_news", "q": "bitcoin OR btc", "api_key": serpapi_key}
    
    try:
        response = requests.get(url, params=params)
        news_results = response.json().get("news_results", [])
        headlines = [{"title": item.get("title", ""), "date": item.get("date", "")} for item in news_results[:6]]
        logger.info("Bitcoin news headlines fetched successfully.")
        return headlines
    except requests.RequestException as e:
        logger.error(f"Error fetching news: {e}", exc_info=True)
        return []

# 주문장 요약 함수
def summarize_orderbook(orderbook):
    logger.info("Summarizing orderbook data...")
    try:
        bids = orderbook.get('orderbook_units', [])[:5]
        asks = orderbook.get('orderbook_units', [])[:5]
        summary = {
            'bid_top_5': [{'price': bid['bid_price'], 'size': bid['bid_size']} for bid in bids],
            'ask_top_5': [{'price': ask['ask_price'], 'size': ask['ask_size']} for ask in asks]
        }
        logger.info("Orderbook summarized successfully.")
        return summary
    except Exception as e:
        logger.error(f"Error summarizing orderbook: {e}", exc_info=True)
        return {}

### 매매 결정 후 거래 실행
def make_trade(decision, percentage, krw_balance, btc_balance):
    if decision == "buy":
        amount_to_buy = krw_balance * (percentage / 100) * 0.9995  # 수수료 고려
        if amount_to_buy > 5000:
            logger.info(f"Placing BUY order: {percentage}% of available KRW (Amount: {amount_to_buy})")
            upbit.buy_market_order("KRW-BTC", amount_to_buy)
    elif decision == "sell":
        amount_to_sell = btc_balance * (percentage / 100)
        current_price = pyupbit.get_current_price("KRW-BTC")
        if amount_to_sell * current_price > 5000:
            logger.info(f"Placing SELL order: {percentage}% of held BTC (Amount: {amount_to_sell})")
            upbit.sell_market_order("KRW-BTC", amount_to_sell)

### 메인 AI 트레이딩 로직
def ai_trading():
    logger.info("Starting AI trading logic...")
    conn = init_db()
    all_balances = upbit.get_balances()
    filtered_balances = [balance for balance in all_balances if balance['currency'] in ['BTC', 'KRW']]
    orderbook_data = pyupbit.get_orderbook("KRW-BTC")

    if not orderbook_data:
        logger.error("Failed to retrieve orderbook.")
        return

    orderbook = orderbook_data[0] if isinstance(orderbook_data, list) and len(orderbook_data) > 0 else orderbook_data
    df_daily = pyupbit.get_ohlcv("KRW-BTC", interval="day", count=180)
    df_daily = add_indicators(dropna(df_daily)).tail(7)
    df_hourly = pyupbit.get_ohlcv("KRW-BTC", interval="minute60", count=168)
    df_hourly = add_indicators(dropna(df_hourly)).tail(12)

    fear_greed_index = get_fear_and_greed_index()
    news_headlines = get_bitcoin_news()

    current_market_data = {
        "fear_greed_index": fear_greed_index,
        "news_headlines": news_headlines,
    }

    reflection = generate_reflection(get_recent_trades(conn), current_market_data)
    if reflection is None:
        logger.error("Failed to generate reflection.")
        return
    
    gpt_response = get_gpt_decision(reflection, current_market_data)
    if gpt_response:
        decision, percentage, reason = parse_gpt_response(gpt_response)
        if decision and percentage is not None and reason:
            logger.info(f"GPT-4 Trading Decision: {gpt_response}")
            current_btc_price = pyupbit.get_current_price("KRW-BTC")
            btc_balance = next((float(balance['balance']) for balance in all_balances if balance['currency'] == 'BTC'), 0)
            krw_balance = next((float(balance['balance']) for balance in all_balances if balance['currency'] == 'KRW'), 0)
            btc_avg_buy_price = next((float(balance['avg_buy_price']) for balance in all_balances if balance['currency'] == 'BTC'), 0)

            # 거래 내역 DB에 저장
            log_trade(conn, decision, percentage, reason, gpt_response, btc_balance, krw_balance, btc_avg_buy_price, current_btc_price, reflection)
            make_trade(decision, percentage, krw_balance, btc_balance)
        else:
            logger.error("Failed to parse decision from GPT response.")
    else:
        logger.error("Failed to get a decision from GPT.")

    evaluate_performance(conn)
    logger.info("AI trading logic completed successfully.")

# 수동 테스트 실행 함수
def test_run():
    logger.info("Starting test run for AI trading logic...")
    ai_trading()
    logger.info("Test run completed.")

if __name__ == "__main__":
    # 데이터베이스 초기화
    init_db()

    # 테스트를 위한 수동 실행
    test_run()

    # 스케줄링 작업 설정 (6시간 간격으로 실행)
    # schedule.every().day.at("06:00").do(ai_trading)
    # schedule.every().day.at("12:00").do(ai_trading)
    # schedule.every().day.at("18:00").do(ai_trading)
    # schedule.every().day.at("00:00").do(ai_trading)
    logger.info("Scheduler initialized. Waiting for scheduled tasks to run.")

    while True:
        schedule.run_pending()
        time.sleep(1)
