from django.db.models import Count

from .models import (
    Candidate,
    Position,
    Student,
    Vote,
)


def get_all_results(election):

    results = []

    positions = Position.objects.filter(
        election=election
    ).order_by("id")

    for position in positions:

        candidates = Candidate.objects.filter(
            election=election,
            position=position,
        ).select_related(
            "student"
        ).annotate(
            votes=Count("vote")
        ).order_by(
            "-votes",
            "student__full_name",
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