# --- IMPORTS CORRIGÉS ---
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.contrib import messages
from django.contrib.auth import login, authenticate, get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum,Count
from django.urls import reverse_lazy
import json
from django.db.models.functions import ExtractMonth
from datetime import datetime
from django.views import View
from django.views.generic import UpdateView, ListView, CreateView, TemplateView
from django.shortcuts import redirect, render, get_object_or_404

from django.utils import timezone  # Assurez-vous d'avoir cet import

# IMPORT CRUCIAL : Importe tes modèles depuis core.models
from core.models import Dechet, Collecte, Citoyen, Collecteur

User = get_user_model()
# ------------------------

from django.db import IntegrityError  # Importe ceci en haut

def register_collecteur_view(request):
    if request.method == 'POST':
        # 1. Récupération sécurisée
        # Dans collecteur/views.py
        username = request.POST.get('username')
        print(f"DEBUG - Nom d'utilisateur reçu : {username}")  # Ajoutez ce print pour voir ce qui arrive vraiment
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password2')
        role = request.POST.get('role', 'citoyen')

        # Optionnel : si tu veux forcer une valeur valide
        if role not in ['citoyen', 'collecteur', 'centre_de_tri']:
            role = 'citoyen'  # Valeur de repli sécurisée

        # 2. Validation des mots de passe
        if password != password_confirm:
            messages.error(request, "Les mots de passe ne correspondent pas.")
            return render(request, 'register.html')

        # 3. Vérification si utilisateur existe déjà
        if User.objects.filter(username=username).exists():
            messages.error(request, "Ce nom d'utilisateur est déjà pris.")
            return render(request, 'register.html')
        try:
            with transaction.atomic():
                if role == "citoyen":
                    user = User.objects.create_user(username=username, email=email, password=password, role='citoyen')
                    Citoyen.objects.create(user=user)
                # ... à l'intérieur de la vue register_collecteur_view ...
                elif role == "collecteur":
                    # 1. On crée d'abord l'utilisateur standard
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=password,
                        role='collecteur'
                    )
                    # 2. Ensuite on crée le profil Collecteur lié
                    Collecteur.objects.create(
                        user=user,
                        zone_couverture="Non renseigné",
                        vehicule="Non renseigné"
                    )


            # MAINTENANT, la variable 'user' existe toujours ici !
            login(request, user)
            return redirect('collecteur:login')

        except IntegrityError:
            messages.error(request, "Ce nom d'utilisateur est déjà pris.")
            return render(request, 'register.html')


    # Si GET, on affiche simplement le formulaire
    return render(request, 'register.html')
# =========================================================
# DASHBOARD collecteur
class CollecteurDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if hasattr(self.request.user, 'collecteur'):
            collecteur = self.request.user.collecteur
            collectes = Collecte.objects.filter(collecteur=collecteur)

            # 1. Statistiques KPI
            total_volume = collectes.aggregate(total=Sum('dechets__poids'))['total'] or 0
            alertes_attente = collectes.filter(statut='en_attente').count()

            # 2. Données dynamiques : Types de déchets
            # Note: remplacez 'dechets__type' par le nom réel du champ dans votre modèle
            stats_types = collectes.values('dechets__type').annotate(total=Sum('dechets__poids'))
            labels_types = [str(s['dechets__type'] or 'Autre') for s in stats_types]
            values_types = [float(s['total'] or 0) for s in stats_types]

            # 3. Données dynamiques : Évolution (les 6 derniers mois)
            six_months_ago = timezone.now() - timezone.timedelta(days=180)
            stats_evo = collectes.filter(date__gte=six_months_ago) \
                .annotate(month=ExtractMonth('date')) \
                .values('month').annotate(total=Sum('dechets__poids')).order_by('month')

            # Conversion des numéros de mois en noms (ex: 1 -> Jan)
            labels_evo = [datetime(2000, s['month'], 1).strftime('%b') for s in stats_evo]
            values_evo = [float(s['total'] or 0) for s in stats_evo]

            # 4. Données dynamiques : Statuts
            stats_statuts = collectes.values('statut').annotate(count=Count('id'))
            labels_statuts = [str(s['statut']) for s in stats_statuts]
            values_statuts = [int(s['count']) for s in stats_statuts]

            # Injection dans le contexte
            context.update({
                'collectes_recentes': collectes.order_by("-date")[:10],
                'total_volume': round(total_volume, 2),
                'alertes_attente': alertes_attente,
                'chart_labels_types': json.dumps(labels_types),
                'chart_values_types': json.dumps(values_types),
                'chart_labels_evo': json.dumps(labels_evo),
                'chart_values_evo': json.dumps(values_evo),
                'chart_labels_statuts': json.dumps(labels_statuts),
                'chart_values_statuts': json.dumps(values_statuts),
            })
        else:
            # Valeurs par défaut pour les utilisateurs sans profil collecteur
            context.update({
                'collectes_recentes': [],
                'total_volume': 0,
                'alertes_attente': 0,
                'chart_labels_types': json.dumps([]),
                'chart_values_types': json.dumps([]),
                'chart_labels_evo': json.dumps([]),
                'chart_values_evo': json.dumps([]),
                'chart_labels_statuts': json.dumps([]),
                'chart_values_statuts': json.dumps([]),
            })

        return context


