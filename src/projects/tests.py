"""
Tests des permissions de l'API SoftDesk

On vérifie, à travers les vrais endpoints, les trois permissions
définies dans projects/permissions.py :

- IsContributor       -> seuls les contributeurs d'un projet y ont accès
- IsAuthorOrReadOnly  -> seul l'auteur d'une ressource peut la modifier ou la supprimer
- IsProjectAuthor     -> seul l'auteur du projet ajoute ou retire des contributeurs

Ainsi que les deux autres règles annoncées dans le README :
l'authentification JWT obligatoire et l'assignation d'une issue
réservée aux contributeurs du projet.

Lancer les tests (depuis le dossier src/) :
    python manage.py test
"""
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from comments.models import Comment
from issues.models import Issue
from projects.models import Contributor, Project
from projects.permissions import IsContributor


User = get_user_model()

PASSWORD = 'Str0ng-Pass!'


# Hasheur rapide, réservé aux tests : divise le temps d'exécution par ~10
@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class SoftDeskAPITestCase(APITestCase):
    """
    Jeu de données commun à tous les tests

    Trois utilisateurs, trois rôles :
    - author      : a créé le projet, l'issue et le commentaire (auteur ET contributeur)
    - contributor : contributeur du projet, mais auteur de rien
    - outsider    : utilisateur connecté, mais étranger au projet
    """

    @classmethod
    def setUpTestData(cls):
        # setUpTestData est exécuté une seule fois pour toute la classe :
        # Django restaure ces données avant chaque test
        cls.author = cls.create_user('author')
        cls.contributor = cls.create_user('contributor')
        cls.outsider = cls.create_user('outsider')

        cls.project = Project.objects.create(
            title='SoftDesk',
            description='Projet de test',
            type=Project.TYPE_BACKEND,
            author=cls.author,
        )
        cls.author_link = Contributor.objects.create(project=cls.project, user=cls.author)
        cls.contributor_link = Contributor.objects.create(project=cls.project, user=cls.contributor)

        cls.issue = Issue.objects.create(
            title='Bug de connexion',
            description='Impossible de se connecter',
            priority=Issue.PRIORITY_HIGH,
            tag=Issue.TAG_BUG,
            project=cls.project,
            author=cls.author,
        )
        cls.comment = Comment.objects.create(
            description='Je regarde ça',
            issue=cls.issue,
            author=cls.author,
        )

    @staticmethod
    def create_user(username):
        return User.objects.create_user(username=username, password=PASSWORD, age=30)

    def login(self, user):
        """ Authentifie le client de test sans passer par le JWT """
        self.client.force_authenticate(user=user)

    # --- URLs, construites à partir des basename déclarés dans les routers ---

    def projects_url(self):
        return reverse('projects-list')

    def project_url(self, project=None):
        return reverse('projects-detail', kwargs={'pk': (project or self.project).pk})

    def contributors_url(self):
        return reverse('contributors-list', kwargs={'project_pk': self.project.pk})

    def contributor_url(self, link):
        return reverse('contributors-detail', kwargs={'project_pk': self.project.pk, 'pk': link.pk})

    def issues_url(self, project=None):
        return reverse('issues-list', kwargs={'project_pk': (project or self.project).pk})

    def issue_url(self, issue=None, project=None):
        return reverse('issues-detail', kwargs={
            'project_pk': (project or self.project).pk,
            'pk': (issue or self.issue).pk,
        })

    def comments_url(self):
        return reverse('comments-list', kwargs={'project_pk': self.project.pk, 'issue_pk': self.issue.pk})

    def comment_url(self):
        return reverse('comments-detail', kwargs={
            'project_pk': self.project.pk,
            'issue_pk': self.issue.pk,
            'pk': self.comment.pk,
        })

    def readable_urls(self):
        """ Toutes les routes de lecture d'un projet """
        return {
            'projet': self.project_url(),
            'contributeurs': self.contributors_url(),
            'issues': self.issues_url(),
            'issue': self.issue_url(),
            'commentaires': self.comments_url(),
            'commentaire': self.comment_url(),
        }

    def editable_resources(self):
        """ Les trois ressources protégées par IsAuthorOrReadOnly : (nom, url, données PATCH) """
        return [
            ('projet', self.project_url(), {'title': 'Nouveau titre'}),
            ('issue', self.issue_url(), {'title': 'Nouveau titre'}),
            ('commentaire', self.comment_url(), {'description': 'Nouveau texte'}),
        ]

    def new_issue_data(self, **extra):
        return {
            'title': 'Nouvelle issue',
            'description': 'Description',
            'priority': Issue.PRIORITY_LOW,
            'tag': Issue.TAG_TASK,
            **extra,
        }


