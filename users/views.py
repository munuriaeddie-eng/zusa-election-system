from django.utils import timezone
from django.db.models import Count
from reportlab.pdfgen import canvas
from io import BytesIO

from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect, get_object_or_404

from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login
from .forms import (
    StudentRegistrationForm,
    CandidateForm,
    PositionForm,
    ElectionForm,
)
from django.db.models import Q

import csv
from django.contrib.auth import logout


from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.db import transaction

from .services import get_all_results


from .models import Student
from .models import Candidate
from .models import Election,Position
from .models import Vote



from .services import (
    get_all_results,
    get_dashboard_results,
    get_winner_object,
    promote_winner,
    finalize_election,
)


# --------------------------------------------------
# JSON HELPERS
# --------------------------------------------------

def ok(data):
    return JsonResponse({
        "status": "success",
        "data": data
    })


def fail(message):
    return JsonResponse({
        "status": "error",
        "message": message
    })


# --------------------------------------------------
# HOME
# --------------------------------------------------

def home(request):

    if not request.user.is_authenticated:
        return render(request, "home.html")

    student = Student.objects.filter(
        user=request.user
    ).first()

    if not student:
        return redirect("register_student")

    if not student.is_verified:
        return render(
            request,
            "pending_verification.html"
        )

    return redirect("dashboard")

# --------------------------------------------------
# LOGIN
# --------------------------------------------------

def login_view(request):

    if request.user.is_authenticated:

        if request.user.is_staff:
            return redirect("admin_dashboard")

        return redirect("dashboard")

    if request.method == "POST":

        admission_no = request.POST.get("admission_no")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=admission_no,
            password=password
        )

        if user:

            login(request, user)

            if user.is_staff:
                return redirect("admin_dashboard")

            return redirect("dashboard")

        return render(
            request,
            "home.html",
            {
                "error": "Invalid admission number or password."
            }
        )

    return render(
        request,
        "home.html"
    )

def logout_view(request):

    if request.method == "POST":
        logout(request)

    return redirect("login")
# --------------------------------------------------
# STUDENT REGISTRATION
# --------------------------------------------------

@login_required
def register_student(request):

    if Student.objects.filter(
        user=request.user
    ).exists():
        return redirect("dashboard")

    if request.method == "POST":

        form = StudentRegistrationForm(
            request.POST
        )

        if form.is_valid():

            student = form.save(
                commit=False
            )

            student.user = request.user
            student.role = "student"
            student.is_verified = False

            student.save()

            return render(
                request,
                "pending_verification.html"
            )

    else:

        form = StudentRegistrationForm()

    return render(
        request,
        "register_student.html",
        {
            "form": form
        }
    )


# --------------------------------------------------
# VERIFY STUDENTS
# --------------------------------------------------

@staff_member_required
def verify_students(request):

    students = Student.objects.filter(
        is_verified=False
    )

    return render(
        request,
        "verify_students.html",
        {
            "students": students
        }
    )


