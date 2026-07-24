from django import forms

from .models import (
    Student,
    Candidate,
    Position,
    Election,
)

class StudentRegistrationForm(forms.ModelForm):

    class Meta:
        model = Student

        fields = [
            "admission_no",
            "full_name",
            "email",
            "course",
            "year",
        ]


class CandidateForm(forms.ModelForm):

    class Meta:

        model = Candidate

        fields = [
            "student",
            "position",
            "photo",
            "manifesto",
        ]

        widgets = {

            "manifesto": forms.Textarea(
                attrs={
                    "rows": 4,
                    "class": "form-control",
                }
            ),

            "student": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "position": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "photo": forms.FileInput(
                attrs={
                    "class": "form-control",
                }
            ),
        }

    def __init__(self, *args, **kwargs):

        election = kwargs.pop("election", None)

        super().__init__(*args, **kwargs)

        # Display students as:
        # 3118 - Eddie Mwangi
        self.fields["student"].label_from_instance = (
            lambda obj: f"{obj.admission_no} - {obj.full_name}"
        )

        if election:

            self.fields["position"].queryset = Position.objects.filter(
                election=election
            )

            if election.election_type == "delegate":

                self.fields["student"].queryset = Student.objects.filter(
                    role="student"
                )

            elif election.election_type == "leader":

                self.fields["student"].queryset = Student.objects.all()
                
class PositionForm(forms.ModelForm):

    class Meta:

        model = Position

        fields = [
            "name",
        ]

        widgets = {

            

            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),

            
        }
    def clean(self):

        cleaned_data = super().clean()

        election = cleaned_data.get("election")
        election_type = cleaned_data.get("election_type")

        if election and election_type:

            if election.election_type != election_type:

                raise forms.ValidationError(
                    "Position type must match election type."
                )

        return cleaned_data
        
                
class ElectionForm(forms.ModelForm):

    class Meta:

        model = Election

        fields = [
            "title",
            "election_type",
            "start_date",
            "end_date",
        ]

        widgets = {

            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "election_type": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "start_date": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                }
            ),

            "end_date": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                }
            ),

        }