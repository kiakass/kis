import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(page_title='Crypto Trading Performance', layout='wide')

# 제목
st.title('암호화폐 트레이딩 성과 대시보드')

# 사이드바에서 계좌의 시초가 입력받기
initial_balance = st.sidebar.number_input('계좌의 시초가를 입력하세요 (KRW)', min_value=0.0, value=1000000.0)

# SQLite 데이터베이스 연결
conn = sqlite3.connect('crypto_trades.db')

# 거래 데이터 읽어오기
trades_df = pd.read_sql_query("SELECT * FROM trades", conn)

# 데이터베이스 연결 종료
conn.close()

# 'trade_end_time'을 datetime 형식으로 변환
trades_df['trade_end_time'] = pd.to_datetime(trades_df['trade_end_time'])

# 'sell' 거래만 필터링하여 수익 계산
sell_trades = trades_df[trades_df['decision'] == 'sell'].copy()
sell_trades.sort_values('trade_end_time', inplace=True)

# 수익 금액이 없는 경우 0으로 대체
sell_trades['profit_amount'].fillna(0, inplace=True)

# 누적 수익 금액 계산
if not sell_trades.empty:
    sell_trades.set_index('trade_end_time', inplace=True)
    daily_profit = sell_trades['profit_amount'].resample('D').sum().cumsum()
    daily_profit_rate = (daily_profit / initial_balance) * 100

    # 날짜 인덱스 설정 및 결측치 처리
    daily_profit_rate = daily_profit_rate.reindex(
        pd.date_range(daily_profit_rate.index.min(), daily_profit_rate.index.max()),
        method='ffill'
    )
    daily_profit_rate.index.name = '날짜'
else:
    daily_profit_rate = pd.Series(dtype=float)

# 총 수익 금액 계산
total_profit = sell_trades['profit_amount'].sum()

# 수익률 계산
if initial_balance > 0:
    profit_rate = (total_profit / initial_balance) * 100
else:
    profit_rate = 0

# 현재 수익 금액과 수익률 출력
st.header('현재 수익 현황')
st.write(f'**총 수익 금액:** {total_profit:,.2f} KRW')
st.write(f'**총 수익률:** {profit_rate:.2f}%')

# 거래 이력 테이블 출력
st.header('거래 이력')

if not sell_trades.empty:
    trade_history = sell_trades.reset_index()[['trade_end_time', 'coin_symbol', 'profit_amount', 'profit_rate']]
    trade_history.rename(columns={
        'trade_end_time': '매매 시간',
        'coin_symbol': '코인',
        'profit_amount': '수익 금액 (KRW)',
        'profit_rate': '수익률 (%)'
    }, inplace=True)
    trade_history['수익 금액 (KRW)'] = trade_history['수익 금액 (KRW)'].round(2)
    trade_history['수익률 (%)'] = trade_history['수익률 (%)'].round(2)
    st.dataframe(trade_history.reset_index(drop=True))
else:
    st.write('매도 거래 내역이 없습니다.')

# 수익률 추이 그래프 출력
st.header('일별 수익률 추이')

if not daily_profit_rate.empty:
    st.line_chart(daily_profit_rate)
else:
    st.write('수익률 추이를 표시할 데이터가 없습니다.')
