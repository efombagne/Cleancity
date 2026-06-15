from django.contrib import admin
from .models import Utilisateur, Citoyen, Collecteur, Recycleur, Dechet, Collecte, DemandeCollecte, Notification

# Enregistrez uniquement les modèles présents dans votre fichier models.py
admin.site.register(Utilisateur)
admin.site.register(Citoyen)
admin.site.register(Collecteur)
admin.site.register(Recycleur)
admin.site.register(Dechet)
admin.site.register(Collecte)
admin.site.register(DemandeCollecte)
admin.site.register(Notification)