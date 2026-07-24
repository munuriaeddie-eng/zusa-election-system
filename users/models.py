from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class Student(models.Model):
    ROLE_CHOICES = (
        ("student", "Student"),
        ("delegate", "Delegate"),
        ("leader", "Leader"),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    admission_no = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    course = models.CharField(max_length=100)
    year = models.PositiveIntegerField()

    role = models.CharField(
    max_length=20,
    choices=ROLE_CHOICES,
    default="student"
)

    current_position = models.ForeignKey(
        "Position",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="office_holders"
    )

    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.full_name


class Election(models.Model):
    ELECTION_TYPE = (
        ("delegate", "Delegate Election"),
        ("leader", "Leader Election"),
    )

    title = models.CharField(max_length=100)

    election_type = models.CharField(
        max_length=20,
        choices=ELECTION_TYPE
    )

    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    STATUS_CHOICES = (
    ("draft", "Draft"),
    ("active", "Active"),
    ("closed", "Closed"),
    ("finalized", "Finalized"),
)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft",
    )
    def __str__(self):
        return f"{self.title} - {self.election_type}"

    is_active = models.BooleanField(
    default=True,
    help_text="Indicates whether the election is currently active."
    )
    
    
class Position(models.Model):

    POSITION_TYPE = (
        ("delegate", "Delegate Election"),
        ("leader", "Leader Election"),
    )

    election = models.ForeignKey(
        Election,
        on_delete=models.CASCADE,
        related_name="positions"
        
    )

    name = models.CharField(max_length=100)

    election_type = models.CharField(
        max_length=20,
        choices=POSITION_TYPE
    )

    def __str__(self):
        return f"{self.name} ({self.election.title})"
    
class Candidate(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    position = models.ForeignKey(Position, on_delete=models.CASCADE)

    manifesto = models.TextField(blank=True)
    photo = models.ImageField(
    upload_to="candidate_photos/",
    blank=True,
    null=True
)

    def clean(self):

        if not self.election_id:

            return
        
        duplicate = Candidate.objects.filter(
            student=self.student,
            election=self.election,
            ).exclude(
                id=self.id
            ).exists()

        if duplicate:

            raise ValidationError(
                "This student is already registered as a candidate in this election."
            )

        if self.position.election != self.election:

            raise ValidationError(
                "This position does not belong to this election."
            )
            
        if self.election.election_type == "delegate":

            if self.student.role != "student":

                raise ValidationError(
                    "Only students can contest delegate elections."
                )


    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student.full_name} - {self.position.name}"


class Vote(models.Model):
    voter = models.ForeignKey(Student, on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    position = models.ForeignKey(Position, on_delete=models.CASCADE)

    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["voter", "election", "position"],
                name="unique_vote_per_position",
            )
        ]

    def __str__(self):
        return f"{self.voter.full_name} -> {self.candidate.student.full_name}"