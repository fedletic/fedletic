from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.db.transaction import atomic
from django.http import HttpRequest, HttpResponseNotFound, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.views import View
from rest_framework import status

from activitypub.methods import (
    create_actor,
    fetch_remote_actor,
    follow_actor,
    unfollow_actor,
    webfinger_lookup,
)
from activitypub.models import Actor
from fedletic.models import FedleticUser
from feeds.models import FeedItem
from frontend.forms import LoginForm, RegisterForm
from workouts.forms import CreateWorkoutForm
from workouts.methods import create_workout
from workouts.models import Workout
from workouts.tasks import process_workout


def handle_register(request):
    form = RegisterForm(data=request.POST)
    if not form.is_valid():
        return form, None
    email = form.cleaned_data["email"]
    password = form.cleaned_data["password"]
    user = FedleticUser.objects.create_user(
        username=email, email=email, password=password
    )
    user.actor = create_actor(
        username=form.cleaned_data["username"],
    )
    user.save()
    return form, user


def handle_login(request):
    form = LoginForm(data=request.POST)
    if not form.is_valid():
        return form, None
    user = authenticate(
        request,
        username=form.cleaned_data["username"],
        password=form.cleaned_data["password"],
    )
    if not user:
        form.add_error(field="username", error="Invalid username or password")
        return form, None
    return form, user


class LandingView(View):

    @atomic
    def post(self, request):
        action = request.POST.get("action")

        if action == "register":
            form, user = handle_register(request=request)
            if not user:
                return self.get(request, register_form=form)
            login(request, user)

        if action == "login":
            form, user = handle_login(request=request)
            if not user:
                return self.get(request, login_form=form)
            login(request, user)

        return redirect(to=reverse("frontend-feed"))

    def get(self, request, login_form=None, register_form=None):

        if request.user.is_authenticated:
            return redirect(to=reverse("frontend-feed"))

        if not register_form:
            register_form = RegisterForm()
        if not login_form:
            login_form = LoginForm()

        return render(
            request,
            "frontend/landing.html",
            {"register_form": register_form, "login_form": login_form},
        )


class FedleticView(View):
    REQUIRES_AUTH = False

    def get_ap(self, request, *args, **kwargs):
        raise NotImplementedError

    def dispatch(self, request: HttpRequest, *args, **kwargs):

        if self.REQUIRES_AUTH and not request.user.is_authenticated:
            return redirect(to=reverse("frontend-landing"))

        # Handle actor extraction first
        actor = None
        if "webfinger" in kwargs:
            webfinger = kwargs["webfinger"]
            if "@" not in webfinger:
                webfinger = f"{webfinger}@{settings.SITE_URL}"
            actor = Actor.objects.get(webfinger=webfinger)

        setattr(request, "actor", actor)

        # Check for ActivityPub content negotiation
        accept_header = request.headers.get("Accept", "")
        if (
            "application/activity+json" in accept_header
            or "application/ld+json" in accept_header
        ):
            response = self.get_ap(request, *args, **kwargs)
            response.headers["Content-Type"] = "application/activity+json"
            return response

        # Otherwise continue with normal view handling
        return super().dispatch(request, *args, **kwargs)


class LoginView(View):

    def post(self, request):
        form = LoginForm(data=request.POST)
        next_page = request.GET.get("next")
        if not form.is_valid():
            return self.get(request, form=form)
        user = authenticate(
            username=form.cleaned_data["username"],
            password=form.cleaned_data["password"],
        )

        if not user:
            form.add_error(field="username", error="Invalid username or password.")
            return self.get(request, form=form)
        login(request, user)

        if next_page:
            return redirect(to=next_page)

        return redirect(to=reverse("frontend-feed"))

    def get(self, request, form=None):
        if not form:
            form = LoginForm()
        return render(request, "frontend/accounts/login.html", {"form": form})


class RegisterView(View):

    def post(self, request):
        form, user = handle_register(request)
        if not user:
            return self.get(request, form)

        login(request, user)
        return redirect(to=reverse("frontend-feed"))

    def get(self, request, form=None):
        if not form:
            form = RegisterForm()
        return render(request, "frontend/accounts/register.html", {"form": form})


