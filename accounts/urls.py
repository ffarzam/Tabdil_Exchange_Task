from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.SellerRegister.as_view(), name='register'),
    path('login/', views.SellerLogin.as_view(), name='login'),
    path('refresh/', views.RefreshToken.as_view(), name='refresh'),
    # path('verify_account_request/', views.VerifyAccountRequestView.as_view(), name='verify_account_request'),
    # path('verify_account/<str:uidb64>/<str:token>/', views.VerifyAccount.as_view(), name='verify_account'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('logout_all/', views.LogoutAll.as_view(), name='logout_all'),
    path('active_login/', views.CheckAllActiveLogin.as_view(), name='active_login'),
    path('selected_logout/', views.SelectedLogout.as_view(), name='selected_logout'),
    #
    path('disable_account/<str:user_spec>/', views.DisableAccount.as_view(), name='disable_account'),
    path('enable_account/<str:user_spec>/', views.EnableAccount.as_view(), name='enable_account'),
]