# --------------------------------------------------
# IMPORT PAGE
# --------------------------------------------------
@staff_member_required
def import_students(request):

    if request.method == "POST":

        csv_file = request.FILES.get("csv_file")

        if not csv_file:
            messages.error(request, "Please select a CSV file.")
            return redirect(request.path)

        try:

            decoded = csv_file.read().decode("utf-8").splitlines()
            reader = csv.DictReader(decoded)

            existing_students = set(
                Student.objects.values_list(
                    "admission_no",
                    flat=True
                )
            )

            existing_usernames = set(
                User.objects.values_list(
                    "username",
                    flat=True
                )
            )

            existing_emails = set(
                User.objects.values_list(
                    "email",
                    flat=True
                )
            )

            users_to_create = []
            student_rows = []

            skipped = 0

            default_password = make_password("1234")

            for row in reader:

                admission_no = row["admission_no"].strip()
                email = row["email"].strip()

                if (
                    admission_no in existing_students
                    or admission_no in existing_usernames
                    or email in existing_emails
                ):
                    skipped += 1
                    continue

                users_to_create.append(
                    User(
                        username=admission_no,
                        email=email,
                        password=default_password,
                    )
                )

                student_rows.append(row)

                existing_students.add(admission_no)
                existing_usernames.add(admission_no)
                existing_emails.add(email)

            with transaction.atomic():

                User.objects.bulk_create(
                    users_to_create,
                    batch_size=500
                )

                users = User.objects.filter(
                    username__in=[
                        row["admission_no"].strip()
                        for row in student_rows
                    ]
                )

                user_map = {
                    user.username: user
                    for user in users
                }

                students = []

                for row in student_rows:

                    admission_no = row["admission_no"].strip()

                    students.append(
                        Student(
                            user=user_map[admission_no],
                            admission_no=admission_no,
                            full_name=row["full_name"].strip(),
                            email=row["email"].strip(),
                            course=row["course"].strip(),
                            year=int(row["year"]),
                            role="student",
                            is_verified=True,
                        )
                    )

                Student.objects.bulk_create(
                    students,
                    batch_size=500
                )

            messages.success(
                request,
                f"Successfully imported {len(students)} students. Skipped {skipped} duplicates."
            )

            return redirect("admin:users_student_changelist")

        except Exception as e:

            messages.error(
                request,
                f"Import failed: {e}"
            )

            return redirect(request.path)

    return render(
        request,
        "admin/import_students.html"
    )
# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

@login_required
def dashboard(request):
    return HttpResponse("Dashboard works")

# --------------------------------------------------
# VOTING RULES
# --------------------------------------------------

def can_vote(student, election):

    now = timezone.now()

    if election.status != "active":
        return False, "Election is not active."
        
    if now < election.start_date:
        return False, "Voting has not started."

    if now > election.end_date:
        return False, "Voting has ended."

    if election.election_type == "delegate":

        if student.role != "student":
            return False, "Only students may vote."

    elif election.election_type == "leader":

        if student.role != "delegate":
            return False, "Only delegates may vote."

    return True, "OK"



@login_required
def confirm_vote(request, candidate_id, election_id, position_id):

    student = get_object_or_404(
        Student,
        user=request.user
    )

    election = get_object_or_404(
        Election,
        id=election_id
    )

    candidate = get_object_or_404(
        Candidate,
        id=candidate_id
    )

    position = get_object_or_404(
        Position,
        id=position_id
    )

    return render(
        request,
        "confirm_vote.html",
        {
            "student": student,
            "candidate": candidate,
            "election": election,
            "position": position,
        }
    )



# -------------------------
# VOTE
# -------------------------
@login_required
def cast_vote(request, candidate_id, election_id, position_id):

    if request.method != "POST":
        return redirect("dashboard")

    student = get_object_or_404(
        Student,
        user=request.user
    )

    if not student.is_verified:
        return fail(
            "Your account is awaiting verification."
        )

    election = get_object_or_404(
        Election,
        id=election_id
    )

    candidate = get_object_or_404(
        Candidate,
        id=candidate_id
    )

    position = get_object_or_404(
        Position,
        id=position_id
    )

    allowed, message = can_vote(
        student,
        election
    )

    if not allowed:
        return fail(message)

    if candidate.election != election:
        return fail("Invalid candidate.")

    if candidate.position != position:
        return fail("Invalid position.")

    already_voted = Vote.objects.filter(
        voter=student,
        election=election,
        position=position
    ).exists()

    if already_voted:
        return fail(
            "You have already voted for this position."
        )

    Vote.objects.create(
        voter=student,
        candidate=candidate,
        election=election,
        position=position
    )

    messages.success(
        request,
        "Your vote has been recorded successfully."
    )

    return redirect("dashboard")
# --------------------------------------------------
# ACTIVE ELECTIONS
# --------------------------------------------------

def active_elections(request):

    now = timezone.now()

    elections = Election.objects.filter(
    status="active",
    start_date__lte=now,
    end_date__gte=now
    )

    return ok([
        {
            "id": election.id,
            "title": election.title,
            "type": election.election_type,
        }
        for election in elections
    ])