class ProfileView(View):

    def post(self, request, webfinger):
        if "@" not in webfinger:
            webfinger = f"{webfinger}@{settings.SITE_URL}"

        action = request.POST.get("action")
        target = Actor.objects.get(webfinger=webfinger)

        if action == "follow":
            follow_actor(actor=request.user.actor, target=target)
        elif action == "unfollow":
            unfollow_actor(actor=request.user.actor, target=target)

        return self.get(request, webfinger)

    def get(self, request, webfinger):
        # TODO: Refactor this to be less chunky, just yeet it into a separate function.
        if "@" in webfinger:
            try:
                actor = Actor.objects.get(webfinger=webfinger)
            except Actor.DoesNotExist:
                from_webfinger = webfinger_lookup(user_id=webfinger)

                if not from_webfinger.get("links"):
                    return HttpResponseNotFound()
                actor_url = None

                for link in from_webfinger["links"]:
                    if link["rel"] == "self":
                        actor_url = link["href"]
                        break

                if not actor_url:
                    return HttpResponseNotFound()

                actor = fetch_remote_actor(actor_url=actor_url)

                if not actor:
                    return HttpResponseNotFound()

        else:

            actor = get_object_or_404(
                Actor, webfinger=f"{webfinger}@{settings.SITE_URL}"
            )

        following = False
        if request.user.is_authenticated:
            following = request.user.actor.following.filter(target=actor).exists()

        return render(
            request,
            "frontend/profile/profile.html",
            {"actor": actor, "following": following},
        )


class LogoutView(FedleticView):
    def get(self, request):
        logout(request)
        return redirect(to=reverse("frontend-landing"))


class FeedView(FedleticView):
    def get(self, request):
        if request.user.is_authenticated:
            feed_items = FeedItem.objects.filter(target=request.user.actor)
        else:
            # TODO: construct public feed.
            feed_items = []
        return render(request, "frontend/feed.html", {"feed_items": feed_items})


class CreateWorkoutView(FedleticView):

    @atomic
    def post(self, request):
        form = CreateWorkoutForm(files=request.FILES, data=request.POST)
        if not form.is_valid():
            return self.get(request, form)

        workout = create_workout(
            actor=request.user.actor,
            fit_file=form.cleaned_data["fit_file"],
            name=form.cleaned_data.get("name"),
        )
        process_workout.delay_on_commit(workout_id=workout.id)

        return redirect(
            reverse(
                "frontend-workout",
                kwargs={
                    "workout_id": workout.ap_id,
                    "webfinger": request.user.actor.domainless_webfinger,
                },
            )
        )

    def get(self, request, form=None):
        if not form:
            form = CreateWorkoutForm()
        return render(
            request,
            "frontend/workouts/create.html",
            {"form": form},
        )


class WorkoutView(FedleticView):

    def get_ap(self, request, *args, **kwargs):
        pass

    def get(self, request, webfinger, workout_id, **kwargs):

        if "@" not in webfinger:
            webfinger = f"{webfinger}@{settings.SITE_URL}"

        workout = Workout.objects.get(ap_id=workout_id, actor__webfinger=webfinger)

        return render(
            request,
            "frontend/workouts/view.html",
            {"workout": workout},
        )


class WorkoutNoteView(FedleticView):
    def get_ap(self, request, webfinger, workout_id, *args, **kwargs):
        if "@" not in webfinger:
            webfinger = f"{webfinger}@{settings.SITE_URL}"
        try:
            workout = Workout.objects.get(ap_id=workout_id, actor__webfinger=webfinger)
        except Workout.DoesNotExist:
            return JsonResponse(
                {"error": "not found"}, status=status.HTTP_404_NOT_FOUND
            )

        activity = workout.note_activities.filter(activity_type="Create").first()
        if not activity:
            return JsonResponse(
                {"error": "not found"}, status=status.HTTP_404_NOT_FOUND
            )
        return JsonResponse(activity.object_json)

    def get(self, request, webfinger, workout_id):
        if "@" not in webfinger:
            webfinger = f"{webfinger}@{settings.SITE_URL}"
        anchor = Workout.objects.get(ap_id=workout_id, actor__webfinger=webfinger)
        return redirect(
            to=reverse(
                "frontend-workout",
                kwargs={"webfinger": webfinger, "workout_id": anchor.ap_id},
            )
        )


class FollowersView(FedleticView):

    def get(self, request, webfinger):
        return render(
            request, "frontend/profile/followers.html", {"actor": request.actor}
        )


class FollowingView(FedleticView):

    def get(self, request, webfinger):
        return render(
            request, "frontend/profile/following.html", {"actor": request.actor}
        )
