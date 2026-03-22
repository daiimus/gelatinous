"""
Django views for Gelatinous Monster character creation.

Extends Evennia's default CharacterCreateView to add GRIM stats and archiving.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.text import slugify
from django.views.generic import View
from evennia.web.website.views.characters import (
    CharacterCreateView as EvenniaCharacterCreateView,
    CharacterListView as EvenniaCharacterListView,
    CharacterDetailView as EvenniaCharacterDetailView,
    CharacterUpdateView as EvenniaCharacterUpdateView,
    CharacterMixin
)

# Import forms module (Evennia pattern)
from web.website import forms


class CharacterCreateView(EvenniaCharacterCreateView):
    """
    Extended character creation view with GRIM stats and name structure.
    
    Two modes:
    1. Respawn (account.db.last_character exists): Template selection + flash clone
    2. First character: Manual stat allocation form
    """
    
    # Use our extended form with GRIM fields (Evennia pattern: forms.ClassName)
    form_class = forms.CharacterForm
    
    def get(self, request, *args, **kwargs):
        """Determine which character creation flow to show."""
        account = request.user
        
        # Check for respawn scenario FIRST (before max character check)
        # This allows respawn even when at 0 active characters
        if account.db.last_character:
            old_char = account.db.last_character
            
            # Validate that last_character is actually dead/archived and eligible for respawn
            # If they're alive or missing archived attribute (legacy), clear last_character
            try:
                # Check if character still exists and is accessible
                _ = old_char.key
                
                # Check if character is actually archived/dead (default False for legacy)
                is_archived = old_char.db.archived or False
                
                # If not archived, they're alive - clear last_character and proceed to normal creation
                if not is_archived:
                    account.db.last_character = None
                else:
                    # Character is properly archived, show respawn interface
                    return self.show_respawn_interface(request, account)
                    
            except (AttributeError, TypeError):
                # last_character reference is broken/invalid, clear it
                account.db.last_character = None
        
        # Check if account has reached max character limit
        active_characters = []
        for char in account.characters:
            # Defensive check - ensure character is accessible
            if not char:
                continue
            archived = char.db.archived or False
            if not archived:
                active_characters.append(char)
        
        from django.conf import settings
        max_chars = settings.MAX_NR_CHARACTERS
        
        if max_chars is not None and len(active_characters) >= max_chars:
            from evennia.utils.ansi import strip_ansi
            error_msg = strip_ansi(
                f"You already have the maximum of {max_chars} active character(s). "
                f"Archive an existing sleeve before creating a new one."
            )
            messages.error(request, error_msg)
            return HttpResponseRedirect(reverse_lazy('character-manage-list'))
        
        # Debug: Add info to context to display on page
        debug_info = {
            'account_key': account.key if hasattr(account, 'key') else str(account),
            'has_db': True,
            'last_character': None,
        }
        
        last_char = account.db.last_character
        debug_info['last_character'] = last_char.key if last_char else 'None'
        
        # First character - show manual stat allocation form with debug info
        response = super().get(request, *args, **kwargs)
        # Try to inject debug info into context
        if hasattr(response, 'context_data'):
            response.context_data['debug_info'] = debug_info
        return response
    
    def show_respawn_interface(self, request, account):
        """Display template selection + flash clone options for respawn."""
        from commands.charcreate import generate_random_template
        
        # Generate 3 random templates
        templates = [generate_random_template() for _ in range(3)]
        
        # Get old character for flash clone option
        old_character = account.db.last_character
        
        # Validate old_character exists and is accessible
        if old_character:
            try:
                # Test if we can access the character (it might be deleted/invalid)
                _ = old_character.key
                
                # GRIM stats and sex are AttributeProperty with autocreate=True,
                # so they always exist on Character instances - no need to check/set.
                
                # Ensure archived attribute exists (db attribute, not AttributeProperty)
                if old_character.db.archived is None:
                    old_character.db.archived = False  # Legacy characters were active when they died
                    
            except (AttributeError, TypeError, Exception) as e:
                # Old character reference is invalid/deleted - clear it
                import logging
                logger = logging.getLogger('evennia')
                logger.warning(f"Invalid last_character for {account.key}: {e}")
                account.db.last_character = None
                old_character = None
        
        context = {
            'templates': templates,
            'old_character': old_character,
        }
        
        # Persist templates in Django session so POST receives the same ones
        # Templates are dicts of basic types (str, int), so JSON-serializable
        request.session['respawn_templates'] = templates
        
        return render(request, 'website/character_respawn_create.html', context)
    
    def post(self, request, *args, **kwargs):
        """Handle both respawn and first character creation."""
        account = request.user
        
        # Check if this is a respawn submission
        if 'sleeve_choice' in request.POST:
            return self.handle_respawn_submission(request, account)
        else:
            # First character form submission
            return super().post(request, *args, **kwargs)
    
    def handle_respawn_submission(self, request, account):
        """Process respawn template/flash clone selection."""
        from commands.charcreate import create_flash_clone, create_character_from_template
        
        choice = request.POST.get('sleeve_choice')
        
        try:
            if choice == 'flash_clone':
                # Create flash clone
                old_character = account.db.last_character
                if not old_character:
                    messages.error(request, "Flash clone source not found.")
                    return HttpResponseRedirect(self.success_url)
                
                # Flash clone inherits sex from old character automatically
                # No need to override - create_flash_clone() handles inheritance
                character = create_flash_clone(account, old_character)
                
                messages.success(
                    request,
                    f"Flash clone '{character.name}' decanted successfully! "
                    f"Consciousness transfer complete."
                )
                
            else:
                # Create from template
                # Retrieve templates from session (persisted during GET)
                templates = request.session.get('respawn_templates')
                if not templates:
                    messages.error(request, "Session expired. Please try again.")
                    return HttpResponseRedirect(reverse_lazy('character-create'))
                
                template_idx = int(choice.split('_')[1])
                if template_idx >= len(templates):
                    messages.error(request, "Invalid template selection.")
                    return HttpResponseRedirect(self.success_url)
                
                template = templates[template_idx]
                # Use the template's pre-assigned sex (not user selection)
                template_sex = template.get('sex', 'ambiguous')
                character = create_character_from_template(account, template, template_sex)
                
                messages.success(
                    request,
                    f"Character '{character.name}' decanted successfully! "
                    f"GRIM: Grit {character.grit}, Resonance {character.resonance}, "
                    f"Intellect {character.intellect}, Motorics {character.motorics}"
                )
            
            # WEB-CREATED CHARACTERS: Make invisible until puppeted
            # Set location to None (standard Evennia unpuppet behavior)
            # This makes them invisible in room until first puppet/login
            # Save spawn location for restoration during at_pre_puppet
            from evennia.objects.models import ObjectDB
            from django.conf import settings as django_settings
            spawn_location = ObjectDB.objects.get_id(django_settings.START_LOCATION)
            if not spawn_location:
                spawn_location = character.location  # Fallback to creation location
            character.db.prelogout_location = spawn_location
            character.location = None
            
            # Debug logging
            from evennia.comms.models import ChannelDB
            try:
                splattercast = ChannelDB.objects.get_channel("Splattercast")
                splattercast.msg(
                    f"WEB_CHAR_CREATE: {character.key} created via web (respawn), "
                    f"location set to None for invisibility. "
                    f"Will be restored to {character.db.prelogout_location.key} on telnet login."
                )
            except Exception:
                pass
            
            # Clear last_character after successful respawn
            # (archive_character() will set it again when this character is archived)
            account.db.last_character = None
            
            # Clean up session data
            request.session.pop('respawn_templates', None)
            
            return HttpResponseRedirect(self.success_url)
            
        except Exception:
            import logging
            logging.getLogger('evennia').exception(
                "Sleeve decantation failed for account %s", account.key
            )
            messages.error(
                request,
                "Sleeve decantation failed due to an internal error. "
                "Please try again or contact staff."
            )
            return HttpResponseRedirect(self.success_url)
    
    def form_valid(self, form):
        """
        Handle character creation with GRIM stats and name structure.
        
        Follows Evennia's pattern: extract form data, call typeclass.create(),
        set additional attributes, return HttpResponseRedirect.
        """
        account = self.request.user
        
        # Check character slot availability (excluding archived characters)
        # Note: Account.check_available_slots() override in typeclasses/accounts.py
        # handles the primary slot checking. This view-level check provides additional
        # user-friendly validation before the character creation attempt.
        active_characters = []
        for char in account.characters:
            # Access archived status via db.archived (returns None if unset)
            archived = char.db.archived or False
            if not archived:
                active_characters.append(char)
        
        from django.conf import settings
        max_chars = settings.MAX_NR_CHARACTERS
        
        if max_chars is not None and len(active_characters) >= max_chars:
            from evennia.utils.ansi import strip_ansi
            error_msg = strip_ansi(f"You may only have a maximum of {max_chars} active character(s). Archive an existing sleeve to create a new one.")
            messages.error(self.request, error_msg)
            return self.form_invalid(form)
        
        # Extract name components and build full name
        first_name = form.cleaned_data['first_name']
        last_name = form.cleaned_data['last_name']
        charname = f"{first_name} {last_name}"
        
        # Extract other form data
        description = form.cleaned_data.get('desc', '')
        sex = form.cleaned_data['sex']
        
        # Get locations: create at Limbo (#2) staging area, spawn at START_LOCATION
        from django.conf import settings
        from evennia.objects.models import ObjectDB
        from evennia import search_object
        
        # Creation location: Limbo (#2) as safe staging area
        try:
            creation_location = search_object("#2")[0]
        except (IndexError, AttributeError):
            creation_location = None
        
        # Spawn location: where the character will appear on first puppet
        spawn_location = ObjectDB.objects.get_id(settings.START_LOCATION)
        if not spawn_location:
            spawn_location = creation_location  # Fallback to Limbo
        
        # Create character using typeclass.create() - returns (character, errors)
        character, errors = self.typeclass.create(
            charname, account, description=description, location=creation_location, home=creation_location
        )
        
        if errors:
            # Strip Evennia color codes from error messages before displaying on web
            from evennia.utils.ansi import strip_ansi
            clean_errors = [strip_ansi(str(err)) for err in errors]
            for err in clean_errors:
                messages.error(self.request, err)
            return self.form_invalid(form)
        
        if character:
            # Set GRIM stats (using AttributeProperty) - ensure integers
            character.grit = int(form.cleaned_data['grit'])
            character.resonance = int(form.cleaned_data['resonance'])
            character.intellect = int(form.cleaned_data['intellect'])
            character.motorics = int(form.cleaned_data['motorics'])
            
            # Set sex (using AttributeProperty)
            character.sex = sex
            
            # Set Stack/clone tracking (matching telnet charcreate.py)
            import uuid
            import time
            character.db.stack_id = str(uuid.uuid4())
            character.db.original_creation = time.time()
            character.db.current_sleeve_birth = time.time()
            character.db.archived = False
            # death_count defaults to 1 via AttributeProperty in Character class
            
            # WEB-CREATED CHARACTERS: Make invisible until puppeted
            # Set location to None (standard Evennia unpuppet behavior)
            # This makes them invisible in room until first puppet/login
            # Save spawn location for restoration during at_pre_puppet
            character.db.prelogout_location = spawn_location
            character.location = None
            
            # Debug logging
            from evennia.comms.models import ChannelDB
            try:
                splattercast = ChannelDB.objects.get_channel("Splattercast")
                splattercast.msg(
                    f"WEB_CHAR_CREATE: {character.key} created via web (first-time), "
                    f"location set to None for invisibility. "
                    f"Will be restored to {character.db.prelogout_location.key} on telnet login."
                )
            except Exception:
                pass
            
            messages.success(
                self.request,
                f"Character '{character.name}' decanted successfully! "
                f"GRIM: Grit {character.grit}, Resonance {character.resonance}, "
                f"Intellect {character.intellect}, Motorics {character.motorics}"
            )
            return HttpResponseRedirect(self.success_url)
        else:
            messages.error(self.request, "Character creation failed.")
            return self.form_invalid(form)


class CharacterArchiveView(LoginRequiredMixin, CharacterMixin, View):
    """
    Archive a character instead of deleting it.
    
    Sets character.db.archived = True rather than deleting from database.
    This preserves Stack tracking and death history.
    """
    
    # -- Django constructs --
    template_name = "website/character_confirm_archive.html"
    success_url = reverse_lazy("character-manage")
    
    # -- Evennia constructs --
    access_type = "delete"  # Use delete permission (user must own character)
    
    def get(self, request, *args, **kwargs):
        """Display the archive confirmation page."""
        # Get the character using pk from URL
        pk = kwargs.get('pk')
        slug_param = kwargs.get('slug')
        
        # Get character from database
        try:
            character = self.typeclass.objects.get(pk=pk)
            
            # Verify slug matches
            if slugify(character.name) != slug_param:
                raise Http404("Character not found")
            
            # Verify ownership (user must be in character's account's characters)
            if character not in request.user.characters:
                raise PermissionDenied("You don't have permission to archive this character")
                
        except self.typeclass.DoesNotExist:
            raise Http404("Character not found")
        
        # Render confirmation template
        return render(request, self.template_name, {'object': character})
    
    def post(self, request, *args, **kwargs):
        """Handle the archive action."""
        # Get the character using pk from URL
        pk = kwargs.get('pk')
        slug_param = kwargs.get('slug')
        
        # Get character (same validation as GET)
        try:
            character = self.typeclass.objects.get(pk=pk)
            
            # Verify slug matches
            if slugify(character.name) != slug_param:
                raise Http404("Character not found")
            
            # Verify ownership
            if character not in request.user.characters:
                raise PermissionDenied("You don't have permission to archive this character")
                
        except self.typeclass.DoesNotExist:
            raise Http404("Character not found")
        
        # Archive the character (handles archiving + disconnecting active sessions)
        character.archive_character(reason="manual")
        
        # FIX: character.account is None when accessed via web
        # Manually set last_character using request.user (which is the Evennia Account)
        account = request.user
        account.db.last_character = character
        
        # Success message using character terminology
        messages.success(
            request,
            f"Sleeve '{character.name}' has been archived. "
            f"Stack ID preserved for future respawn."
        )
        
        # Redirect to character management page
        return HttpResponseRedirect(self.success_url)


class StaffCharacterListView(EvenniaCharacterListView):
    """
    Staff-only character list view.
    
    Restricts access to the character list to staff members only.
    Regular players attempting to access this page will be redirected.
    """
    
    def dispatch(self, request, *args, **kwargs):
        """Check if user is staff before allowing access."""
        if not request.user.is_staff:
            messages.error(request, "You must be a staff member to access the character list.")
            return HttpResponseRedirect(reverse_lazy("index"))
        return super().dispatch(request, *args, **kwargs)


class OwnerOnlyCharacterDetailView(EvenniaCharacterDetailView):
    """
    Owner-only character detail view.
    
    Only allows viewing character details if you own the character.
    Staff members can view any character.
    """
    
    template_name = "website/character_detail.html"
    
    def get_queryset(self):
        """
        Override to only return characters owned by the current user.
        Staff can view all characters.
        """
        account = self.request.user
        
        # Staff can view all characters
        if account.is_staff:
            return super().get_queryset()
        
        # Regular users can only view their own characters
        ids = [getattr(x, "id") for x in account.characters if x]
        return self.typeclass.objects.filter(id__in=ids)
    
    def get_context_data(self, **kwargs):
        """Add GRIM stat descriptors to context."""
        context = super().get_context_data(**kwargs)
        character = self.object
        
        # Import the descriptor function
        from commands.CmdCharacter import get_stat_descriptor
        
        # Get stat descriptors (AttributeProperty with autocreate=True, always exist)
        grit = character.grit
        resonance = character.resonance
        intellect = character.intellect
        motorics = character.motorics
        
        context['grit_descriptor'] = get_stat_descriptor('grit', grit)
        context['resonance_descriptor'] = get_stat_descriptor('resonance', resonance)
        context['intellect_descriptor'] = get_stat_descriptor('intellect', intellect)
        context['motorics_descriptor'] = get_stat_descriptor('motorics', motorics)
        
        return context
    
    def dispatch(self, request, *args, **kwargs):
        """Check ownership before allowing access."""
        # Get the character being requested
        try:
            char = self.get_object()
            account = request.user
            
            # Staff can view any character
            if account.is_staff:
                return super().dispatch(request, *args, **kwargs)
            
            # Check if the character belongs to this account
            if char not in account.characters:
                messages.error(request, "You can only view your own characters.")
                return HttpResponseRedirect(reverse_lazy("character-manage"))
        except Exception:
            messages.error(request, "Character not found.")
            return HttpResponseRedirect(reverse_lazy("index"))
        
        return super().dispatch(request, *args, **kwargs)


class OwnerOnlyCharacterUpdateView(EvenniaCharacterUpdateView):
    """
    Owner-only character update view.
    
    Only allows editing character details if you own the character.
    Staff members can edit any character.
    """
    
    def get_queryset(self):
        """
        Override to only return characters owned by the current user.
        Staff can edit all characters.
        """
        account = self.request.user
        
        # Staff can edit all characters
        if account.is_staff:
            from django.db.models.functions import Lower
            return self.typeclass.objects.all().order_by(Lower("db_key"))
        
        # Regular users can only edit their own characters
        ids = [getattr(x, "id") for x in account.characters if x]
        return self.typeclass.objects.filter(id__in=ids)
    
    def dispatch(self, request, *args, **kwargs):
        """Check ownership before allowing access."""
        # Get the character being requested
        try:
            char = self.get_object()
            account = request.user
            
            # Staff can edit any character
            if account.is_staff:
                return super().dispatch(request, *args, **kwargs)
            
            # Check if the character belongs to this account
            if char not in account.characters:
                messages.error(request, "You can only edit your own characters.")
                return HttpResponseRedirect(reverse_lazy("character-manage"))
        except Exception:
            messages.error(request, "Character not found.")
            return HttpResponseRedirect(reverse_lazy("index"))
        
        return super().dispatch(request, *args, **kwargs)
