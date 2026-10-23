from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError

from .models import Project, Contributor
from .serializers import ProjectSerializer, ContributorSerializer
from .permissions import IsContributor, IsAuthorOrReadOnly, IsProjectAuthor


class ProjectViewSet(viewsets.ModelViewSet):

    """
    ViewSet complet pour les projets

    ModelViewSet fournit automatiquement :
    - list
    - create
    - retrieve
    - update
    - partial_update
    - destroy
    """

    serializer_class = ProjectSerializer

    # L'utilisateur doit :
    # - être authentifié
    # - être contributeur du projet
    # - être auteur pour modifier/supprimer
    permission_classes = [IsAuthenticated, IsContributor, IsAuthorOrReadOnly]

    def get_queryset(self):
        """
        Retourne uniquement les projets où l'utilisateur connecté est contributeur
        Cela empêche un utilisateur de voir les projets des autres
        """
        # order_by : la pagination a besoin d'un ordre stable
        return Project.objects.filter(contributors__user=self.request.user).distinct().order_by('id')

    def perform_create(self, serializer):
        """
        Personnalise la création d'un projet
        1. Crée le projet avec request.user comme auteur
        2. Crée automatiquement une ligne Contributor pour que le créateur soit aussi contributeur
        """
        project = serializer.save(author=self.request.user)
        Contributor.objects.get_or_create(project=project, user=self.request.user)


class ContributorViewSet(mixins.ListModelMixin,
                         mixins.CreateModelMixin,
                         mixins.DestroyModelMixin,
                         viewsets.GenericViewSet):
    """
    ViewSet limité pour les contributeurs

    On autorise seulement :
    - list : voir les contributeurs d'un projet
    - create : ajouter un contributeur
    - destroy : supprimer un contributeur

    On n'utilise pas ModelViewSet car on ne veut pas exposer update/partial_update/retrieve inutilement
    """
    serializer_class = ContributorSerializer

    def get_queryset(self):
        """
        Retourne uniquement les contributeurs du projet ciblé dans l'URL
        """
        project_id = self.kwargs['project_pk']
        return Contributor.objects.filter(project_id=project_id).order_by('id')

    def perform_create(self, serializer):
        """
        Ajoute un contributeur au projet ciblé par l'URL

        Le body contient seulement user_id
        Le project_id vient de l'URL : /projects/{project_pk}/contributors/
        """
        project_id = self.kwargs['project_pk']
        user = serializer.validated_data['user']

        # Évite d'ajouter deux fois le même utilisateur au même projet
        if Contributor.objects.filter(project_id=project_id, user=user).exists():
            raise ValidationError("Cet utilisateur est déjà contributeur de ce projet.")

        serializer.save(project_id=project_id)

    def perform_destroy(self, instance):
        """
        Supprime un contributeur

        Sécurité : l'auteur du projet ne peut pas être retiré des contributeurs.
        """
        if instance.project.author_id == instance.user_id:
            raise ValidationError("Impossible de supprimer l'auteur des contributeurs.")

        instance.delete()

    def get_permissions(self):
        """
        Définit des permissions différentes selon l'action demandée
        """
        # Voir les contributeurs : autorisé aux utilisateurs connectés qui sont contributeurs du projet
        if self.action == 'list':
            return [IsAuthenticated(), IsContributor()]

        # Ajouter ou supprimer un contributeur -> réservé à l'auteur du projet uniquement
        if self.action in ['create', 'destroy']:
            return [IsAuthenticated(), IsProjectAuthor()]

        return [IsAuthenticated()]