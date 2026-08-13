from rest_framework.routers import DefaultRouter

from apps.social.views import (
    ConversationViewSet,
    ForumPostViewSet,
    ForumThreadViewSet,
    LearningGroupViewSet,
    MentorshipRelationViewSet,
)

router = DefaultRouter()
router.register('forum-threads', ForumThreadViewSet, basename='forum-thread')
router.register('forum-posts', ForumPostViewSet, basename='forum-post')
router.register('groups', LearningGroupViewSet, basename='learning-group')
router.register('mentorships', MentorshipRelationViewSet, basename='mentorship')
router.register('conversations', ConversationViewSet, basename='conversation')

urlpatterns = router.urls
