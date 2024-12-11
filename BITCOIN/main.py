# main.py
import logging
from config.config_manager import ConfigManager
from database.database_manager import DatabaseManager
from indicators.indicator_calculator import IndicatorCalculator
from trade.trade_bot import TradeBot
from scheduler.scheduler import Scheduler

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    config_manager = ConfigManager()
    access_key, secret_key = config_manager.get_keys()

    db_manager = DatabaseManager()
    indicator_calculator = IndicatorCalculator()
    trade_bot = TradeBot(access_key, secret_key, db_manager, indicator_calculator)

    def job():
        logging.info("Executing scheduled trading job...")
        # Add job logic here

    scheduler = Scheduler(job, interval=15)  # 15 minutes interval
    scheduler.start()
