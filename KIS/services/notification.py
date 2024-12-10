# 3. services/notification.py
#python
import requests
import datetime

class NotificationService:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url
    
    def send_message(self, msg):
        """Discord 메시지 전송"""
        now = datetime.datetime.now()
        message = {"content": f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {str(msg)}"}
        try:
            response = requests.post(self.webhook_url, data=message)
            response.raise_for_status()
            print(message)
        except requests.exceptions.RequestException as e:
            print(f"Notification failed: {e}")