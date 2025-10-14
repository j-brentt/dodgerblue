from django.urls import path
from django.contrib.auth import views as auth_views
from authors.forms import CustomAuthenticationForm
from . import views
app_name = 'authors'

urlpatterns = [
    # Root as login page
    path('', auth_views.LoginView.as_view(template_name='authors/login.html'), name='login'), 
    
    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='authors/login.html', authentication_form = CustomAuthenticationForm ), name='login'), 
    path('logout/', auth_views.LogoutView.as_view(next_page='authors:login'), name='logout'),
    path('signup/', views.signup, name='signup'),

    # Profile management
    path('profile/<uuid:author_id>/', views.profile_detail, name='profile_detail'),
    path('<str:author_id>/edit/', views.profile_edit, name='profile_edit'),

    # Main app pages (requires login)
    path('stream/', views.stream, name='stream'),
]