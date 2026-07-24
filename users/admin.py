from django.contrib import admin
from django.contrib.auth.models import User
from django.urls import path, reverse
from django.utils.html import format_html

from . import views
from .models import (
    Student,
    Election,
    Position,
    Candidate,
    Vote,
)
from .services import (
    finalize_election,
    get_all_results,
)


# -------------------------------------------------
# STUDENT ADMIN
# -------------------------------------------------

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):

    list_display = (
        "full_name",
        "admission_no",
        "course",
        "role",
        "current_position",
        "is_verified",
    )

    list_filter = (
        "role",
        "is_verified",
    )

    search_fields = (
        "full_name",
        "admission_no",
    )

    fields = (
        "admission_no",
        "full_name",
        "email",
        "course",
        "year",
        "role",
        "current_position",
        "is_verified",
    )

    def save_model(self, request, obj, form, change):

        if obj.pk is None:

            user = User.objects.create_user(
                username=obj.admission_no,
                email=obj.email,
                password="1234"
            )

            obj.user = user

        super().save_model(
            request,
            obj,
            form,
            change
        )

    def get_urls(self):

        urls = super().get_urls()

        custom_urls = [

            path(
                "import-csv/",
                self.admin_site.admin_view(
                    views.import_students
                ),
                name="student_import_csv",
            ),

        ]

        return custom_urls + urls


# -------------------------------------------------
# CANDIDATE ADMIN
# -------------------------------------------------

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):

    list_display = (
        "photo_preview",
        "student",
        "position",
        "election",
    )

    fields = (
        "student",
        "election",
        "position",
        "photo",
        "manifesto",
    )

    # -----------------------------
    # Candidate Photo
    # -----------------------------
    def photo_preview(self, obj):

        if obj.photo:

            return format_html(
                '<img src="{}" width="60" height="60" style="border-radius:50%;">',
                obj.photo.url
            )

        return "No Photo"

    photo_preview.short_description = "Photo"

    # -----------------------------
    # Prevent Adding Candidates
    # -----------------------------
    def has_add_permission(self, request):

        active_exists = Election.objects.filter(
            status="active"
        ).exists()

        if active_exists:
            return False

        return super().has_add_permission(request)

    # -----------------------------
    # Prevent Editing Candidates
    # -----------------------------
    def has_change_permission(self, request, obj=None):

        if obj and obj.election.status in (
            "active",
            "finalized",
        ):
            return False

        return super().has_change_permission(
            request,
            obj,
        )

    # -----------------------------
    # Prevent Deleting Candidates
    # -----------------------------
    def has_delete_permission(self, request, obj=None):

        if obj and obj.election.status in (
            "active",
            "finalized",
        ):
            return False

        return super().has_delete_permission(
            request,
            obj,
        )
    
# -------------------------------------------------
# ELECTION ACTIONS
# -------------------------------------------------

@admin.action(description="▶ Start selected elections")
def start_selected(modeladmin, request, queryset):

    from django.contrib import messages

    started = 0

    for election in queryset:

        if election.status == "finalized":
            continue

        # Election must have candidates
        if not Candidate.objects.filter(
            election=election
        ).exists():

            messages.warning(
                request,
                f'"{election.title}" was not started because it has no candidates.'
            )

            continue

        # Only one election can be active
        Election.objects.filter(
            status="active"
        ).update(
            status="draft"
        )

        election.status = "active"
        election.save()

        started += 1

    if started:

        messages.success(
            request,
            f"{started} election(s) started successfully."
        )

    else:

        messages.warning(
            request,
            "No elections were started."
        )


# -------------------------------------------------

@admin.action(description="■ Close selected elections")
def close_selected(modeladmin, request, queryset):

    from django.contrib import messages

    closed = 0

    for election in queryset:

        if election.status != "active":
            continue

        election.status = "closed"
        election.save()

        closed += 1

    if closed:

        messages.success(
            request,
            f"{closed} election(s) closed successfully."
        )

    else:

        messages.warning(
            request,
            "No elections were closed."
        )


# -------------------------------------------------

