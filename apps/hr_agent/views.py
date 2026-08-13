from rest_framework import permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.constants import Roles
from apps.core.mixins import CompanyScopedViewSetMixin
from apps.core.permissions import HasRole
from apps.hr_agent.models import AgentConversation, AgentMessage, AgentResource
from apps.hr_agent.serializers import (
    AgentConversationSerializer,
    AgentMessageSerializer,
    AgentResourceSerializer,
    ChatRequestSerializer,
    JobDescriptionRequestSerializer,
    JobDescriptionResultSerializer,
)
from apps.hr_agent.services import detect_intent, find_resources, generate_job_description

IsHRorAdmin = HasRole.for_roles(Roles.HR, Roles.COMPANY_ADMIN, Roles.TRAINING_CENTER_ADMIN)

_INTENT_REPLIES = {
    'internal_rules': "Voici le règlement intérieur de l'entreprise, disponible en texte, en PDF téléchargeable et en vidéo.",
    'onboarding': "Voici les contenus d'intégration prévus pour votre département — n'hésitez pas à les consulter pour bien démarrer.",
    'job_description': (
        "Je peux générer votre fiche de poste. Merci de renseigner votre nom complet, votre intitulé de poste, "
        "votre département et, si possible, votre responsable et votre date de prise de poste."
    ),
}


class AgentResourceViewSet(CompanyScopedViewSetMixin, viewsets.ModelViewSet):
    """CRUD des contenus de l'agent IA RH — réservé aux RH/Admins (gestion depuis l'admin/RH)."""

    queryset = AgentResource.objects.select_related('department', 'service', 'company').all()
    serializer_class = AgentResourceSerializer
    permission_classes = [IsHRorAdmin]
    filterset_fields = ['category', 'content_type', 'department', 'service', 'is_active']

    def perform_create(self, serializer):
        # A super admin authors content while "viewing" a specific company (top-nav
        # switcher) — request.user.company is *their own* account's company, which is
        # usually a different one, so forcing it here silently created every resource
        # under the wrong tenant and it never showed up for that company's employees.
        user = self.request.user
        company = user.company
        if user.is_superuser or user.role == Roles.SUPER_ADMIN:
            requested_company = serializer.validated_data.get('company')
            if requested_company:
                company = requested_company
        serializer.save(company=company, created_by=user)

    def perform_update(self, serializer):
        # Same reasoning as perform_create — only a super admin may repoint a
        # resource at a different company; everyone else keeps it where it is.
        user = self.request.user
        if user.is_superuser or user.role == Roles.SUPER_ADMIN:
            serializer.save()
        else:
            serializer.save(company=serializer.instance.company)


class AgentChatView(APIView):
    """POST /api/hr-agent/chat/ — envoie un message à l'agent IA RH et reçoit une réponse
    (texte + éventuels contenus attachés : PDF téléchargeable, vidéo, ou déclenchement du
    formulaire de génération de fiche de poste)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        conversation, _ = AgentConversation.objects.get_or_create(user=request.user)
        return Response(AgentConversationSerializer(conversation, context={'request': request}).data)

    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message_text = serializer.validated_data['message']

        conversation, _ = AgentConversation.objects.get_or_create(user=request.user)
        AgentMessage.objects.create(conversation=conversation, role=AgentMessage.ROLE_USER, content=message_text)

        intent = detect_intent(message_text)
        category_map = {
            'internal_rules': AgentResource.CATEGORY_INTERNAL_RULES,
            'onboarding': AgentResource.CATEGORY_ONBOARDING,
        }
        resources = []
        if intent != 'job_description':
            resources = find_resources(request.user, message_text, category=category_map.get(intent))

        if intent in _INTENT_REPLIES:
            reply_text = _INTENT_REPLIES[intent]
        elif resources:
            reply_text = f"J'ai trouvé {len(resources)} contenu(s) qui pourraient vous aider :"
        else:
            reply_text = (
                "Je n'ai pas trouvé de contenu correspondant précisément à votre question. "
                "Vous pouvez me demander le règlement intérieur, les contenus d'intégration de votre "
                "département, ou votre fiche de poste."
            )

        agent_message = AgentMessage.objects.create(
            conversation=conversation, role=AgentMessage.ROLE_AGENT, content=reply_text, intent=intent,
        )
        if resources:
            agent_message.resources.set(resources)

        conversation.save(update_fields=['updated_at'])
        return Response(AgentMessageSerializer(agent_message, context={'request': request}).data)


class AgentResourcesMenuView(APIView):
    """GET /api/hr-agent/resources/menu/ — contenus disponibles pour l'employé, groupés par catégorie
    (alimente les boutons de suggestion rapide de l'agent)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.hr_agent.services import find_resources as _find

        result = {}
        for key, _label in AgentResource.CATEGORY_CHOICES:
            result[key] = AgentResourceSerializer(
                _find(request.user, '', category=key), many=True, context={'request': request}
            ).data
        return Response(result)


class JobDescriptionGenerateView(APIView):
    """POST /api/hr-agent/job-description/ — génère la fiche de poste PDF de l'employé à partir
    des informations qu'il renseigne (nom, poste, département, responsable, date, missions)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = JobDescriptionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job_request = generate_job_description(request.user, **serializer.validated_data)
        return Response(JobDescriptionResultSerializer(job_request, context={'request': request}).data, status=201)
