from rest_framework import permissions

class IsNotAuthenticated(permissions.BasePermission):
    """
    Chỉ cho phép những người dùng chưa được xác thực (chưa đăng nhập) truy cập API.
    """

    def has_permission(self, request, view):
        return not request.user.is_authenticated


