from ninja import NinjaAPI

from apis.authentication import OAuth2BearerToken

api_v1 = NinjaAPI(title="Fedletic API", version="1")
auth = OAuth2BearerToken()
