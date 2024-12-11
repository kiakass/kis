# database/database_manager.py
import sqlite3
from datetime import datetime, timedelta
import pandas as pd

class DatabaseManager:
    def __init__(self, db_name="crypto_trades.db"):
        self.conn = sqlite3.connect(db_name)
        self._initialize_db()

    def _initialize_db(self):
        c = self.conn.cursor()
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
                      profit_amount REAL,
                      profit_rate REAL,
                      trade_start_time TEXT,
                      trade_end_time TEXT,
                      reflection TEXT)''')
        self.conn.commit()

    def log_trade(self, **kwargs):
        c = self.conn.cursor()
        c.execute("""INSERT INTO trades 
                     (timestamp, decision, percentage, reason, coin_symbol, coin_balance, krw_balance,
                      coin_avg_buy_price, coin_krw_price, profit_amount, profit_rate, trade_start_time, trade_end_time, reflection) 
                     VALUES (:timestamp, :decision, :percentage, :reason, :coin_symbol, :coin_balance, :krw_balance,
                             :coin_avg_buy_price, :coin_krw_price, :profit_amount, :profit_rate, :trade_start_time, :trade_end_time, :reflection)""",
                  kwargs)
        self.conn.commit()

    def get_recent_trades(self, days=30):
        c = self.conn.cursor()
        days_ago = (datetime.now() - timedelta(days=days)).isoformat()
        c.execute("SELECT * FROM trades WHERE timestamp > ? ORDER BY timestamp ASC", (days_ago,))
        columns = [column[0] for column in c.description]
        trades_df = pd.DataFrame.from_records(data=c.fetchall(), columns=columns)
        return trades_df