from django.urls import path
from . import views

app_name = "accounts"
urlpatterns = [
    path('register/', views.SellerRegister.as_view(), name='register'),
    path('login/', views.SellerLogin.as_view(), name='login'),
    path('refresh/', views.RefreshToken.as_view(), name='refresh'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('logout_all/', views.LogoutAll.as_view(), name='logout_all'),
    path('active_login/', views.CheckAllActiveLogin.as_view(), name='active_login'),
    path('selected_logout/', views.SelectedLogout.as_view(), name='selected_logout'),
]
