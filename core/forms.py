from django import forms
from .models import Collecte, Collecteur
from .models import Citoyen

class CitoyenForm(forms.ModelForm):
    class Meta:
        model = Citoyen
        fields = ['adresse', 'quartier', 'code_postal', 'preference_collecte']
        widgets = {
            'adresse': forms.TextInput(attrs={'class': 'form-input'}),
            'quartier': forms.TextInput(attrs={'class': 'form-input'}),
            'code_postal': forms.TextInput(attrs={'class': 'form-input'}),
            'preference_collecte': forms.Select(choices=[('hebdo', 'Hebdomadaire'), ('mensuel', 'Mensuel')], attrs={'class': 'form-select'}),
        }

class CollecteForm(forms.ModelForm):
    # Champ de sélection pour les catégories générales
    TYPE_DECHET_CHOICES = [
        ('', '--- Sélectionner un type ---'),
        ('menager', 'Déchets Ménagers'),
        ('plastique', 'Déchets Plastiques'),
        ('industriel', 'Déchets Industriels'),
    ]

    type_principal = forms.ChoiceField(
        choices=TYPE_DECHET_CHOICES,
        label="Catégorie de Déchet",
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    # SAISIE LIBRE : Ce champ remplace désormais la liste de cases à cocher
    observations_dechets = forms.CharField(
        label="Déchets spécifiques",
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Saisissez ici la liste des déchets spécifiques (ex: 3 pneus, gravats, bouteilles...)'
        })
    )

    class Meta:
        model = Collecte
        # 'dechets' est retiré de la liste ci-dessous
        fields = [
            'date',
            'type_principal',
            'statut',
            'itineraire',
            'collecteur',
            'observations_dechets'
        ]

        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'statut': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: En attente'}),

            'itineraire': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Détails du lieu ou de l\'itinéraire...'
            }),

            'collecteur': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super(CollecteForm, self).__init__(*args, **kwargs)
        # On garde uniquement le chargement des collecteurs
        self.fields['collecteur'].queryset = Collecteur.objects.all()

        # Labels finaux
        self.fields['itineraire'].label = "Zone de saisie libre (Détails)"