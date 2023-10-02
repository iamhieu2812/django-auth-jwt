from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken

class BlacklistMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        authorization_header = request.META.get('HTTP_AUTHORIZATION')

        if authorization_header:
            token_type, token = authorization_header.split(' ')

            if token_type == 'Bearer':
                # Kiểm tra xem token có trong danh sách blacklist không
                if cache.get(token) == "blacklisted":
                    raise AuthenticationFailed('Token is blacklisted')

                # Kiểm tra xem token có phải là refresh token không
                try:
                    token_obj = RefreshToken(token)
                    print(token_obj)
                    if token_obj.access_token.lifetime.total_seconds() <= 0:
                        raise AuthenticationFailed('Token has expired')
                except Exception:
                    pass

        response = self.get_response(request)
        return response
