from oauth2_provider.contrib.rest_framework import TokenHasReadWriteScope
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


class WorkoutsAPI(viewsets.GenericViewSet):

    permission_classes = [IsAuthenticated, TokenHasReadWriteScope]

    def create(self, request, *args, **kwargs):
        return Response({"foo": 1})
