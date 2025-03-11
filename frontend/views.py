from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.db.transaction import atomic
from django.http import HttpRequest, HttpResponseNotFound, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.views import View

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
from workouts.models import WorkoutAnchor
from workouts.tasks import process_workout


class LandingView(View):

    @atomic
    def post(self, request):
        action = request.POST.get("action")

        if action == "register":
            form = RegisterForm(data=request.POST)
            if not form.is_valid():
                return self.get(request, register_form=form)
            username = form.cleaned_data["username"]
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            user = FedleticUser.objects.create_user(
                username=username, email=email, password=password
            )
            user.actor = create_actor(
                username=form.cleaned_data["username"],
            )
            user.save()

            login(request, user)

        if action == "login":
            form = LoginForm(data=request.POST)
            if not form.is_valid():
                return self.get(request, login_form=form)
            user = authenticate(
                request,
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
            )
            if not user:
                form.add_error(field="username", error="Invalid username or password")
                return self.get(request, login_form=form)
            login(request, user)

        return redirect(to=reverse("frontend-feed"))

    def get(self, request, login_form=None, register_form=None):
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
    def get_ap(self, request, *args, **kwargs):
        raise NotImplementedError

    def dispatch(self, request: HttpRequest, *args, **kwargs):
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
        feed_items = FeedItem.objects.filter(target=request.user.actor)
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
            summary=form.cleaned_data.get("summary"),
        )
        process_workout.delay_on_commit(anchor_id=workout.anchor.id)

        return redirect(
            reverse(
                "frontend-workout",
                kwargs={
                    "workout_id": workout.anchor.ap_id,
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

        anchor = WorkoutAnchor.objects.get(ap_id=workout_id, actor__webfinger=webfinger)
        workout = anchor.workout

        return render(
            request,
            "frontend/workouts/view.html",
            {"workout": workout},
        )


class WorkoutNoteView(FedleticView):
    def get_ap(self, request, webfinger, workout_id, *args, **kwargs):
        if "@" not in webfinger:
            webfinger = f"{webfinger}@{settings.SITE_URL}"
        anchor = WorkoutAnchor.objects.get(ap_id=workout_id, actor__webfinger=webfinger)
        return JsonResponse(anchor.as_activitypub_object())

    def get(self, request, webfinger, workout_id):
        if "@" not in webfinger:
            webfinger = f"{webfinger}@{settings.SITE_URL}"
        anchor = WorkoutAnchor.objects.get(ap_id=workout_id, actor__webfinger=webfinger)
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
