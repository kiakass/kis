# trade/trade_bot.py
import pyupbit
import logging
from datetime import datetime

class TradeBot:
    def __init__(self, access_key, secret_key, database_manager, indicator_calculator):
        self.upbit = pyupbit.Upbit(access_key, secret_key)
        self.db_manager = database_manager
        self.indicator_calculator = indicator_calculator
        self.logger = logging.getLogger(__name__)

    def make_decision(self, df):
        if len(df) < 2:
            return "hold", ""

        prev_row = df.iloc[-2]
        last_row = df.iloc[-1]
        decision, reason = "hold", ""

        if (prev_row['close'] < prev_row['bb_bbh'] and last_row['close'] >= last_row['bb_bbh']) and \
           (prev_row['rsi'] <= 70 and last_row['rsi'] > 70):
            decision, reason = "sell", "Price crossed upper BB and RSI overbought."
        elif (prev_row['close'] > prev_row['bb_bbl'] and last_row['close'] <= last_row['bb_bbl']) and \
             (prev_row['rsi'] >= 30 and last_row['rsi'] < 30):
            decision, reason = "buy", "Price crossed lower BB and RSI oversold."
        elif prev_row['macd'] <= prev_row['macd_signal'] and last_row['macd'] > last_row['macd_signal']:
            decision, reason = "buy", "MACD crossed above signal line."
        elif prev_row['macd'] >= prev_row['macd_signal'] and last_row['macd'] < last_row['macd_signal']:
            decision, reason = "sell", "MACD crossed below signal line."

        return decision, reason

    def execute_trade(self, decision, market, allocation, krw_balance):
        if decision == "buy":
            amount_to_buy = krw_balance * (allocation / 100)
            if amount_to_buy >= 5000:
                self.upbit.buy_market_order(market, amount_to_buy)
                self.logger.info(f"Executed BUY order for {amount_to_buy} KRW on {market}.")
        elif decision == "sell":
            coin_balance = self.upbit.get_balance(market.replace("KRW-", ""))
            if coin_balance * pyupbit.get_current_price(market) >= 5000:
                self.upbit.sell_market_order(market, coin_balance)
                self.logger.info(f"Executed SELL order for {coin_balance} on {market}.")