# --------------------------------------------------
# START ELECTION
# --------------------------------------------------

@staff_member_required
def start_election(request, election_id):

    election = get_object_or_404(
        Election,
        id=election_id,
    )

    if election.status != "draft":

        messages.error(
            request,
            "Only draft elections can be started.",
        )

        return redirect(
            "admin_election_details",
            election.id,
        )

    if not Candidate.objects.filter(
        election=election,
    ).exists():

        messages.error(
            request,
            "You cannot start an election without candidates.",
        )

        return redirect(
            "admin_election_details",
            election.id,
        )

    positions = Position.objects.filter(
        election=election,
    )
    for position in positions:

        if not Candidate.objects.filter(
            election=election,
            position=position,
        ).exists():

            messages.error(
                request,
                f"No candidate has been assigned to {position.name}.",
            )

            return redirect(
                "admin_election_details",
                election.id,
            )

    if Election.objects.filter(
        election_type=election.election_type,
        status="active",
    ).exclude(
        id=election.id,
    ).exists():

        messages.error(
            request,
            "Another election of this type is already active.",
        )

        return redirect(
            "admin_election_details",
            election.id,
        )

    election.status = "active"

    election.save()

    messages.success(
        request,
        "Election started successfully.",
    )

    return redirect(
        "admin_election_details",
        election.id,
    )

# --------------------------------------------------
# CLOSE ELECTION
# --------------------------------------------------

@staff_member_required
def close_election(request, election_id):

    election = get_object_or_404(
        Election,
        id=election_id,
    )

    if election.status != "active":

        messages.error(
            request,
            "Only active elections can be closed.",
        )

        return redirect(
            "admin_election_details",
            election.id,
        )

    election.status = "closed"

    election.save()

    messages.success(
        request,
        "Election closed successfully.",
    )

    return redirect(
        "admin_election_details",
        election.id,
    )

# --------------------------------------------------
# RESULTS
# --------------------------------------------------

def election_results(request, election_id, position_id):

    return ok(
        list(
            get_results(
                election_id,
                position_id
            )
        )
    )


def live_results(request, election_id, position_id):

    return election_results(
        request,
        election_id,
        position_id
    )


# --------------------------------------------------
# WINNER
# --------------------------------------------------

def get_winner(election_id, position_id):

    results = (
        Vote.objects.filter(
            election_id=election_id,
            position_id=position_id
        )
        .values("candidate")
        .annotate(
            total_votes=Count("id")
        )
        .order_by("-total_votes")
    )

    if not results.exists():
        return None

    candidate = Candidate.objects.get(
        id=results[0]["candidate"]
    )

    return candidate.student.full_name


# --------------------------------------------------
# FINALIZE ELECTION
# --------------------------------------------------

@staff_member_required
def process_election(request, election_id):

    election = get_object_or_404(
        Election,
        id=election_id
    )

    try:

        winners = finalize_election(
            election
        )

        messages.success(
            request,
            "Election finalized successfully."
        )

    except ValueError as e:

        messages.error(
            request,
            str(e)
        )

    return redirect(
        "admin_election_details",
        election.id
    )

@staff_member_required
def finalize_election_view(request, election_id):

    return process_election(
        request,
        election_id
    )


@staff_member_required
def run_full_cycle(request, election_id):

    return process_election(
        request,
        election_id
    )




@staff_member_required
def admin_results(request):

    elections = Election.objects.filter(
        is_active=True
    ).annotate(
        total_candidates=Count(
            "candidate",
            distinct=True,
        ),
        total_votes=Count(
            "vote",
            distinct=True,
        ),
    ).order_by("-id")

    context = {

        "elections": elections,

        "total_elections": elections.count(),

        "active_count": elections.filter(
            status="active",
        ).count(),

        "closed_count": elections.filter(
            status="closed",
        ).count(),

        "finalized_count": elections.filter(
            status="finalized",
        ).count(),

        "draft_count": elections.filter(
            status="draft",
        ).count(),

        "active_page": "results",

    }

    return render(
        request,
        "adminpanel/results.html",
        context,
    )

