from django.urls import path
from . import views
from .views import CustomTokenRefreshView



from rest_framework_simplejwt.views import (
    TokenRefreshView,
)


urlpatterns = [
    path('register/', views.registration_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('forgot-password/', views.forgot_password, name='forgot-password'),
    path('reset-password/<str:reset_token>/', views.confirm_reset_password, name='reset-password'),
    path('update-password/', views.update_password, name='update-password'),
    
    path('users/', views.user_list, name='user-list'),
    path('ban-user/', views.ban_user, name='ban-user'),
    
    path('upload/', views.upload_image, name='upload-image'),
    
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
]