class AuthenticationTests(SoftDeskAPITestCase):
    """ JWT obligatoire : un visiteur anonyme n'accède à rien """

    def test_anonymous_user_gets_401_everywhere(self):
        urls = {'liste des projets': self.projects_url(), **self.readable_urls()}

        for name, url in urls.items():
            with self.subTest(route=name):
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_anonymous_user_cannot_create_project(self):
        response = self.client.post(self.projects_url(), {
            'title': 'Pirate', 'description': '...', 'type': Project.TYPE_IOS,
        })

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Project.objects.count(), 1)

    def test_valid_jwt_gives_access(self):
        token_response = self.client.post(
            reverse('obtain_token_access'),
            {'username': 'contributor', 'password': PASSWORD},
        )
        self.assertEqual(token_response.status_code, status.HTTP_200_OK)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_response.data['access']}")
        response = self.client.get(self.projects_url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_jwt_is_rejected(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer faux.jeton.jwt')

        response = self.client.get(self.projects_url())

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class IsContributorTests(SoftDeskAPITestCase):
    """ Permission IsContributor : un projet n'est visible que par ses contributeurs """

    def test_project_creator_automatically_becomes_contributor(self):
        self.login(self.outsider)

        response = self.client.post(self.projects_url(), {
            'title': 'Mon projet', 'description': '...', 'type': Project.TYPE_ANDROID,
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['is_author'])
        self.assertTrue(
            Contributor.objects.filter(project_id=response.data['id'], user=self.outsider).exists()
        )

    def test_project_list_only_shows_projects_of_the_user(self):
        self.login(self.outsider)
        response = self.client.get(self.projects_url())
        self.assertEqual(response.data['count'], 0)

        self.login(self.contributor)
        response = self.client.get(self.projects_url())
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.project.id)

    def test_outsider_cannot_read_project_resources(self):
        self.login(self.outsider)

        for name, url in self.readable_urls().items():
            with self.subTest(route=name):
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_outsider_cannot_create_issue_or_comment(self):
        self.login(self.outsider)

        response = self.client.post(self.issues_url(), self.new_issue_data())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.post(self.comments_url(), {'description': 'Intrusion'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(Issue.objects.count(), 1)
        self.assertEqual(Comment.objects.count(), 1)

    def test_contributor_can_read_project_resources(self):
        self.login(self.contributor)

        for name, url in self.readable_urls().items():
            with self.subTest(route=name):
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_contributor_can_create_issue_and_comment(self):
        self.login(self.contributor)

        response = self.client.post(self.issues_url(), self.new_issue_data())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['author'], self.contributor.id)

        response = self.client.post(self.comments_url(), {'description': 'Bien vu'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['author'], self.contributor.id)

    def test_outsider_gets_access_once_added_as_contributor(self):
        self.login(self.outsider)
        self.assertEqual(self.client.get(self.project_url()).status_code, status.HTTP_403_FORBIDDEN)

        Contributor.objects.create(project=self.project, user=self.outsider)

        self.assertEqual(self.client.get(self.project_url()).status_code, status.HTTP_200_OK)

    def test_cannot_reach_another_project_issue_through_own_project_url(self):
        """
        Le contributeur passe le contrôle IsContributor sur SON projet,
        mais l'issue d'un autre projet ne doit pas être atteignable via cette URL
        """
        other_project = Project.objects.create(
            title='Secret', description='...', type=Project.TYPE_IOS, author=self.outsider,
        )
        other_issue = Issue.objects.create(
            title='Confidentiel', description='...', priority=Issue.PRIORITY_LOW,
            tag=Issue.TAG_TASK, project=other_project, author=self.outsider,
        )
        self.login(self.contributor)

        response = self.client.get(self.issue_url(issue=other_issue, project=self.project))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_object_permission_finds_the_project_of_each_resource(self):
        """
        Test unitaire de IsContributor.has_object_permission

        Via l'API, has_permission bloque déjà l'accès grâce à l'id du projet dans l'URL :
        ce second contrôle n'est jamais décisif. On l'appelle donc directement,
        pour vérifier qu'il retrouve bien le projet d'un Project, d'une Issue
        et d'un Comment (via comment.issue.project)
        """
        permission = IsContributor()
        request = APIRequestFactory().get('/')

        for obj in (self.project, self.issue, self.comment):
            with self.subTest(objet=type(obj).__name__):
                request.user = self.contributor
                self.assertTrue(permission.has_object_permission(request, None, obj))

                request.user = self.outsider
                self.assertFalse(permission.has_object_permission(request, None, obj))


class IsAuthorOrReadOnlyTests(SoftDeskAPITestCase):
    """ Permission IsAuthorOrReadOnly : lecture pour tous les contributeurs, écriture pour l'auteur """

    def test_contributor_cannot_update_resources_of_others(self):
        self.login(self.contributor)

        for name, url, data in self.editable_resources():
            with self.subTest(ressource=name):
                response = self.client.patch(url, data)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.project.refresh_from_db()
        self.assertEqual(self.project.title, 'SoftDesk')

    def test_contributor_cannot_delete_resources_of_others(self):
        self.login(self.contributor)

        for name, url, _ in self.editable_resources():
            with self.subTest(ressource=name):
                response = self.client.delete(url)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertTrue(Project.objects.filter(pk=self.project.pk).exists())
        self.assertTrue(Issue.objects.filter(pk=self.issue.pk).exists())
        self.assertTrue(Comment.objects.filter(pk=self.comment.pk).exists())

    def test_author_can_update_own_resources(self):
        self.login(self.author)

        for name, url, data in self.editable_resources():
            with self.subTest(ressource=name):
                response = self.client.patch(url, data)
                self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.project.refresh_from_db()
        self.comment.refresh_from_db()
        self.assertEqual(self.project.title, 'Nouveau titre')
        self.assertEqual(self.comment.description, 'Nouveau texte')

    def test_author_can_delete_own_resources(self):
        self.login(self.author)

        # Du plus petit au plus grand : supprimer le projet supprimerait tout en cascade
        for name, url, _ in reversed(self.editable_resources()):
            with self.subTest(ressource=name):
                response = self.client.delete(url)
                self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertFalse(Project.objects.filter(pk=self.project.pk).exists())

    def test_contributor_can_update_own_issue(self):
        """ L'auteur, c'est l'auteur de la ressource, pas celui du projet """
        issue = Issue.objects.create(
            title='Mon issue', description='...', priority=Issue.PRIORITY_LOW,
            tag=Issue.TAG_TASK, project=self.project, author=self.contributor,
        )
        self.login(self.contributor)

        response = self.client.patch(self.issue_url(issue=issue), {'status': Issue.STATUS_FINISHED})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], Issue.STATUS_FINISHED)

    def test_project_author_cannot_edit_comment_of_contributor(self):
        comment = Comment.objects.create(description='À moi', issue=self.issue, author=self.contributor)
        url = reverse('comments-detail', kwargs={
            'project_pk': self.project.pk, 'issue_pk': self.issue.pk, 'pk': comment.pk,
        })
        self.login(self.author)

        response = self.client.patch(url, {'description': 'Modifié par le chef'})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class IsProjectAuthorTests(SoftDeskAPITestCase):
    """ Permission IsProjectAuthor : seul l'auteur du projet gère les contributeurs """

    def test_author_can_add_contributor(self):
        self.login(self.author)

        response = self.client.post(self.contributors_url(), {'user_id': self.outsider.id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Contributor.objects.filter(project=self.project, user=self.outsider).exists())

    def test_contributor_cannot_add_contributor(self):
        self.login(self.contributor)

        response = self.client.post(self.contributors_url(), {'user_id': self.outsider.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Contributor.objects.filter(project=self.project, user=self.outsider).exists())

    def test_outsider_cannot_add_himself_to_project(self):
        self.login(self.outsider)

        response = self.client.post(self.contributors_url(), {'user_id': self.outsider.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Contributor.objects.filter(project=self.project, user=self.outsider).exists())

    def test_author_can_remove_contributor(self):
        self.login(self.author)

        response = self.client.delete(self.contributor_url(self.contributor_link))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Contributor.objects.filter(pk=self.contributor_link.pk).exists())

    def test_contributor_cannot_remove_contributor(self):
        self.login(self.contributor)

        response = self.client.delete(self.contributor_url(self.author_link))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Contributor.objects.filter(pk=self.author_link.pk).exists())

    def test_author_cannot_be_removed_from_contributors(self):
        self.login(self.author)

        response = self.client.delete(self.contributor_url(self.author_link))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Contributor.objects.filter(pk=self.author_link.pk).exists())

    def test_same_user_cannot_be_added_twice(self):
        self.login(self.author)

        response = self.client.post(self.contributors_url(), {'user_id': self.contributor.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Contributor.objects.filter(project=self.project, user=self.contributor).count(), 1)


class IssueAssigneeTests(SoftDeskAPITestCase):
    """ Règle métier : une issue ne peut être assignée qu'à un contributeur du projet """

    def test_issue_can_be_assigned_to_contributor(self):
        self.login(self.author)

        response = self.client.post(self.issues_url(), self.new_issue_data(assignee_id=self.contributor.id))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['assignee'], self.contributor.id)

    def test_issue_cannot_be_assigned_to_outsider(self):
        self.login(self.author)

        response = self.client.post(self.issues_url(), self.new_issue_data(assignee_id=self.outsider.id))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('assignee_id', response.data)

    def test_existing_issue_cannot_be_reassigned_to_outsider(self):
        self.login(self.author)

        response = self.client.patch(self.issue_url(), {'assignee_id': self.outsider.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.issue.refresh_from_db()
        self.assertIsNone(self.issue.assignee)
