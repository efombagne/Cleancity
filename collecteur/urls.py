from django.urls import path
from . import views  # Importe les vues depuis collecteur/views.py
from .views import GérerCollecteView

app_name = 'collecteur'

urlpatterns = [
    path('dashboard/', views.CollecteurDashboardView.as_view(), name='dashboard'),
    # Dans collecteur/urls.py
    path('gerer/<int:pk>/',GérerCollecteView.as_view(), name='gerer_collecte'),
    path('ajouter/', views.AjouterCollecteView.as_view(), name='ajouter_collecte'),
# Dans ton fichier urls.py
    path('selectionner-dechets/', views.selectionner_declarations, name='selection_dechets'),
    # Dans collecteur/urls.py
    path('finaliser-collecte/<int:id>/', views.finaliser_collecte, name='finaliser_collecte'),
    path('register/', views.register_collecteur_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('a-gerer/', views.collection_liste, name='collection_liste'),

]
