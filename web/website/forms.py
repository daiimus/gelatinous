"""
Django forms for Gelatinous Monster character creation and account registration.

Extends Evennia's default forms to add GRIM stat system, name structure,
and Cloudflare Turnstile verification.
"""

import re

from django import forms
from evennia.web.website.forms import (
    CharacterForm as EvenniaCharacterForm,
    AccountForm as EvenniaAccountForm
)


# Constants from telnet character creation
GRIM_TOTAL_POINTS = 300
GRIM_MIN = 1
GRIM_MAX = 150

SEX_CHOICES = [
    ('male', 'Male'),
    ('female', 'Female'),
    ('ambiguous', 'Ambiguous'),
]

# Regex for validating character names: must start and end with a letter,
# may contain letters, hyphens, and apostrophes in between.
_NAME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z\-']*[a-zA-Z]$")


def _validate_name(name: str) -> str:
    """Validate a character name component (first or last name).

    Args:
        name: The raw name string from the form.

    Returns:
        The stripped name if valid.

    Raises:
        forms.ValidationError: If the name doesn't match the allowed pattern.
    """
    name = name.strip()
    if not _NAME_PATTERN.match(name):
        raise forms.ValidationError(
            "Name must start and end with a letter, and contain only "
            "letters, hyphens, and apostrophes."
        )
    return name


