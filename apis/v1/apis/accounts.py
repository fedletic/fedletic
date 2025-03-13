from oauth2_provider.contrib.rest_framework import TokenHasReadWriteScope
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


class AccountsAPI(viewsets.GenericViewSet):

    permission_classes = [IsAuthenticated, TokenHasReadWriteScope]

    @action(detail=False, methods=["get"])
    def me(self, request):
        user = self.request.user
        return Response(
            {
                "id": user.actor.id,
                "name": user.actor.name,
                "webfinger": user.actor.webfinger,
            }
        )
