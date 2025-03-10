import logging

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from activitypub.crypto import verify_http_signature

log = logging.getLogger()


@method_decorator(csrf_exempt, name="dispatch")
class ActivityPubBaseView(View):
    CONTENT_TYPE = "application/activity+json"

    def dispatch(self, request, *args, **kwargs):

        if request.method in ["POST", "DELETE", "PUT", "PATCH"]:
            is_valid, message = verify_http_signature(request)
            if not is_valid:
                log.warning("Invalid request %s", message)
                return JsonResponse({"error": message}, status=403)

        response = super().dispatch(request, *args, **kwargs)
        response.headers["Content-Type"] = self.CONTENT_TYPE

        return response