@staff_member_required
def admin_election_results(request, election_id):

    election = get_object_or_404(
        Election,
        id=election_id,
    )

    results = get_all_results(election)

    total_votes = Vote.objects.filter(
        election=election,
    ).count()

    return render(
        request,
        "adminpanel/election_results.html",
        {
            "election": election,
            "results": results,
            "total_votes": total_votes,
            "active_page": "results",
            "live_url": f"/admin/election/{election.id}/live/",
        },
    )



@staff_member_required
def live_admin_results(request, election_id):

    election = get_object_or_404(
        Election,
        id=election_id,
    )

    results = get_all_results(election)

    data = []

    for section in results:

        candidates = []

        for candidate in section["candidates"]:

            candidates.append({

                "id": candidate.id,

                "name": candidate.student.full_name,

                "admission_no": candidate.student.admission_no,

                "course": candidate.student.course,

                "votes": candidate.votes,

                "photo": candidate.photo.url if candidate.photo else "",

            })

        data.append({

            "position": section["position"].name,

            "position_id": section["position"].id,

            "highest": section["highest"],

            "tie": section["tie"],

            "winner": (
                section["winner"].student.full_name
                if section["winner"]
                else None
            ),

            "total_votes": section["total_votes"],

            "total_candidates": len(candidates),

            "candidates": candidates,

        })

    return JsonResponse(data, safe=False)

# --------------------------------------------------
# CUSTOM ADMIN DASHBOARD
# --------------------------------------------------
@staff_member_required
def admin_dashboard(request):

    active_election = Election.objects.filter(
        status="active"
    ).first()

    draft_elections = Election.objects.filter(
        status="draft"
    ).count()

    finalized_elections = Election.objects.filter(
        status="finalized"
    ).count()

    verified_students = Student.objects.filter(
        is_verified=True
    ).count()

    unverified_students = Student.objects.filter(
        is_verified=False
    ).count()

    context = {

        "students": Student.objects.count(),

        "verified_students": verified_students,

        "unverified_students": unverified_students,

        "candidates": Candidate.objects.count(),

        "positions": Position.objects.count(),

        "votes": Vote.objects.count(),

        "active_election": active_election,

        "draft_elections": draft_elections,

        "finalized_elections": finalized_elections,

        "elections": Election.objects.order_by("-id")[:5],

        "recent_votes": Vote.objects.select_related(
            "voter",
            "candidate",
            "position",
        ).order_by("-id")[:10],

        "active_page": "dashboard",
    }

    return render(
        request,
        "adminpanel/dashboard.html",
        context,
    )
    
# --------------------------------------------------
# CUSTOM ADMIN PAGES
# --------------------------------------------------


@staff_member_required
def admin_elections(request):

    search = request.GET.get("search", "")
    status = request.GET.get("status", "")
    election_type = request.GET.get("type", "")

    elections = Election.objects.filter(
        is_active=True
    )

    if search:
        elections = elections.filter(
            Q(title__icontains=search) |
            Q(election_type__icontains=search) |
            Q(status__icontains=search)
        )

    if status:
        elections = elections.filter(
            status=status
        )

    if election_type:
        elections = elections.filter(
            election_type=election_type
        )

    elections = elections.order_by("-id")

    return render(
        request,
        "adminpanel/elections.html",
        {
            "elections": elections,
            "search": search,
            "status": status,
            "type": election_type,
            "active_page": "elections",
        }
    )
    
from django.db.models import Q

@staff_member_required
def admin_students(request):

    search = request.GET.get("search", "")
    role = request.GET.get("role", "")
    verified = request.GET.get("verified", "")
    year = request.GET.get("year", "")

    students = Student.objects.all()

    if search:

        students = students.filter(

            Q(full_name__icontains=search) |

            Q(admission_no__icontains=search) |

            Q(email__icontains=search) |

            Q(course__icontains=search)

        )

    if role:

        students = students.filter(
            role=role
        )

    if verified:

        students = students.filter(
            is_verified=(verified == "true")
        )

    if year:

        students = students.filter(
            year=year
        )

    students = students.order_by("full_name")

    return render(
        request,
        "adminpanel/students.html",
        {
            "students": students,
            "search": search,
            "role": role,
            "verified": verified,
            "year": year,
            "active_page": "students",
        }
    )
