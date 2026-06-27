from datetime import timezone, timedelta
from django.db.models import Q  # N'oubliez pas cet import pour vos recherches
from django.db import models
from django.db.models import Sum, Count
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Sum, Count
from django.utils import timezone
import json
from django.db.models.functions import ExtractMonth
from datetime import timedelta
from .models import (
    Utilisateur,
    Citoyen,
    Collecteur,
    Dechet,
    Collecte,
    DemandeCollecte,
    Notification
)
from .forms import CollecteForm, CitoyenForm

User = get_user_model()


# =========================================================
# 🔥 DECLARER DECHET (CORRIGÉ + SAFE)
# =========================================================
@login_required
def declarer_dechet(request):
    # 1. Vérification sécurisée du profil Citoyen
    if not hasattr(request.user, 'citoyen'):
        messages.error(request, "Veuillez d'abord compléter votre profil citoyen.")
        return redirect('core:profile_create')  # Remplace par ton URL de création de profil

    if request.method == "POST":
        # 2. Utilisation sécurisée
        citoyen = request.user.citoyen

        type_dechet = request.POST.get("type")
        poids = request.POST.get("poids")
        localisation = request.POST.get("localisation")
        image = request.FILES.get('image')

        # 3. Création de l'objet
        Dechet.objects.create(
            citoyen=citoyen,
            type=type_dechet,
            poids=poids,
            image=image,
            localisation=localisation,
            etat="en_attente"
        )

        messages.success(request, "Déclaration effectuée avec succès !")
        return redirect("core:dashboard")

    return render(request, "citoyen/declarer_dechet.html")


def profil_create(request):
    template_name = 'profil_create.html'


    if hasattr(request.user, 'citoyen'):
        messages.info(request, "Votre profil est déjà configuré.")
        return redirect("core:dashboard")

    if request.method == "POST":
        form = CitoyenForm(request.POST)
        if form.is_valid():
            citoyen = form.save(commit=False)
            citoyen.user = request.user
            citoyen.save()
            messages.success(request, "Bienvenue ! Votre profil a été initialisé.")
            return redirect("core:dashboard")
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    else:
        form = CitoyenForm()

    return render(request, "citoyen/profil_create.html", {"form": form})


def declaration_rapide(request):
    if request.method == 'POST':
        # 1. Récupération des données du formulaire textuel
        type_dechet = request.POST.get('type_dechet')
        quantite = request.POST.get('quantite')
        unite = request.POST.get('unite')
        position = request.POST.get('position')
        urgent = request.POST.get('urgent') == 'on'  # Renvoie True si coché
        notes = request.POST.get('notes')

        # 2. Récupération du fichier photo
        photo = request.FILES.get('photo_dechet')

        # [Optionnel] Ici, tu pourras enregistrer ces données dans un modèle en base de données
        # Exemple : Dechet.objects.create(type=type_dechet, quantite=quantite, ...)

        # Message de succès et redirection
        messages.success(request, "Votre déclaration a bien été enregistrée !")
        return redirect('core:dashboard')

    # Si c'est une requête GET, on affiche simplement le formulaire
    return render(request, 'citoyen/declaration_rapide.html')




class MesDeclarationsListView(LoginRequiredMixin, ListView):
    model = Dechet
    template_name = 'citoyen/mes_declarations.html'
    context_object_name = 'mes_dechets'

    def get_queryset(self):
        # On récupère uniquement les déchets du citoyen connecté
        queryset = Dechet.objects.filter(citoyen=self.request.user.citoyen).order_by('-date_creation')

        # Gestion dynamique de la barre de recherche (Recherche par ID ou par Type)
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(id__icontains=query.replace('#c', '').replace('7621bc', '')) |
                Q(type__icontains=query)
            )

        # Gestion dynamique du filtre par Statut
        statut = self.request.GET.get('statut')
        if statut:
            queryset = queryset.filter(etat=statut)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        citoyen = self.request.user.citoyen

        # 1. Total des déclarations (sans filtre de recherche)
        context['total_dechets'] = Dechet.objects.filter(citoyen=citoyen).count()

        # 2. Nombre de collectes terminées / recyclées
        context['collectes_terminees'] = Dechet.objects.filter(
            citoyen=citoyen,
            etat__in=['termine', 'recycle']
        ).count()

        # 3. Somme totale du poids collecté (coordonné avec l'indicateur orange)
        poids_agg = Dechet.objects.filter(
            citoyen=citoyen,
            etat__in=['termine', 'recycle']
        ).aggregate(Sum('poids'))

        # get('poids__sum') renvoie None si pas de déchet, d'où le "or 0"
        context['total_poids'] = round(poids_agg.get('poids__sum') or 0, 1)

        # 4. Points cumulés du citoyen
        context['points'] = citoyen.points_recompense

        return context





