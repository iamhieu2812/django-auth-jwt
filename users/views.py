import uuid
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import logout
from users.models import CustomUser, Image
from .serializers import CustomUserSerializer, ImageSerializer
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .permissions import IsNotAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate
from datetime import timedelta
from django.core.cache import cache
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.response import Response
from rest_framework import status


class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get('refresh')
        
        # Kiểm tra xem refresh token có trong danh sách blacklist không
        if cache.get(refresh_token) == "blacklisted":
            return Response({'error': 'Refresh token has been blacklisted'}, status=status.HTTP_400_BAD_REQUEST)
        
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == status.HTTP_200_OK:
            # Lấy old access token từ refresh token thông qua redis
            old_access_token = cache.get(refresh_token)
            # Cho old access token vào blacklist
            cache.set(old_access_token, "blacklisted", 900)
            # Lấy access token mới từ response
            new_access_token = response.data.get('access')
            
            # Đưa access token vào refresh token
            cache.set(refresh_token, new_access_token, 900) 
            
        return response


@api_view(['POST'])
@permission_classes([IsNotAuthenticated])
def registration_view(request):
    if request.method == 'POST':
        print("jaovnavnuiaevpvuj")
        data = request.data
        data['password'] = make_password(data['password'])
        serializer = CustomUserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            response_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsNotAuthenticated])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(request, username=username, password=password)
    
    if user is not None:
        old_refresh_token = cache.get(f"{user.id}")
        cache.delete(f"{user.id}")
        old_access_token = cache.get(old_refresh_token)
        cache.set(old_refresh_token, "blacklisted", 1500)
        cache.set(old_access_token, "blacklisted", 900)
        refresh = RefreshToken.for_user(user)
        
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        
        cache.set(f"{user.id}", refresh_token, 1500)
        cache.set(refresh_token, access_token, 900)
        
        print(user.id)
        
        return Response({'access_token': access_token, 'refresh_token': refresh_token}, status=status.HTTP_200_OK)
    
    return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    user = request.user
    # Lấy access token từ request.auth
    access_token = request.auth
    refresh_token = cache.get(f"{user.id}")

    if access_token:
        # Thêm access token vào danh sách blacklist
        cache.set(str(access_token), 'blacklisted', int(access_token.lifetime.total_seconds()))
        cache.delete(f"{user.id}")
        cache.set(refresh_token, "blacklisted", 1500)
        return Response({'detail': 'Logout successful'}, status=status.HTTP_200_OK)

    return Response({'detail': 'Token is required'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_list(request):
    users = CustomUser.objects.all()
    serializer = CustomUserSerializer(users, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsNotAuthenticated])
def forgot_password(request):
    # Lấy thông tin người dùng từ request
    username = request.data.get('username')

    # Kiểm tra xem người dùng có tồn tại trong hệ thống hay không
    try:
        user = CustomUser.objects.get(username=username)
    except CustomUser.DoesNotExist:
        return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    # Tạo một mã token đặc biệt cho việc đặt lại mật khẩu
    reset_token = str(uuid.uuid4())

    # Lưu mã token vào Redis với thời gian hết hạn 5 phút
    cache.set(reset_token, str(user.pk), 300)

    # Tạo link dẫn đến API "confirm reset password" với mã token
    reset_link = f'http://localhost:8000/api/reset-password/{reset_token}/'

    return Response({'reset_link': reset_link}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsNotAuthenticated])
def confirm_reset_password(request, reset_token):
    # Lấy mã token từ URL
    token = reset_token

    # Kiểm tra xem mã token có tồn tại trong Redis không
    user_pk = cache.get(token)

    if not user_pk:
        return Response({'detail': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)

    # Lấy thông tin người dùng từ user_pk
    try:
        user = CustomUser.objects.get(pk=user_pk)
    except CustomUser.DoesNotExist:
        return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    # Lấy thông tin mật khẩu mới từ request
    new_password = request.data.get('new_password')

    # Kiểm tra xem mật khẩu mới có đủ độ dài
    if len(new_password) < 8:
        return Response({'detail': 'Password must be at least 8 characters long'}, status=status.HTTP_400_BAD_REQUEST)

    # Kiểm tra xem mật khẩu mới có chứa ký tự đặc biệt
    special_characters = "!@#$%^&*()-_=+[]{}|;:'\",.<>?/"
    if any(char in special_characters for char in new_password):
        return Response({'detail': 'Password must contain at least one special character'}, status=status.HTTP_400_BAD_REQUEST)
    
    refresh_token = cache.get(f"{user.id}")
    cache.delete(f"{user.id}")
    cache.set(refresh_token, "blacklisted", 1500)

    # Cập nhật mật khẩu của người dùng
    user.set_password(new_password)
    user.save()

    # Xóa mã token khỏi Redis sau khi đã sử dụng
    cache.delete(token)

    return Response({'detail': 'Password reset successful'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_password(request):
    # Lấy người dùng hiện tại từ request
    user = request.user

    # Lấy thông tin mật khẩu mới từ request
    new_password = request.data.get('new_password')

    # Kiểm tra xem mật khẩu mới có đủ độ dài
    if len(new_password) < 8:
        return Response({'detail': 'Password must be at least 8 characters long'}, status=status.HTTP_400_BAD_REQUEST)
    
    special_characters = "!@#$%^&*()-_=+[]{}|;:'\",.<>?/"
    if any(char in special_characters for char in new_password):
        return Response({'detail': 'Password must contain at least one special character'}, status=status.HTTP_400_BAD_REQUEST)

    # Cập nhật mật khẩu của người dùng
    user.set_password(new_password)
    user.save()

    # Đưa access token vào danh sách đen (blacklist) trong Redis
    access_token = request.auth
    refresh_token = cache.get(f"{user.id}")
    
    if access_token:
        cache.set(str(access_token), 'blacklisted', int(access_token.lifetime.total_seconds()))
    
    if refresh_token:
        cache.delete(f"{user.id}")
        cache.set(refresh_token, "blacklisted", 1500)

    # Đăng xuất người dùng để đảm bảo họ phải đăng nhập lại với mật khẩu mới
    logout(request)

    return Response({'detail': 'Password updated successfully. Please log in again with your new password.'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def ban_user(request):
    target_username = request.data.get('target_username')

    try:
        target_user = CustomUser.objects.get(username=target_username)
    except CustomUser.DoesNotExist:
        return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    
    refresh_token = cache.get(f"{target_user.id}")
    cache.delete(f"{target_user.id}")
    cache.set(refresh_token, "blacklisted", 1500)
    
    print(refresh_token)

    target_user.is_active = False  
    target_user.save()

    return Response({'detail': f'User {target_user.username} has been banned'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_image(request):
    serializer = ImageSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
