# scheduler/scheduler.py
import schedule
import time

class Scheduler:
    def __init__(self, job, interval):
        self.job = job
        self.interval = interval

    def start(self):
        schedule.every(self.interval).minutes.do(self.job)
        while True:
            schedule.run_pending()
            time.sleep(1)