class DechetDetailView(LoginRequiredMixin, DetailView):
    model = Dechet
    template_name = 'citoyen/detail.html'
    context_object_name = 'dechet'

    # pk_url_kwarg est 'pk' par défaut, donc inutile de le redéfinir si votre URL utilise <int:pk>

    def get_queryset(self):
        # Sécurité : On vérifie d'abord si l'utilisateur possède un profil citoyen
        if hasattr(self.request.user, 'citoyen'):
            # Retourne uniquement les déchets appartenant au citoyen connecté
            return Dechet.objects.filter(citoyen=self.request.user.citoyen)

        # Si ce n'est pas un citoyen (ex: collecteur), il ne doit pas voir ce détail
        return Dechet.objects.none()


def suivi_collecte(request, declaration_id):
    # On cherche un objet Dechet, pas Declaration
    dechet = get_object_or_404(Dechet, pk=declaration_id)
    context = {
        'declaration': dechet, # On garde le nom 'declaration' pour ne pas changer le template
    }
    return render(request, 'citoyen/suivi_collecte.html', context)



class CitoyenDashboardView(LoginRequiredMixin, ListView):
    model = Dechet
    template_name = "citoyen/dashboard.html"
    context_object_name = "mes_dechets"

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, "citoyen"):
            return Dechet.objects.filter(citoyen=user.citoyen).order_by("-id")
        return Dechet.objects.none()

    def post(self, request, *args, **kwargs):
        user = request.user
        if hasattr(user, "citoyen"):
            citoyen = user.citoyen
            type_dechet = request.POST.get("type")
            poids = request.POST.get("poids")
            localisation = request.POST.get("localisation", "Position non spécifiée")

            if type_dechet and poids:
                Dechet.objects.create(
                    citoyen=citoyen,
                    type=type_dechet,
                    poids=poids,
                    localisation=localisation,
                    etat="en_attente"
                )
        return redirect(request.path_info)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # --- LOGIQUE COLLECTEUR ---
        if hasattr(user, 'collecteur'):
            collectes = Collecte.objects.filter(collecteur=user.collecteur)
            count_encours = collectes.filter(statut='en_cours').count()
            total = collectes.count()
            context['progression'] = (count_encours / total * 100) if total > 0 else 0
            context['count_encours'] = count_encours
        else:
            context['progression'] = 0
            context['count_encours'] = 0

        # --- LOGIQUE CITOYEN ---
        if hasattr(user, 'citoyen'):
            citoyen = user.citoyen
            mes_dechets = Dechet.objects.filter(citoyen=citoyen)
            poids_total = mes_dechets.aggregate(Sum('poids'))['poids__sum'] or 0

            context['total_declarations'] = mes_dechets.count()
            context['total_poids'] = poids_total
            context['total_dechets'] = mes_dechets.count()
            context['co2_economise'] = round(poids_total * 2.5, 1)
            context['arbres_sauves'] = round(poids_total * 0.015)

            # --- DONNÉES GRAPHIQUES (Corrigées pour MySQL) ---
            # --- DONNÉES POUR LES 3 GRAPHIQUES ---
            if hasattr(user, 'citoyen'):
                mes_dechets = Dechet.objects.filter(citoyen=user.citoyen)

                # 1. Graphique Circulaire (Doughnut) : Répartition par TYPE de déchet
                stats_types = mes_dechets.values('type').annotate(total=Sum('poids'))
                context['chart_labels_types'] = json.dumps([s['type'] for s in stats_types])
                context['chart_values_types'] = json.dumps([float(s['total']) for s in stats_types])

                # 2. Graphique en Courbe (Line) : Évolution du poids par MOIS
                six_months_ago = timezone.now() - timedelta(days=180)
                stats_evo = mes_dechets.filter(date_creation__gte=six_months_ago) \
                    .annotate(month=ExtractMonth('date_creation')) \
                    .values('month').annotate(total=Sum('poids')).order_by('month')
                context['chart_labels_evo'] = json.dumps([f"Mois {s['month']}" for s in stats_evo])
                context['chart_values_evo'] = json.dumps([float(s['total']) for s in stats_evo])

                # 3. Graphique en Barres (Bar) : Nombre de déclarations par ÉTAT
                stats_etat = mes_dechets.values('etat').annotate(count=Count('id'))
                context['chart_labels_etat'] = json.dumps([s['etat'] for s in stats_etat])
                context['chart_values_etat'] = json.dumps([int(s['count']) for s in stats_etat])

            # Utilisation de ExtractMonth pour une compatibilité parfaite avec MySQL
            stats_evo = mes_dechets.filter(date_creation__gte=six_months_ago) \
                .annotate(month=ExtractMonth('date_creation')) \
                .values('month') \
                .annotate(total=Sum('poids')) \
                .order_by('month')

            context['chart_labels_evo'] = json.dumps([s['month'] for s in stats_evo])
            context['chart_values_evo'] = json.dumps([float(s['total']) for s in stats_evo])
        else:
            context.update({
                'total_declarations': 0, 'total_poids': 0, 'total_dechets': 0,
                'co2_economise': 0, 'arbres_sauves': 0,
                'chart_labels_types': '[]', 'chart_values_types': '[]',
                'chart_labels_evo': '[]', 'chart_values_evo': '[]'
            })

        return context