class CharacterForm(EvenniaCharacterForm):
    """
    Extends Evennia's default CharacterForm with GRIM stats and name structure.
    
    GRIM System:
    - Grit: Physical power and endurance
    - Resonance: Psychic affinity and willpower
    - Intellect: Logic, memory, and reasoning
    - Motorics: Dexterity, reflexes, and coordination
    
    Total points must equal 300.
    """
    
    # Name fields (split from db_key)
    first_name = forms.CharField(
        max_length=30,
        min_length=2,
        label="First Name",
        help_text="Your character's first name (2-30 characters)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        min_length=2,
        label="Last Name",
        help_text="Your character's last name (2-30 characters)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name'
        })
    )
    
    # Sex/Gender
    sex = forms.ChoiceField(
        choices=SEX_CHOICES,
        initial='ambiguous',
        label="Sex",
        help_text="Biological sex presentation",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # GRIM Stats
    grit = forms.IntegerField(
        min_value=GRIM_MIN,
        max_value=GRIM_MAX,
        initial=75,
        label="Grit",
        help_text="Physical power and endurance (1-150)",
        widget=forms.NumberInput(attrs={
            'class': 'form-control grim-stat',
            'data-stat': 'grit',
            'value': '75'
        })
    )
    
    resonance = forms.IntegerField(
        min_value=GRIM_MIN,
        max_value=GRIM_MAX,
        initial=75,
        label="Resonance",
        help_text="Psychic affinity and willpower (1-150)",
        widget=forms.NumberInput(attrs={
            'class': 'form-control grim-stat',
            'data-stat': 'resonance',
            'value': '75'
        })
    )
    
    intellect = forms.IntegerField(
        min_value=GRIM_MIN,
        max_value=GRIM_MAX,
        initial=75,
        label="Intellect",
        help_text="Logic, memory, and reasoning (1-150)",
        widget=forms.NumberInput(attrs={
            'class': 'form-control grim-stat',
            'data-stat': 'intellect',
            'value': '75'
        })
    )
    
    motorics = forms.IntegerField(
        min_value=GRIM_MIN,
        max_value=GRIM_MAX,
        initial=75,
        label="Motorics",
        help_text="Dexterity, reflexes, and coordination (1-150)",
        widget=forms.NumberInput(attrs={
            'class': 'form-control grim-stat',
            'data-stat': 'motorics',
            'value': '75'
        })
    )
    
    class Meta(EvenniaCharacterForm.Meta):
        # Extend parent's fields with our custom fields
        fields = ('first_name', 'last_name', 'sex', 'desc', 'grit', 'resonance', 'intellect', 'motorics')
    
    def clean_first_name(self):
        """Validate first name format."""
        return _validate_name(self.cleaned_data.get('first_name', ''))
    
    def clean_last_name(self):
        """Validate last name format."""
        return _validate_name(self.cleaned_data.get('last_name', ''))
    
    def clean(self):
        """
        Validate that GRIM stats total exactly 300 points and name is unique.
        
        IntegerField automatically converts values to int during field cleaning,
        so by the time we get here, values should already be integers.
        """
        cleaned_data = super().clean()
        
        # Check name uniqueness (matching MUD path's validate_name() logic)
        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')
        if first_name and last_name:
            full_name = f"{first_name} {last_name}"
            from typeclasses.characters import Character
            if Character.objects.filter(db_key__iexact=full_name).exists():
                raise forms.ValidationError(
                    f"The name '{full_name}' is already taken. Please choose a different name."
                )
        
        # IntegerField should have already converted these to int
        # If a field failed validation, it won't be in cleaned_data
        grit = cleaned_data.get('grit', 0)
        resonance = cleaned_data.get('resonance', 0)
        intellect = cleaned_data.get('intellect', 0)
        motorics = cleaned_data.get('motorics', 0)
        
        # Sanity check: ensure they're actually integers
        if not all(isinstance(v, int) for v in [grit, resonance, intellect, motorics]):
            # Force conversion if needed (shouldn't happen with IntegerField)
            grit = int(grit) if grit else 0
            resonance = int(resonance) if resonance else 0
            intellect = int(intellect) if intellect else 0
            motorics = int(motorics) if motorics else 0
        
        total = grit + resonance + intellect + motorics
        
        if total != GRIM_TOTAL_POINTS:
            raise forms.ValidationError(
                f"GRIM stats must total exactly {GRIM_TOTAL_POINTS} points. "
                f"Current total: {total} points."
            )
        
        return cleaned_data


class TurnstileAccountForm(EvenniaAccountForm):
    """
    Extends Evennia's AccountForm with Cloudflare Turnstile verification.
    
    Adds a hidden field to capture the Turnstile response token,
    which is validated server-side in the view.
    
    Overrides email field to make it required (critical for password resets).
    """
    
    # Hidden field to store Turnstile response token
    # This is populated by the Turnstile JavaScript widget
    cf_turnstile_response = forms.CharField(
        widget=forms.HiddenInput(),
        required=False,
        error_messages={
            'required': 'CAPTCHA verification is required. Please complete the verification.'
        }
    )
    
    def __init__(self, *args, **kwargs):
        """Override email field to make it required, conditionally require Turnstile."""
        super().__init__(*args, **kwargs)
        # Make email required and update help text
        self.fields['email'].required = True
        self.fields['email'].help_text = "A valid email address. Required for login and password resets."
        self.fields['email'].error_messages = {
            'required': 'Email address is required.',
            'invalid': 'Please enter a valid email address.'
        }
    
    def clean_email(self):
        """
        Validate that the email address is unique (case-insensitive).
        
        This is critical because Evennia's email_login contrib allows users
        to log in with their email address, so duplicate emails could cause
        authentication conflicts.
        """
        from evennia.accounts.models import AccountDB
        
        email = self.cleaned_data.get('email', '').strip()
        
        if not email:
            raise forms.ValidationError("Email address is required.")
        
        # Check for existing account with this email (case-insensitive)
        if AccountDB.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email address already exists. "
                "If you forgot your password, use the password reset link."
            )
        
        return email
    
    def clean_username(self):
        """
        Validate username uniqueness (case-insensitive).
        
        This adds an explicit check in addition to the parent form's validation
        to provide clearer error messages and ensure consistency.
        """
        from evennia.accounts.models import AccountDB
        
        username = self.cleaned_data.get('username', '').strip()
        
        if not username:
            raise forms.ValidationError("Username is required.")
        
        # Check for existing account with this username (case-insensitive)
        if AccountDB.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(
                "An account with this username already exists. "
                "Please choose a different username."
            )
        
        return username
    
    class Meta(EvenniaAccountForm.Meta):
        # Extend parent's fields with Turnstile response
        fields = EvenniaAccountForm.Meta.fields + ('cf_turnstile_response',)