class GérerCollecteView(LoginRequiredMixin, View):
    def get(self, request, pk):
        collecte = get_object_or_404(Collecte, pk=pk, collecteur=request.user.collecteur)
        dechets_disponibles = Dechet.objects.filter(etat='en_attente')

        context = {
            'collecte': collecte,
            'dechets_disponibles': dechets_disponibles,
            'alertes_attente': dechets_disponibles.count(),
            # Utilisez directement Sum et Count sans le préfixe 'models.'
            'stats': dechets_disponibles.aggregate(
                total_kg=Sum('poids'),
                count=Count('id')
            )
        }
        return render(request, 'gerer_collecte.html', context)

    def form_valid(self, form):
        # 1. Sauvegarde l'objet pour avoir accès aux relations M2M
        collecte = form.save(commit=False)
        collecte.save()
        form.save_m2m()  # Maintenant les déchets sont liés à la collecte

        # 2. Calcul du poids avec les objets réellement liés
        total_poids = collecte.dechets.aggregate(total=Sum('poids'))['total'] or 0

        # 3. Validation métier
        if total_poids > 500:
            messages.error(self.request, f"Le poids total ({total_poids}kg) dépasse la capacité (500kg).")
            # On peut supprimer l'objet si on veut annuler complètement, ou juste renvoyer l'erreur
            return self.form_invalid(form)

        # 4. Mise à jour en cascade des statuts
        collecte.dechets.update(etat='collecte')
        messages.success(self.request, "Collecte validée avec succès.")

        return super().form_valid(form)

class AjouterCollecteView(LoginRequiredMixin, CreateView):
        model = Collecte
        template_name = "ajouter_collecte.html"
        fields = ['date', 'type_principal', 'itineraire', 'collecteur']
        success_url = reverse_lazy('collecteur:dashboard')

        def form_valid(self, form):
            return super().form_valid(form)




@login_required
def selectionner_declarations(request):
    # Protection : Vérifier si l'utilisateur est bien un collecteur
    if not hasattr(request.user, 'collecteur'):
        messages.error(request, "Accès refusé.")
        return redirect('core:welcome')

    dechets_en_attente = Dechet.objects.filter(etat='en_attente')

    if request.method == "POST":
        selected_ids = request.POST.getlist('dechets')

        if not selected_ids:
            messages.error(request, "Veuillez sélectionner des déchets.")
            return render(request, 'selection_dechets.html', {'dechets': dechets_en_attente})

        try:
            # Création avec les champs obligatoires (ajustez selon votre modèle Collecte)
            nouvelle_collecte = Collecte.objects.create(
                collecteur=request.user.collecteur,
                statut='en_cours',
                date=timezone.now(),  # Très souvent obligatoire dans les modèles
                # Ajoutez ici tout autre champ obligatoire de votre modèle Collecte
            )

            # Lier les déchets
            dechets = Dechet.objects.filter(id__in=selected_ids)
            nouvelle_collecte.dechets.set(dechets)
            dechets.update(etat='en_cours')

            # Redirection avec le bon paramètre 'id'
            return redirect('collecteur:finaliser_collecte', id=nouvelle_collecte.id)

        except Exception as e:
            print(f"ERREUR : {e}")
            messages.error(request, f"Erreur lors de la création : {e}")
            return render(request, 'selection_dechets.html', {'dechets': dechets_en_attente})

    return render(request, 'selection_dechets.html', {'dechets': dechets_en_attente})


# Remplacez 'ids' par 'id' (le nom dans l'URL doit correspondre)
def finaliser_collecte(request, id):
    # Récupérez la collecte existante au lieu d'en recréer une
    nouvelle_collecte = get_object_or_404(Collecte, id=id)
    dechets = nouvelle_collecte.dechets.all()

    if request.method == "POST":
        statut_choisi = request.POST.get('statut')

        # Mise à jour de la collecte existante
        nouvelle_collecte.statut = statut_choisi
        nouvelle_collecte.save()

        dechets.update(etat=statut_choisi)
        messages.success(request, "Collecte finalisée !")
        return redirect('collecteur:dashboard')  # Vérifiez le nom de votre URL ici

    return render(request, 'finaliser_collecte.html', {
        'collecte': nouvelle_collecte,
        'dechets': dechets
    })


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)

                # --- LOGIQUE DE REDIRECTION PAR RÔLE ---
                # On vérifie si l'utilisateur possède un profil collecteur
                if hasattr(user, 'collecteur'):
                    return redirect('collecteur:dashboard')

                # On vérifie si l'utilisateur possède un profil citoyen
                elif hasattr(user, 'citoyen'):
                    return redirect('core:dashboard')

                # Cas par défaut si aucun rôle n'est détecté
                else:
                    return redirect('core:welcome')
            else:
                messages.error(request, "Ce compte est désactivé.")
        else:
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")

    return render(request, 'login.html')


def collection_liste(request):
    # Utilisez 'en_attente' (minuscule) pour correspondre à votre modèle
    collectes = Collecte.objects.filter(statut='en_attente')
    return render(request, 'collection_liste.html', {'collectes': collectes})