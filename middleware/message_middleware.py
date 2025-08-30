# Create file: middleware/message_middleware.py
from django.contrib import messages

class MessageCleanupMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Before processing the request
        if request.user.is_authenticated:
            # Limit messages to 10 per user
            storage = messages.get_messages(request)
            message_list = list(storage)
            
            if len(message_list) > 10:
                # Keep only the last 10 messages
                storage._loaded_messages = message_list[-10:]

        response = self.get_response(request)
        return response