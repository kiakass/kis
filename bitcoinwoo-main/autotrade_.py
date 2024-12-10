import os
import logging
import time
import schedule
import sqlite3
from datetime import datetime, timedelta
import argparse
from dotenv import load_dotenv
import pyupbit
import pandas as pd
import ta
from ta.utils import dropna

# .env 파일에 저장된 환경 변수를 불러오기 (API 키 등)
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Upbit 객체 생성
access = os.getenv("UPBIT_ACCESS_KEY")
secret = os.getenv("UPBIT_SECRET_KEY")
if not access or not secret:
    logger.error("API keys not found. Please check your .env file.")
    raise ValueError("Missing API keys. Please check your .env file.")
upbit = pyupbit.Upbit(access, secret)

# 거래 수수료 및 최소 거래 금액 설정
FEE_RATE = 0.0005  # 업비트 수수료는 0.05%
MIN_TRADE_AMOUNT = 5000  # 최소 거래 금액 5,000원

# 기본값 설정
default_coins = ['BTC', 'DOGE', 'XLM', 'XRP', 'SOL']
default_allocation = 20.0
default_data_interval = 'minute5'
default_fetch_interval = 1

# 명령줄 인자 파싱
parser = argparse.ArgumentParser(description='Crypto Trading Bot')
parser.add_argument('--auto', action='store_true', help='Run with default settings without user input')
args = parser.parse_args()

# 사용자로부터 입력 받기 또는 기본값 사용
if args.auto:
    coin_symbols = default_coins
    allocation_percentages = {coin: default_allocation for coin in coin_symbols}
    data_interval = default_data_interval
    fetch_interval = default_fetch_interval
else:
    print("===== Trading Bot Configuration =====")
    input_coins = input(f"Enter coin symbols to trade (default: {' '.join(default_coins)}): ").strip()
    if input_coins:
        coin_symbols = input_coins.upper().split()
    else:
        coin_symbols = default_coins

    allocation_percentages = {}
    for coin in coin_symbols:
        input_alloc = input(f"Enter allocation percentage for {coin} (default: {default_allocation}%): ").strip()
        if input_alloc:
            alloc = float(input_alloc)
        else:
            alloc = default_allocation
        allocation_percentages[coin] = alloc

    input_data_interval = input(f"Enter data interval (default: {default_data_interval}): ").strip()
    if input_data_interval:
        data_interval = input_data_interval
    else:
        data_interval = default_data_interval

    input_fetch_interval = input(f"Enter fetch interval in minutes (default: {default_fetch_interval}): ").strip()
    if input_fetch_interval:
        fetch_interval = int(input_fetch_interval)
    else:
        fetch_interval = default_fetch_interval

# 전체 할당 비율 검증
total_alloc = sum(allocation_percentages.values())
if total_alloc > 100:
    logger.error("Total allocation percentage exceeds 100%. Please adjust the allocations.")
    raise ValueError("Invalid allocation percentages.")

markets = [f"KRW-{coin}" for coin in coin_symbols]

