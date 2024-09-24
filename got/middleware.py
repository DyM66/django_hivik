# middleware.py
import time
import logging

logger = logging.getLogger(__name__)

class RequestTimingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        end_time = time.time()
        total_time = end_time - start_time
        logger.debug(f"Tiempo total de procesamiento del servidor: {total_time} segundos")
        return response
