from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsSuperuser(BasePermission):
    message = 'Permission denied, you are not the superuser'

    def has_permission(self, request, view):
        return request.user.is_superuser


class UserIsOwner(BasePermission):
    message = 'Permission denied, you do not have permission to perform this action.'

    def has_object_permission(self, request, view, obj):

        return obj.id == request.user.id