# SQLite 데이터베이스 초기화 함수
def init_db():
    conn = sqlite3.connect('crypto_trades.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS trades
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT,
                  decision TEXT,
                  percentage REAL,
                  reason TEXT,
                  coin_symbol TEXT,
                  coin_balance REAL,
                  krw_balance REAL,
                  coin_avg_buy_price REAL,
                  coin_krw_price REAL,
                  reflection TEXT)''')
    conn.commit()
    return conn

# 거래 기록을 DB에 저장하는 함수
def log_trade(conn, decision, percentage, reason, coin_balance, krw_balance,
              coin_avg_buy_price, coin_krw_price, coin_symbol, reflection=''):
    c = conn.cursor()
    timestamp = datetime.now().isoformat()
    c.execute("""INSERT INTO trades 
                 (timestamp, decision, percentage, reason, coin_symbol, coin_balance, krw_balance,
                  coin_avg_buy_price, coin_krw_price, reflection) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (timestamp, decision, percentage, reason, coin_symbol, coin_balance, krw_balance,
               coin_avg_buy_price, coin_krw_price, reflection))
    conn.commit()

# 최근 투자 기록 조회
def get_recent_trades(conn, days=30):
    c = conn.cursor()
    days_ago = (datetime.now() - timedelta(days=days)).isoformat()
    c.execute("SELECT * FROM trades WHERE timestamp > ? ORDER BY timestamp ASC", (days_ago,))
    columns = [column[0] for column in c.description]
    trades_df = pd.DataFrame.from_records(data=c.fetchall(), columns=columns)
    return trades_df

# 최근 투자 기록을 기반으로 퍼포먼스 계산
def calculate_performance(trades_df):
    if trades_df.empty:
        return None, None
    initial_balance = trades_df.iloc[0]['krw_balance'] + trades_df.iloc[0]['coin_balance'] * trades_df.iloc[0]['coin_krw_price']
    final_balance = trades_df.iloc[-1]['krw_balance'] + trades_df.iloc[-1]['coin_balance'] * trades_df.iloc[-1]['coin_krw_price']
    if initial_balance == 0:
        return None, final_balance
    return (final_balance - initial_balance) / initial_balance * 100, initial_balance

# 데이터프레임에 보조 지표를 추가하는 함수
def add_indicators(df):
    # 볼린저 밴드 추가
    indicator_bb = ta.volatility.BollingerBands(close=df['close'], window=20, window_dev=2)
    df['bb_bbm'] = indicator_bb.bollinger_mavg()
    df['bb_bbh'] = indicator_bb.bollinger_hband()
    df['bb_bbl'] = indicator_bb.bollinger_lband()
    
    # RSI 추가
    df['rsi'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()
    
    # MACD 추가
    macd = ta.trend.MACD(close=df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['macd_diff'] = macd.macd_diff()

    return df

# 매매 결정 로직 수정: 신호 발생 시점에 매매가 이루어지도록 변경
def make_trading_decision(df):
    if len(df) < 2:
        return "hold", ""

    # 이전 행과 현재 행을 가져옵니다.
    prev_row = df.iloc[-2]
    last_row = df.iloc[-1]
    decision = "hold"
    reason = ""

    # 조건 1: 볼린저 밴드 상단 돌파와 RSI 과매수 진입 순간 -> 매도
    if (prev_row['close'] < prev_row['bb_bbh'] and last_row['close'] >= last_row['bb_bbh']) and \
       (prev_row['rsi'] <= 70 and last_row['rsi'] > 70):
        decision = "sell"
        reason = "Price just crossed above upper Bollinger Band and RSI entered overbought."
    # 조건 2: 볼린저 밴드 하단 돌파와 RSI 과매도 진입 순간 -> 매수
    elif (prev_row['close'] > prev_row['bb_bbl'] and last_row['close'] <= last_row['bb_bbl']) and \
         (prev_row['rsi'] >= 30 and last_row['rsi'] < 30):
        decision = "buy"
        reason = "Price just crossed below lower Bollinger Band and RSI entered oversold."
    # 조건 3: MACD 시그널 라인 상향 돌파 순간 -> 매수
    elif (prev_row['macd'] <= prev_row['macd_signal'] and last_row['macd'] > last_row['macd_signal']):
        decision = "buy"
        reason = "MACD line just crossed above signal line."
    # 조건 4: MACD 시그널 라인 하향 돌파 순간 -> 매도
    elif (prev_row['macd'] >= prev_row['macd_signal'] and last_row['macd'] < last_row['macd_signal']):
        decision = "sell"
        reason = "MACD line just crossed below signal line."

    return decision, reason

# 누적 매수 금액을 저장할 딕셔너리
cumulative_buy_amounts = {}

# 트레이딩 작업을 수행하는 함수
def job():
    try:
        conn = init_db()
        total_krw_balance = upbit.get_balance("KRW")
        logger.info(f"Total KRW Balance: {total_krw_balance}")

        for market, coin_symbol in zip(markets, coin_symbols):
            # 데이터 수집 및 보조 지표 계산
            df = pyupbit.get_ohlcv(market, interval=data_interval, count=100)
            if df is None or df.empty or len(df) < 2:
                continue
            df = dropna(df)
            df = add_indicators(df)
            
            # 매매 결정
            decision, reason = make_trading_decision(df)
            
            # 매매 신호 발생 시간
            signal_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 매매 실행 로직
            if decision in ["buy", "sell"]:
                coin_balance = upbit.get_balance(coin_symbol)
                krw_balance = upbit.get_balance("KRW")
                current_price = pyupbit.get_current_price(market)
                allocation_percentage = allocation_percentages[coin_symbol]
                allocation_amount = total_krw_balance * (allocation_percentage / 100)
                cumulative_buy = cumulative_buy_amounts.get(coin_symbol, 0)

                if decision == "buy":
                    remaining_alloc = allocation_amount - cumulative_buy
                    buy_amount = min(remaining_alloc, krw_balance)
                    if buy_amount >= MIN_TRADE_AMOUNT:
                        # 매매 시작 시간
                        trade_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        upbit.buy_market_order(market, buy_amount)
                        cumulative_buy_amounts[coin_symbol] = cumulative_buy + buy_amount
                        # 매매 완료 시간
                        trade_end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        logger.info(f"Signal Time: {signal_time}, Trade Start Time: {trade_start_time}, Trade End Time: {trade_end_time}, [{coin_symbol}] Executed BUY order for {buy_amount} KRW. Reason: {reason}")
                        # 거래 기록 저장 (매매가 실행된 경우에만)
                        log_trade(conn, decision, allocation_percentage, reason, coin_balance, krw_balance,
                                  upbit.get_avg_buy_price(coin_symbol), current_price, coin_symbol)
                    else:
                        logger.info(f"{signal_time} [{coin_symbol}] Not enough allocation or KRW balance to execute BUY. Remaining Allocation: {remaining_alloc:.2f} KRW, Available KRW: {krw_balance:.2f} KRW")
                elif decision == "sell":
                    sell_amount = coin_balance
                    sell_total = sell_amount * current_price
                    if sell_total >= MIN_TRADE_AMOUNT:
                        # 매매 시작 시간
                        trade_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        upbit.sell_market_order(market, sell_amount)
                        cumulative_buy_amounts[coin_symbol] = 0  # 매도 시 누적 매수 금액 초기화
                        # 매매 완료 시간
                        trade_end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        logger.info(f"Signal Time: {signal_time}, Trade Start Time: {trade_start_time}, Trade End Time: {trade_end_time}, [{coin_symbol}] Executed SELL order for {sell_amount} {coin_symbol}. Reason: {reason}")
                        # 거래 기록 저장 (매매가 실행된 경우에만)
                        log_trade(conn, decision, allocation_percentage, reason, coin_balance, krw_balance,
                                  upbit.get_avg_buy_price(coin_symbol), current_price, coin_symbol)
                    else:
                        logger.info(f"{signal_time} [{coin_symbol}] Not enough {coin_symbol} balance to execute SELL. Required: {MIN_TRADE_AMOUNT} KRW, Available: {sell_total:.2f} KRW")
            else:
                # "hold"인 경우 데이터베이스에 기록하지 않음
                continue

        conn.close()
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    # 데이터베이스 초기화
    conn = init_db()
    conn.close()
    
    # 백그라운드 실행 시에는 사용자 입력 없이 기본값 사용
    if not args.auto:
        # 초기 설정 정보 출력
        print("\n===== Trading Bot Configuration =====")
        print(f"Selected Coins and Allocation Percentages:")
        for coin in coin_symbols:
            print(f"- {coin}: {allocation_percentages[coin]}%")
        print(f"\nData Interval: {data_interval}")
        print(f"Fetch Interval: {fetch_interval} minute(s)")

        # 현재 잔고 및 수익률 계산
        total_krw_balance = upbit.get_balance("KRW")
        total_coin_valuation = 0
        for coin in coin_symbols:
            coin_balance = upbit.get_balance(coin)
            current_price = pyupbit.get_current_price(f"KRW-{coin}")
            total_coin_valuation += coin_balance * current_price
        current_total_valuation = total_krw_balance + total_coin_valuation

        # 초기 투자 금액 가져오기 (DB에서)
        conn = init_db()
        trades_df = get_recent_trades(conn)
        conn.close()
        if not trades_df.empty:
            performance, initial_balance = calculate_performance(trades_df)
        else:
            performance = None
            initial_balance = current_total_valuation  # 초기 투자 금액 설정

        if performance is not None:
            print(f"\nCurrent Profit Rate: {performance:.2f}%")
        else:
            print("\nNo previous trade data to calculate profit rate.")
        print(f"Current Cash Balance: {total_krw_balance:,.0f} KRW")
        print(f"Current Total Valuation: {current_total_valuation:,.0f} KRW")
        print("=====================================")

        # 거래 시작 여부 확인
        start_trading = input("Start trading? (Y/N): ").strip().lower()
        if start_trading != 'y':
            print("Trading bot has been terminated by user.")
            exit()

    logger.info("Starting trading bot...")

    # 즉시 job() 함수 실행
    job()

    # 실행 주기 설정 (데이터를 가져오는 주기)
    schedule.every(fetch_interval).minutes.do(job)

    while True:
        schedule.run_pending()
        time.sleep(1)
