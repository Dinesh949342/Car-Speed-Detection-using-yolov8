from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

# Import Views
from . import views as mainView  
from Admins import views as admins
from Users import views as usr

urlpatterns = [
    path('admin/', admin.site.urls),

    # Main Views
    path('', mainView.Base, name="base"),
    path('Home/', mainView.Home, name="Home"),
    path('UserLogin/', mainView.UserLogin, name="UserLogin"),
    path('AdminLogin/', mainView.AdminLogin, name="AdminLogin"),
    path('UserRegister/', mainView.UserRegister, name="UserRegister"),

    # Admin Views
    path("AdminHome/", admins.AdminHome, name="AdminHome"),
    path("AdminLoginCheck/", admins.AdminLoginCheck, name="AdminLoginCheck"),
    path('UserDetails/', admins.UserDetails, name='UserDetails'),
    path('ActivateUsers/', admins.ActivaUsers, name='ActivateUsers'),  

    # Live Streaming Views
    path('live_feed/', usr.live_feed, name='live_feed'),
    path('live_stream/', usr.live_stream_page, name='live_stream_page'),

    # User Views
    path("UserRegisterActions/", usr.UserRegisterActions, name="UserRegisterActions"),
    path("UserLoginCheck/", usr.UserLoginCheck, name="UserLoginCheck"),
    path("UserHome/", usr.UserHome, name="UserHome"),
    
    # Video Processing
    path('upload_video/', usr.upload_video, name='upload_video'),
    path('process_video/', usr.process_video, name='process_video'),  

    # Image Processing
    path('upload_image/', usr.upload_image, name='upload_image'),
    path('process_image/', usr.process_image, name='process_image'),
]

# Media Files Serving in Debug Mode
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
