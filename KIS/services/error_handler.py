import logging
import traceback

class ErrorHandler:
    @staticmethod
    def log_error(error, message=None):
        """
        오류 로깅 및 추적
        :param error: 예외 객체
        :param message: 추가 메시지 (옵션)
        """
        logging.error(f"오류 발생: {error}")
        if message:
            logging.error(f"추가 정보: {message}")
        
        # 전체 스택 트레이스 로깅
        logging.error(traceback.format_exc())
    
    @staticmethod
    def handle_trading_error(error, notification_service=None):
        """
        거래 관련 오류 핸들링
        :param error: 예외 객체
        :param notification_service: 알림 서비스 (옵션)
        """
        ErrorHandler.log_error(error)
        
        if notification_service:
            error_message = f"거래 중 오류 발생: {str(error)}"
            notification_service.send_message(error_message)
    
    @staticmethod
    def safe_execute(func, *args, **kwargs):
        """
        안전한 함수 실행 데코레이터
        :param func: 실행할 함수
        :param args: 함수 위치 인자
        :param kwargs: 함수 키워드 인자
        :return: 함수 실행 결과 또는 None
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            ErrorHandler.log_error(e)
            return None