from django.db.models import Q

@staff_member_required
def admin_candidates(request):

    search = request.GET.get("search", "")
    election = request.GET.get("election", "")
    position = request.GET.get("position", "")

    candidates = Candidate.objects.select_related(
        "student",
        "position",
        "election",
    )

    if search:

        candidates = candidates.filter(

            Q(student__full_name__icontains=search) |

            Q(student__admission_no__icontains=search) |

            Q(position__name__icontains=search) |

            Q(election__title__icontains=search)

        )

    if election:

        candidates = candidates.filter(
            election_id=election
        )

    if position:

        candidates = candidates.filter(
            position_id=position
        )

    candidates = candidates.order_by(
        "position__name",
        "student__full_name",
    )

    return render(
        request,
        "adminpanel/candidates.html",
        {
            "candidates": candidates,
            "search": search,
            "selected_election": election,
            "selected_position": position,
            "elections": Election.objects.filter(
                is_active=True
            ).order_by("title"),
            "positions": Position.objects.order_by("name"),
            "active_page": "candidates",
        },
    )

@staff_member_required
def admin_positions(request):

    positions = Position.objects.all()

    return render(
        request,
        "adminpanel/positions.html",
        {
            "positions": positions,
            "active_page": "positions",
        },
    )

@staff_member_required
def admin_election_positions(request, election_id):

    election = get_object_or_404(
        Election,
        id=election_id,
    )

    positions = Position.objects.filter(
        election=election,
    ).order_by("name")

    return render(
        request,
        "adminpanel/election_positions.html",
        {
            "election": election,
            "positions": positions,
            "active_page": "elections",
        },
    )

@staff_member_required
def add_position(request, election_id):

    election = get_object_or_404(
        Election,
        id=election_id,
    )

    if request.method == "POST":

        form = PositionForm(request.POST)

        if form.is_valid():

            position = form.save(commit=False)

            position.election = election

            position.election_type = election.election_type

            position.save()

            return redirect(
                "admin_election_positions",
                election.id,
            )

    else:

        form = PositionForm()

    return render(
        request,
        "adminpanel/add_position.html",
        {
            "form": form,
            "election": election,
            "active_page": "elections",
        },
    )
@staff_member_required
def edit_position(request, position_id):

    position = get_object_or_404(
        Position,
        id=position_id,
    )

    if request.method == "POST":

        form = PositionForm(
            request.POST,
            instance=position,
        )

        if form.is_valid():

            form.save()

            return redirect(
                "admin_positions",
            )

    else:

        form = PositionForm(
            instance=position,
        )

    return render(
        request,
        "adminpanel/edit_position.html",
        {
            "form": form,
            "position": position,
            "active_page": "positions",
        },
    )
    
@staff_member_required
def delete_position(request, position_id):

    position = get_object_or_404(
        Position,
        id=position_id,
    )

    if Candidate.objects.filter(
        position=position,
    ).exists():

        messages.error(
            request,
            "This position cannot be deleted because it already has candidates.",
        )

    else:

        position.delete()

        messages.success(
            request,
            "Position deleted successfully.",
        )

    return redirect(
        "admin_positions",
    ) 
    

@staff_member_required
def admin_votes(request):

    votes = Vote.objects.select_related(
        "voter",
        "candidate",
        "position",
        "election"
    ).order_by("-id")

    return render(
        request,
        "adminpanel/votes.html",
        {
            "votes": votes,
        }
    )


@staff_member_required
def admin_results(request):

    elections = Election.objects.all().order_by("-id")

    return render(
        request,
        "adminpanel/results.html",
        {
            "elections": elections,
        }
    )
    
