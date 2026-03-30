from django.shortcuts import redirect
from django.urls import reverse
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed

class JWTAuthCookieMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Define routes that do NOT need protection
        public_paths = ['/login/', '/api/token/'] 
        
        if request.path in public_paths or request.path.startswith('/static/'):
            return self.get_response(request)

        # 2. Look for the token in the cookies
        token = request.COOKIES.get('access_token')

        if not token:
            return redirect('login') # Redirect to your login view name

        # 3. Validate the token
        jwt_auth = JWTAuthentication()
        try:
            validated_token = jwt_auth.get_validated_token(token)
            user = jwt_auth.get_user(validated_token)
            request.user = user # Attach user to the request
        except (InvalidToken, AuthenticationFailed):
            # Token is expired or invalid
            response = redirect('login')
            response.delete_cookie('access_token') # Clean up bad token
            return response

        # 4. If everything is good, load the page
        response = self.get_response(request)
        return response