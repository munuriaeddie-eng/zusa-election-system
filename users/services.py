from django.db.models import Count

from .models import Vote, Candidate, Position

from django.db.models import Count

from .models import Candidate
from .models import Vote


# ---------------------------------
# RESULTS FOR ONE POSITION
# ---------------------------------

def get_all_results(election):

    results = []

    positions = Position.objects.filter(
        election=election
    ).order_by("id")

    for position in positions:

        candidates = (
            Candidate.objects.filter(
                election=election,
                position=position,
            )
            .select_related(
                "student"
            )
            .annotate(
                votes=Count("vote")
            )
            .order_by(
                "-votes",
                "student__full_name",
            )
        )

        highest = 0

        if candidates.exists():
            highest = candidates.first().votes

        leaders = []

        if highest > 0:

            leaders = [
                candidate
                for candidate in candidates
                if candidate.votes == highest
            ]

        winner = None
        tie = False

        if highest > 0:

            if len(leaders) == 1:

                winner = leaders[0]

            else:

                tie = True

        results.append({

            "position": position,

            "position_id": position.id,

            "candidates": candidates,

            "winner": winner,

            "tie": tie,

            "highest": highest,

            "total_candidates": candidates.count(),

            "total_votes": sum(
                candidate.votes
                for candidate in candidates
            ),

        })

    return results

# ---------------------------------
# GET WINNER
# ---------------------------------

def get_winner_object(election, position):

    winner = (
        Candidate.objects.filter(
            election=election,
            position=position
        )
        .annotate(
            votes=Count("vote")
        )
        .order_by("-votes")
        .first()
    )

    if winner is None:
        return None, 0

    return winner.student, winner.votes


# ---------------------------------
# PROMOTE WINNER
# ---------------------------------

def promote_winner(election, position):

    student, votes = get_winner_object(
        election,
        position
    )

    if student is None:
        return None

    if election.election_type == "delegate":

        if student.role != "student":
            return None

        student.role = "delegate"

    student.current_position = position

    student.save()

    return student.full_name


# ---------------------------------
# FINALIZE ELECTION
# ---------------------------------

def finalize_election(election):

    if election.status != "closed":

        raise ValueError(
            "Only closed elections can be finalized."
        )

    winners = []

    positions = Position.objects.filter(
        election_type=election.election_type
    )

    for position in positions:

        winner = promote_winner(
            election,
            position,
        )

        if winner:

            winners.append({
                "position": position.name,
                "winner": winner,
            })

    election.status = "finalized"

    election.save()

    return winners




def get_dashboard_results(election):

    output = []

    positions = (
        Candidate.objects.filter(
            election=election
        )
        .values_list(
            "position",
            flat=True
        )
        .distinct()
    )

    for position in positions:

        candidates = (
            Candidate.objects.filter(
                election=election,
                position_id=position
            )
            .annotate(
                votes=Count("vote")
            )
            .order_by("-votes")
        )

        highest = 0

        if candidates.exists():
            highest = candidates.first().votes

        output.append({

            "position": candidates.first().position if candidates else None,

            "highest": highest,

            "candidates": candidates

        })

    return output