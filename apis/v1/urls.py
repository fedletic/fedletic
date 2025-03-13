from rest_framework.routers import DefaultRouter

from apis.v1.apis.accounts import AccountsAPI
from apis.v1.apis.apps import AppsAPI
from apis.v1.apis.workouts import WorkoutsAPI

router = DefaultRouter()
router.register(r"apps", AppsAPI, basename="app")
router.register(r"accounts", AccountsAPI, basename="account")
router.register(r"workouts", WorkoutsAPI, basename="workouts")

# URL patterns to include in your urls.py
urlpatterns = router.urls
