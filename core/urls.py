from django.urls import path
from . import views
from .views import HistoriqueCitoyenView, DechetDetailView, MesDeclarationsListView, HistoriqueCitoyenView
from django.conf import settings
from django.conf.urls.static import static



app_name = 'core'

urlpatterns = [
    path('declarer_dechet', views.declarer_dechet, name='declarer_dechet'),
    path("creer-citoyen/", views.creer_citoyen, name="creer_citoyen"),
    path('declaration-rapide/', views.declaration_rapide, name='declaration_rapide'),
    path("historique/", HistoriqueCitoyenView.as_view(), name="historique"),
    path('declaration/<int:pk>/', DechetDetailView.as_view(), name='detail_declaration'),
    path('mes-declarations/', MesDeclarationsListView.as_view(), name='mes_declarations'),
    path('suivi_collecte/<int:declaration_id>/', views.suivi_collecte, name='suivi_collecte'),
    # Exemple dans urls.py
    path('creer-profil/', views.profil_create, name='profile_create'),









    # --- Accueil et Authentification ---
    path('', views.home, name='home'),
    path('welcome/', views.welcome, name='welcome'),

    # --- Gestion des Déchets (Citoyens) ---




    path('tableau-de-bord/', views.CitoyenDashboardView.as_view(), name='dashboard'),


]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)