@staff_member_required
def add_election(request):

    if request.method == "POST":

        form = ElectionForm(request.POST)

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Election created successfully.",
            )

            return redirect(
                "admin_dashboard",
            )

    else:

        form = ElectionForm()

    return render(
        request,
        "adminpanel/add_election.html",
        {
            "form": form,
            "active_page": "elections",
        },
    )
    
@staff_member_required
def edit_election(request, election_id):

    election = get_object_or_404(
        Election,
        id=election_id,
    )

    if election.status != "draft":

        messages.error(
            request,
            "Only draft elections can be edited.",
        )

        return redirect(
            "admin_elections",
        )

    if request.method == "POST":

        form = ElectionForm(
            request.POST,
            instance=election,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Election updated successfully.",
            )

            return redirect(
                "admin_elections",
            )

    else:

        form = ElectionForm(
            instance=election,
        )

    return render(
        request,
        "adminpanel/edit_election.html",
        {
            "form": form,
            "election": election,
            "active_page": "elections",
        },
    )
    
    
@staff_member_required
def delete_election(request, election_id):

    election = get_object_or_404(
        Election,
        id=election_id,
    )

    if election.status != "draft":

        messages.error(
            request,
            "Only draft elections can be archived.",
        )

        return redirect(
            "admin_elections",
        )

    if Vote.objects.filter(
        election=election,
    ).exists():

        messages.error(
            request,
            "This election has recorded votes and cannot be archived.",
        )

        return redirect(
            "admin_elections",
        )

    election.is_active = False

    election.save()

    messages.success(
        request,
        "Election archived successfully.",
    )

    return redirect(
        "admin_elections",
    )
    
    
    
    
@staff_member_required
def admin_election_details(request, election_id):

    election = get_object_or_404(
        Election,
        id=election_id,
    )

    candidates = (
    Candidate.objects.select_related(
        "student",
        "position",
    )
    .filter(
        election=election,
    )
    .annotate(
        total_votes=Count("vote")
    )
    .order_by(
        "position__name",
        "-total_votes",
        "student__full_name",
    )
    )
    
    highest_votes = 0

    if candidates.exists():

        highest_votes = candidates.first().total_votes
        
        

    candidate_count = Candidate.objects.filter(
        election=election,
    ).count()

    vote_count = Vote.objects.filter(
        election=election,
    ).count()

    position_count = Position.objects.filter(
        election_type=election.election_type,
    ).count()

    eligible_voters = Student.objects.filter(
        role="student",
        is_verified=True,
    ).count()

    maximum_votes = eligible_voters * position_count

    progress = 0

    if maximum_votes > 0:

        progress = round(
            (vote_count / maximum_votes) * 100
        )

    context = {

        "election": election,

        "candidate_count": candidate_count,

        "vote_count": vote_count,

        "position_count": position_count,

        "eligible_voters": eligible_voters,

        "maximum_votes": maximum_votes,

        "progress": progress,

        "candidates": candidates,

        "highest_votes": highest_votes,

        "active_page": "elections",

    }
    return render(
        request,
        "adminpanel/election_details.html",
        context,
    )
    
@staff_member_required
def admin_election_candidates(request, election_id):

    election = get_object_or_404(
        Election,
        id=election_id,
    )

    candidates = (
        Candidate.objects.select_related(
            "student",
            "position",
        )
        .filter(
            election=election,
        )
        .order_by(
            "position__name",
            "student__full_name",
        )
    )

    return render(
        request,
        "adminpanel/election_candidates.html",
        {
            "election": election,
            "candidates": candidates,
            "active_page": "elections",
        },
    )
    
@staff_member_required
from django.http import HttpResponse
import traceback

def add_candidate(request, election_id):
    election = get_object_or_404(
        Election,
        id=election_id,
    )

    if election.status in ["active", "closed", "finalized"]:
        messages.error(
            request,
            "Candidates cannot be added once the election has started."
        )
        return redirect(
            "admin_election_candidates",
            election.id,
        )

    if request.method == "POST":

        form = CandidateForm(
            request.POST,
            request.FILES,
            election=election,
        )

        try:
            if form.is_valid():

                candidate = form.save(commit=False)
                candidate.election = election
                candidate.save()

                return redirect(
                    "admin_election_candidates",
                    election.id,
                )
            else:
                return HttpResponse(form.errors)

        except Exception:
            return HttpResponse(
                "<pre>" + traceback.format_exc() + "</pre>"
            )

    else:
        form = CandidateForm(election=election)

    return render(
        request,
        "adminpanel/add_candidate.html",
        {
            "form": form,
            "election": election,
            "active_page": "elections",
        },
    )
