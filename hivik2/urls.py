"""
URL configuration for hivik2 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from got.views import CustomPasswordResetView
from django.views.generic import RedirectView

from rest_framework import routers
from iot import views
from django.views.generic import TemplateView


router = routers.DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'groups', views.GroupViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('got/', include('got.urls')),
    path('got/preoperacional/', include('preoperacionales.urls')),
    path('outbound/', include('outbound.urls')),
    path('meg/', include('meg.urls')),
    path('inv/', include('inv.urls')),
    path('dth/', include('dth.urls', namespace='dth')),
    path('mto/', include('mto.urls', namespace='mto')),
    path('ope/', include('ope.urls', namespace='ope')),
    path('cont/', include('cont.urls', namespace='cont')),
    path('tic/', include('tic.urls', namespace='tic')),
    path('ntf/', include('ntf.urls', namespace='ntf')),
    path('permissions/', include('permissions_management.urls', namespace='permissions_management')),
    path('', RedirectView.as_view(url='got/', permanent=True)),

    path('', include('pwa.urls')),

    path('serviceworker.js', (TemplateView.as_view(
        template_name="serviceworker.js",
        content_type='application/javascript'
    )), name='serviceworker'),
    
    # path('', include(router.urls)),
    # path('api-auth/', include('rest_framework.urls', namespace='rest_framework')), # probando api restframework django

    path('accounts/password_reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('accounts/password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('accounts/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('accounts/reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('accounts/', include('django.contrib.auth.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) 
