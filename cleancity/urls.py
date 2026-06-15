
from django.contrib import admin
from django.contrib.auth import views
from django.urls import path, include
from django.views.generic import RedirectView

# Dans ton urls.py principal
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('', RedirectView.as_view(pattern_name='core:welcome', permanent=False)),
    # Ici, on pointe vers le module 'collecteur' et son fichier 'urls.py'
    path('collecteur/', include('collecteur.urls', namespace='collecteur')),

]