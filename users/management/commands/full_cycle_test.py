from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count
from random import choice

from users.models import (
    Election,
    Student,
    Position,
    Candidate,
    Vote,
)


class Command(BaseCommand):

    help = "Runs the complete election test"

    def handle(self, *args, **kwargs):

        self.stdout.write("=" * 50)
        self.stdout.write("STARTING FULL ELECTION TEST")
        self.stdout.write("=" * 50)


        # 1. Create election

        election = Election.objects.create(
            title="July 2026 Delegate Election",
            election_type="delegate",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=7),
            status="active"
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Election created and activated"
            )
        )


        # 2. Create positions

        positions = [
            "Class Representative",
            "Department Representative",
            "School Representative",
        ]


        for name in positions:

            position, created = Position.objects.get_or_create(
                name=name,
                election_type="delegate"
            )

            if created:
                self.stdout.write(
                    f"Created position: {name}"
                )


        delegate_positions = Position.objects.filter(
            election_type="delegate"
        )


        # 3. Create candidates

        students = Student.objects.filter(
            role="student"
        )[:20]


        student_index = 0


        for position in delegate_positions:

            for i in range(2):

                student = students[student_index]

                candidate = Candidate.objects.create(
                    student=student,
                    election=election,
                    position=position,
                    manifesto="Improving student leadership."
                )


                self.stdout.write(
                    f"Created candidate: {candidate}"
                )

                student_index += 1



        # 4. Simulate voting


        self.stdout.write("=" * 50)
        self.stdout.write("SIMULATING VOTES")
        self.stdout.write("=" * 50)


        voters = Student.objects.filter(
            role="student"
        )[:20]


        vote_count = 0


        for voter in voters:

            for position in delegate_positions:

                candidates = Candidate.objects.filter(
                    election=election,
                    position=position
                )


                selected_candidate = choice(
                    list(candidates)
                )


                Vote.objects.create(
                    voter=voter,
                    candidate=selected_candidate,
                    election=election,
                    position=position
                )


                vote_count += 1



        self.stdout.write(
            f"Votes created: {vote_count}"
        )



        # 5. Calculate winners


        self.stdout.write("=" * 50)
        self.stdout.write("ELECTION RESULTS")
        self.stdout.write("=" * 50)


        for position in delegate_positions:


            winner = Candidate.objects.filter(
                election=election,
                position=position
            ).annotate(
                total_votes=Count("vote")
            ).order_by(
                "-total_votes"
            ).first()


            self.stdout.write(
                f"Position: {position.name}"
            )

            self.stdout.write(
                f"Winner: {winner.student.full_name}"
            )

            self.stdout.write(
                f"Votes: {winner.total_votes}"
            )

            self.stdout.write("-" * 50)



        # 6. Close and finalize election


        election.status = "closed"
        election.save()


        election.status = "finalized"
        election.save()


        self.stdout.write("=" * 50)

        self.stdout.write(
            self.style.SUCCESS(
                "FULL ELECTION TEST COMPLETED"
            )
        )

        self.stdout.write(
            f"Final Status: {election.status}"
        )