@admin.action(description="🏆 Finalize selected elections")
def finalize_selected(modeladmin, request, queryset):

    from django.contrib import messages

    finalized = 0

    for election in queryset:

        if election.status != "closed":
            continue

        finalize_election(election)

        election.status = "finalized"
        election.save()

        finalized += 1

    if finalized:

        messages.success(
            request,
            f"{finalized} election(s) finalized successfully."
        )

    else:

        messages.warning(
            request,
            "No elections were finalized."
        )

# -------------------------------------------------
# ELECTION ADMIN
# -------------------------------------------------

@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "election_type",
        "candidate_count",
        "vote_count",
        "start_date",
        "end_date",
        "status_badge",
        "view_results_button",
    )

    list_filter = (
        "election_type",
        "status",
    )

    search_fields = (
        "title",
    )

    fields = (
        "title",
        "election_type",
        "start_date",
        "end_date",
        "status",
        "winners",
    )

    readonly_fields = (
        "status",
        "winners",
    )

    actions = (
        start_selected,
        close_selected,
        finalize_selected,
    )

    # -----------------------------------
    # Candidate Count
    # -----------------------------------

    def candidate_count(self, obj):

        count = Candidate.objects.filter(
            election=obj
        ).count()

        url = (
            reverse("admin:users_candidate_changelist")
            + f"?election__id__exact={obj.id}"
        )

        return format_html(
            '<a href="{}"><strong>{}</strong></a>',
            url,
            count,
        )

    candidate_count.short_description = "Candidates"

    # -----------------------------------
    # Vote Count
    # -----------------------------------

    def vote_count(self, obj):

        count = Vote.objects.filter(
            election=obj
        ).count()

        url = (
            reverse("admin:users_vote_changelist")
            + f"?election__id__exact={obj.id}"
        )

        return format_html(
            '<a href="{}"><strong>{}</strong></a>',
            url,
            count,
        )

    vote_count.short_description = "Votes"

     # -----------------------------------
# View Results Button
# -----------------------------------

    def view_results_button(self, obj):

        url = reverse(
            "admin_election_results",
            args=[obj.id],
        )

        return format_html(

            '<a class="button" href="{}">View Results</a>',

            url,

        )

    view_results_button.short_description = "Results"


    # -----------------------------------
    # Status Badge
    # -----------------------------------

    def status_badge(self, obj):

        colors = {
            "draft": "#ffc107",
            "active": "#198754",
            "closed": "#dc3545",
            "finalized": "#0d6efd",
        }

        color = colors.get(
            obj.status,
            "#6c757d",
        )

        return format_html(
            '<span style="background:{};color:white;padding:4px 10px;border-radius:12px;font-weight:bold;">{}</span>',
            color,
            obj.status.upper(),
        )

    status_badge.short_description = "Status"

    # -----------------------------------
    # Winners
    # -----------------------------------

    def winners(self, obj):

        if obj.status != "finalized":
            return "Election not finalized."

        results = get_all_results(obj)

        if not results:
            return "No winners."

        html = ""

        for item in results:

            candidates = item["candidates"]

            if candidates.exists():

                winner = candidates.first()

                html += (
                    f"<strong>{item['position'].name}</strong><br>"
                    f"{winner.student.full_name}"
                    f" ({winner.votes} votes)"
                    "<br><br>"
                )

        return format_html(html)

    winners.short_description = "Election Winners"
    # -----------------------------------
    # Permissions
    # -----------------------------------

    def has_change_permission(self, request, obj=None):

        if obj and obj.status in (
            "active",
            "finalized",
        ):
            return False

        return super().has_change_permission(
            request,
            obj,
        )

    def has_delete_permission(self, request, obj=None):

        if obj and obj.status in (
            "active",
            "finalized",
        ):
            return False

        return super().has_delete_permission(
            request,
            obj,
        )


# -------------------------------------------------
# POSITION ADMIN
# -------------------------------------------------

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "election_type",
    )

    list_filter = (
        "election_type",
    )

    search_fields = (
        "name",
    )


# -------------------------------------------------
# VOTE ADMIN
# -------------------------------------------------

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):

    list_display = (
        "voter",
        "candidate",
        "position",
        "election",
        "voted_at",
    )

    list_filter = (
        "election",
        "position",
    )

    search_fields = (
        "voter__full_name",
        "candidate__student__full_name",
    )

    ordering = (
        "-voted_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False