class ProfilCitoyenView(LoginRequiredMixin, TemplateView):
    template_name = "citoyen/profil.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        citoyen = self.request.user.citoyen

        # Calcul dynamique
        dechets = Dechet.objects.filter(citoyen=citoyen)
        total_poids = dechets.aggregate(Sum('poids'))['poids__sum'] or 0

        context['total_poids'] = total_poids
        context['co2_evite'] = round(total_poids * 2.5, 1)
        context['points_verts'] = int(total_poids * 10)  # Exemple : 10 points par kg
        return context


class HistoriqueCitoyenView(LoginRequiredMixin, ListView):
    model = Dechet
    template_name = "citoyen/historique.html"
    context_object_name = "tous_mes_dechets"
    paginate_by = 10  # Nombre de lignes par page

    def get_queryset(self):
        user = self.request.user
        if not hasattr(user, "citoyen"):
            return Dechet.objects.none()

        queryset = Dechet.objects.filter(citoyen=user.citoyen)

        query = self.request.GET.get('q')
        statut = self.request.GET.get('statut')

        if query:
            queryset = queryset.filter(Q(type__icontains=query) | Q(id__icontains=query))
        if statut:
            queryset = queryset.filter(etat=statut)

        return queryset.order_by("-date_creation")

@login_required
def creer_citoyen(request):
    if request.method == "POST":
        quartier = request.POST.get("quartier")
        adresse = request.POST.get("adresse")

        Citoyen.objects.create(
            user=request.user,
            quartier=quartier,
            adresse=adresse
        )

        return redirect("core:dashboard")

    return render(request, "citoyen/creer_citoyen.html")




# =========================================================
# AUTH
# =========================================================
def home(request):
    return render(request, 'home.html') # Remplace 'core/home.html' par le chemin correct de ton fichier


@login_required
def welcome(request):
    # On retire le bloc "if" qui redirige les citoyens
    return render(request, "welcome.html")

# =========================================================
# DASHBOARD collecteur
# =========================================================

# =========================================================
class CollecteurDashboardView(LoginRequiredMixin, ListView):
    model = Collecte
    template_name = "collecteur/dashboard_pro.html"
    context_object_name = "collectes_recentes"

    def get_queryset(self):
        # Récupère uniquement les collectes des 30 derniers jours
        return Collecte.objects.filter(
            collecteur=self.request.user.collecteur,
            date__gte=timezone.now() - timedelta(days=30)
        ).order_by("-date")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Sécurité : Vérifier si l'utilisateur est bien un collecteur avant d'accéder à .collecteur
        if hasattr(self.request.user, 'collecteur'):
            collecteur = self.request.user.collecteur
            collectes = Collecte.objects.filter(collecteur=collecteur)

            # 1. Statistiques globales
            stats = collectes.aggregate(
                total_collectes=Count('id'),
                total_dechets=Sum('dechets__poids')
            )

            # 2. Collectes en attente (Alertes)
            en_attente = collectes.filter(statut='en_attente').count()

            # 3. Statistiques pour la barre de progression
            count_encours = collectes.filter(statut='en_cours').count()
            total_active = collectes.count()
            progression = (count_encours / total_active * 100) if total_active > 0 else 0

            # 4. Analyse des déchets recyclés par mois (pour le graphique)
            data_mensuelle = collectes.filter(statut='termine').annotate(
                mois=ExtractMonth('date')
            ).values('mois').annotate(
                total_poids=Sum('dechets__poids')
            ).order_by('mois')

            # Préparation des données pour le JS (12 mois)
            mois_noms = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc']
            labels_mensuels = [mois_noms[d['mois'] - 1] for d in data_mensuelle]
            values_mensuels = [float(d['total_poids'] or 0) for d in data_mensuelle]

            # Mise à jour du contexte
            context.update({
                'total_collectes': stats['total_collectes'] or 0,
                'total_volume': round(stats['total_dechets'] or 0, 2),
                'alertes_attente': en_attente,
                'count_encours': count_encours,
                'progression': round(progression, 1),
                # Données pour le nouveau graphique
                'labels_mensuels': json.dumps(labels_mensuels),
                'values_mensuels': json.dumps(values_mensuels),
            })
        else:
            # Valeurs par défaut si aucun profil collecteur n'est trouvé
            context.update({
                'total_collectes': 0, 'total_volume': 0, 'alertes_attente': 0,
                'count_encours': 0, 'progression': 0,
                'labels_mensuels': json.dumps([]), 'values_mensuels': json.dumps([])
            })

        return context

    def calculer_progression(self):
        # Exemple : vous pourriez baser cela sur le nombre de collectes
        # terminées vs le total du mois
        return 75