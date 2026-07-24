from django.urls import path
from . import views

urlpatterns = [

    # -----------------------------
    # HOME & LOGIN
    # -----------------------------

    path(
        "",
        views.login_view,
        name="home",
    ),

    path(
        "login/",
        views.login_view,
        name="login",
    ),

    # -----------------------------
    # REGISTRATION
    # -----------------------------

    path(
        "register/",
        views.register_student,
        name="register_student",
    ),

    path(
        "dashboard/",
        views.dashboard,
        name="dashboard",
    ),

    # -----------------------------
    # VOTING
    # -----------------------------

    path(
        "confirm-vote/<int:candidate_id>/<int:election_id>/<int:position_id>/",
        views.confirm_vote,
        name="confirm_vote",
    ),

    path(
        "vote/<int:candidate_id>/<int:election_id>/<int:position_id>/",
        views.cast_vote,
        name="cast_vote",
    ),

    # -----------------------------
    # ELECTION MANAGEMENT
    # -----------------------------

    path(
        "elections/start/<int:election_id>/",
        views.start_election,
        name="start_election",
    ),

    path(
        "elections/close/<int:election_id>/",
        views.close_election,
        name="close_election",
    ),

    path(
        "elections/finalize/<int:election_id>/",
        views.finalize_election_view,
        name="finalize_election",
    ),

    path(
        "elections/run/<int:election_id>/",
        views.run_full_cycle,
        name="run_full_cycle",
    ),

    path(
        "elections/active/",
        views.active_elections,
        name="active_elections",
    ),

    # -----------------------------
    # STUDENT RESULTS
    # -----------------------------

    path(
        "results/<int:election_id>/<int:position_id>/",
        views.election_results,
        name="election_results",
    ),

    path(
        "results/live/<int:election_id>/<int:position_id>/",
        views.live_results,
        name="live_results",
    ),

    # -----------------------------
    # DJANGO ADMIN RESULTS
    # -----------------------------

    path(
        "admin/election/<int:election_id>/results/",
        views.admin_election_results,
        name="admin_election_results",
    ),

    path(
    "admin/election/<int:election_id>/live/",
    views.live_admin_results,
    name="live_admin_results",
),
    
    path(
    "admin/election/<int:election_id>/results/pdf/",
    views.export_results_pdf,
    name="export_results_pdf",
),

path(
    "admin/election/<int:election_id>/results/csv/",
    views.export_results_csv,
    name="export_results_csv",
),

    # -----------------------------
    # ADMIN TOOLS
    # -----------------------------

    path(
        "verify-students/",
        views.verify_students,
        name="verify_students",
    ),

    path(
        "import-students/",
        views.import_students,
        name="import_students",
    ),


    path(
    "administrator/",
    views.admin_dashboard,
    name="admin_dashboard",
    ),
    
    
    # -----------------------------
# CUSTOM ADMIN
# -----------------------------
path(
    "administrator/elections/<int:election_id>/",
    views.admin_election_details,
    name="admin_election_details",

),


path(
    "administrator/elections/<int:election_id>/candidates/",
    views.admin_election_candidates,
    name="admin_election_candidates",
),

path(
    "administrator/elections/<int:election_id>/positions/",
    views.admin_election_positions,
    name="admin_election_positions",
),

path(
    "administrator/elections/<int:election_id>/candidates/add/",
    views.add_candidate,
    name="add_candidate",
),

path(
    "administrator/candidates/<int:candidate_id>/edit/",
    views.edit_candidate,
    name="edit_candidate",
),

path(
    "administrator/candidates/<int:candidate_id>/delete/",
    views.delete_candidate,
    name="delete_candidate",
),


path(
    "administrator/elections/",
    views.admin_elections,
    name="admin_elections",
),

path(
    "administrator/elections/add/",
    views.add_election,
    name="add_election",
),

path(
    "administrator/elections/<int:election_id>/edit/",
    views.edit_election,
    name="edit_election",
),

path(
    "administrator/elections/<int:election_id>/delete/",
    views.delete_election,
    name="delete_election",
),




path(
    "administrator/students/",
    views.admin_students,
    name="admin_students",
),

path(
    "administrator/candidates/",
    views.admin_candidates,
    name="admin_candidates",
),

path(
    "administrator/positions/",
    views.admin_positions,
    name="admin_positions",
),

path(
    "administrator/elections/<int:election_id>/positions/add/",
    views.add_position,
    name="add_position",
),

path(
    "administrator/positions/<int:position_id>/edit/",
    views.edit_position,
    name="edit_position",
),

path(
    "administrator/positions/<int:position_id>/delete/",
    views.delete_position,
    name="delete_position",
),

path(
    "administrator/votes/",
    views.admin_votes,
    name="admin_votes",
),

path(
    "administrator/results/",
    views.admin_results,
    name="admin_results",
),
    
]