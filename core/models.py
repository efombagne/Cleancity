from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager


# =========================
# UTILISATEUR DE BASE
# =========================

class Utilisateur(AbstractUser):
    role = models.CharField(max_length=50, default='citoyen')

    groups = models.ManyToManyField("auth.Group", related_name="utilisateur_groups", blank=True)
    user_permissions = models.ManyToManyField("auth.Permission", related_name="utilisateur_permissions", blank=True)
    objects = UserManager()

    @property
    def profil(self):
        if self.role == 'citoyen': return getattr(self, 'citoyen', None)
        if self.role == 'collecteur': return getattr(self, 'collecteur', None)
        if self.role == 'recycleur': return getattr(self, 'recycleur', None)
        return None

    def __str__(self):
        return self.username


# =========================
# PROFILS SPÉCIFIQUES
# =========================

class Citoyen(models.Model):
    user = models.OneToOneField(Utilisateur, on_delete=models.CASCADE, primary_key=True)
    adresse = models.CharField(max_length=255)
    quartier = models.CharField(max_length=100, blank=True)
    code_postal = models.CharField(max_length=10, blank=True)
    preference_collecte = models.CharField(max_length=50, blank=True)
    points_recompense = models.PositiveIntegerField(default=0)
    date_inscription = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username


class Collecteur(models.Model):
    user = models.OneToOneField(Utilisateur, on_delete=models.CASCADE, primary_key=True)
    zone_couverture = models.CharField(max_length=255)
    vehicule = models.CharField(max_length=100)

    def __str__(self):
        return self.user.username


class Recycleur(models.Model):
    user = models.OneToOneField(Utilisateur, on_delete=models.CASCADE, primary_key=True)
    type_materiaux = models.CharField(max_length=100)
    capacite = models.IntegerField()


# =========================
# GESTION DES DÉCHETS & COLLECTES
# =========================

class Dechet(models.Model):
    # Ajout de CHOICES pour permettre l'utilisation de get_type_display()
    TYPE_CHOICES = [
        ('plastique', 'Plastique'),
        ('verre', 'Verre'),
        ('metal', 'Métal'),
        ('organique', 'Organique'),
        ('papier', 'Papier'),
    ]

    citoyen = models.ForeignKey(Citoyen, on_delete=models.CASCADE, related_name="dechets")
    type = models.CharField(max_length=100, choices=TYPE_CHOICES)  # Corrigé ici
    poids = models.FloatField()
    localisation = models.CharField(max_length=255)
    etat = models.CharField(max_length=50, default="en_attente")
    collecteur = models.ForeignKey(Collecteur, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="dechets_collectes")
    image = models.ImageField(upload_to='dechets/', null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_type_display()} - {self.poids}kg"


class Collecte(models.Model):
    date = models.DateField()
    statut = models.CharField(max_length=50,
                              choices=[('en_attente', 'En attente'), ('en_cours', 'En cours'), ('termine', 'Terminé')],
                              default='en_attente')
    itineraire = models.TextField()
    collecteur = models.ForeignKey(Collecteur, on_delete=models.CASCADE, related_name="collectes")
    dechets = models.ManyToManyField(Dechet, related_name="collectes", blank=True)

    def __str__(self):
        return f"Collecte {self.id} - {self.date}"


# =========================
# AUTRES MODULES
# =========================

class DemandeCollecte(models.Model):
    citoyen = models.ForeignKey(Citoyen, on_delete=models.CASCADE, related_name="demandes")
    date_souhaitee = models.DateTimeField()
    statut = models.CharField(max_length=20, choices=[('en_attente', 'En attente'), ('approuvee', 'Approuvée')],
                              default='en_attente')


class Notification(models.Model):
    contenu = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    destinataire = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name="notifications")


class Administrateur(models.Model):
    user = models.OneToOneField(Utilisateur, on_delete=models.CASCADE, primary_key=True)
    niveau_acces = models.IntegerField(default=1)

    def __str__(self):
        return self.user.username


class Rapport(models.Model):
    type = models.CharField(max_length=100)
    periode = models.CharField(max_length=100)
    auteur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name="rapports")