@staff_member_required
def edit_candidate(request, candidate_id):

    candidate = get_object_or_404(
        Candidate,
        id=candidate_id,
    )
    
    if candidate.election.status in ["active", "closed", "finalized"]:

        messages.error(
            request,
            "Candidates cannot be edited after the election has started."
        )

        return redirect(
            "admin_election_candidates",
            candidate.election.id,
        )

    if request.method == "POST":

        form = CandidateForm(
            request.POST,
            request.FILES,
            instance=candidate,
            election=candidate.election
        )

        if form.is_valid():

            form.save()

            return redirect(
                "admin_election_candidates",
                candidate.election.id,
            )

    else:

        form = CandidateForm(
        instance=candidate,
        election=candidate.election
    )

    return render(
        request,
        "adminpanel/add_candidate.html",
        {
            "form": form,
            "election": candidate.election,
            "active_page": "elections",
        },
    )
    
@staff_member_required
def delete_candidate(request, candidate_id):

    candidate = get_object_or_404(
        Candidate,
        id=candidate_id,
    )

    if candidate.election.status in ["active", "finalized"]:

        messages.error(
            request,
            "Candidates cannot be deleted while an election is active or finalized."
        )

        return redirect(
            "admin_election_candidates",
            candidate.election.id,
        )

    election_id = candidate.election.id

    if request.method == "POST":

        candidate.delete()

        messages.success(
            request,
            "Candidate deleted successfully."
        )

        return redirect(
            "admin_election_candidates",
            election_id,
        )

    return render(
        request,
        "adminpanel/delete_candidate.html",
        {
            "candidate": candidate,
            "active_page": "elections",
        },
    )
    
@staff_member_required
def export_results_csv(request, election_id):

    election = get_object_or_404(
        Election,
        id=election_id
    )


    results = get_all_results(election)


    response = HttpResponse(
        content_type="text/csv"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="{election.title}_results.csv"'
    )


    writer = csv.writer(response)


    writer.writerow([
        "Position",
        "Candidate",
        "Admission Number",
        "Course",
        "Votes"
    ])



    for section in results:

        for candidate in section["candidates"]:

            writer.writerow([

                section["position"].name,

                candidate.student.full_name,

                candidate.student.admission_no,

                candidate.student.course,

                candidate.votes,

            ])



    return response

@staff_member_required
def export_results_pdf(request, election_id):

    election = get_object_or_404(
        Election,
        id=election_id
    )


    results = get_all_results(election)


    buffer = BytesIO()


    pdf = canvas.Canvas(buffer)


    y = 800


    pdf.setFont(
        "Helvetica-Bold",
        16
    )


    pdf.drawString(
        50,
        y,
        "Election Results Report"
    )


    y -= 40


    pdf.setFont(
        "Helvetica",
        12
    )


    pdf.drawString(
        50,
        y,
        f"Election: {election.title}"
    )


    y -= 30



    for section in results:


        pdf.drawString(
            50,
            y,
            f"Position: {section['position'].name}"
        )


        y -= 20



        for candidate in section["candidates"]:


            text = (
                f"{candidate.student.full_name} "
                f"- {candidate.votes} Votes"
            )


            pdf.drawString(
                70,
                y,
                text
            )


            y -= 20



        y -= 20



        if y < 100:

            pdf.showPage()

            y = 800



    pdf.save()


    buffer.seek(0)


    response = HttpResponse(
        buffer,
        content_type="application/pdf"
    )


    response["Content-Disposition"] = (
        f'attachment; filename="{election.title}_results.pdf"'
    )


    return response