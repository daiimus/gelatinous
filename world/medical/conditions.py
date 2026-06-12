"""
Medical condition classes for the health system.

This module defines the base MedicalCondition class and specific condition types
like bleeding. Conditions are managed by per-character MedicalScript instances.
"""

import random
import time
from .constants import (
    INJURY_SEVERITY_MULTIPLIERS,
    BLOOD_LOSS_PER_SEVERITY,
    HEALING_EFFECTIVENESS,
    BLEEDING_DAMAGE_THRESHOLDS,
    CONDITION_TRIGGERS,
    BLEEDING_CLOT_HAZARD_PER_MINUTE,
    BLEEDING_TREATED_MULTIPLIER,
    BLEEDING_SELF_CLOT_MAX_SEVERITY,
    BLEEDING_SEVERITY_LABELS,
    PAIN_DECAY_HAZARD_PER_MINUTE,
    INFECTION_IMPROVE_HAZARD_PER_MINUTE,
    INFECTION_WORSEN_HAZARD_PER_MINUTE,
    CONSCIOUSNESS_RECOVERY_HAZARD_PER_MINUTE,
    ELAPSED_CAP_MINUTES,
)
from .clock import elapsed_game_minutes
from .clock import now as clock_now


def hazard_fires(p_per_minute: float, elapsed_minutes: float) -> bool:
    """Sample a per-minute hazard over an elapsed window (spec §4.4).

    ``1 - (1 - p) ** t`` — the probability the event fired at least
    once during ``t`` minutes.  Cadence-independent: six 10s samples
    and one 60s sample have identical distributions.
    """
    if p_per_minute <= 0 or elapsed_minutes <= 0:
        return False
    p = min(0.95, p_per_minute)
    return random.random() < 1 - (1 - p) ** elapsed_minutes


class MedicalCondition:
    """
    Base class for all medical conditions.
    
    Medical conditions are now managed by per-character MedicalScript instances
    instead of individual TICKER_HANDLER subscriptions.
    """
    
    def __init__(self, condition_type, severity, location=None, tick_interval=60):
        self.condition_type = condition_type
        self.severity = severity
        self.max_severity = severity  # Track original severity
        self.location = location
        self.tick_interval = tick_interval  # Not used directly anymore, but kept for compatibility
        self.requires_ticker = True
        self.treated = False
        # CONDITION_CADENCE_SPEC (#501): when this condition last had
        # time applied.  Rates are per real minute; ticks just sample.
        self.last_processed = clock_now()

    def process(self, character, current=None):
        """Apply elapsed time to this condition (spec §4.2).

        The only entry point carriers (medical script today, the
        tactical tier later) should call.  Computes capped elapsed
        minutes since ``last_processed``, hands them to
        ``tick_effect``, and advances the marker.  The cap (§4.3)
        means reloads/crashes never bill more than one extra
        sampling gap.
        """
        if current is None:
            current = clock_now()
        elapsed = min(
            elapsed_game_minutes(self.last_processed, current),
            ELAPSED_CAP_MINUTES,
        )
        self.last_processed = current
        if elapsed > 0:
            self.tick_effect(character, elapsed)
        
    def start_condition(self, character):
        """Begin condition management for character."""
        from world.medical.script import start_medical_script
        from world.combat.debug import get_splattercast
        
        splattercast = get_splattercast()
        
        # Don't add conditions to archived characters (permanently dead)
        # Dying characters can still be resuscitated, so they should keep conditions
        if character.db.archived:
            splattercast.msg(f"CONDITION_START: {character.key} is archived, not adding {self.condition_type}")
            return
        
        if not self.requires_ticker:
            splattercast.msg(f"CONDITION_START: {self.condition_type} for {character.key} doesn't require ticker")
            return
            
        splattercast.msg(f"CONDITION_START: Adding {self.condition_type} severity {self.severity} to {character.key}")
        
        # Ensure character has medical script running
        medical_script = start_medical_script(character)
        if medical_script:
            splattercast.msg(f"CONDITION_START: Medical script active for {character.key}")
        else:
            splattercast.msg(f"CONDITION_START: Failed to start medical script for {character.key}")
            
    def tick_effect(self, character, elapsed_minutes=1.0):
        """Apply ``elapsed_minutes`` of this condition's per-minute
        rates.  Override in subclasses.  The default of 1.0 keeps
        direct callers (tests, legacy) equivalent to one old-style
        60s tick."""
        pass
        
    def should_end(self):
        """Check if condition should be removed. Override in subclasses."""
        return self.severity <= 0
        
    def get_pain_contribution(self):
        """Return pain contribution from this condition. Override in subclasses."""
        return 0  # Base conditions don't contribute pain by default
        
    def get_blood_loss_rate(self):
        """Return blood loss rate from this condition. Override in subclasses."""
        return 0  # Base conditions don't cause blood loss by default

    def disables_organ_at_severity(self):
        """Return ``True`` when this condition's current state fully
        disables organs in its location (#307).

        Default ``False`` — most conditions degrade function gradually
        via :meth:`get_organ_functionality_modifier` rather than
        flipping a binary cutoff.  Subclasses with a clear "tissue is
        no longer working" threshold (e.g. critical infection)
        override.
        """
        return False

    def get_organ_functionality_modifier(self):
        """Return a multiplier in ``[0.0, 1.0]`` applied to organ
        functionality at this condition's location (#307).

        Default ``1.0`` — no effect.  Body-wide conditions (pain,
        blood loss, consciousness suppression) keep the default since
        their impact propagates through other channels (pain →
        consciousness, blood loss → blood_level → consciousness, etc.)
        rather than directly reducing individual organ output.
        Location-bound conditions whose biology actually impairs the
        tissue at that site (infection inflammation) override.
        """
        return 1.0

    @property
    def type(self):
        """Alias for condition_type for backward compatibility."""
        return self.condition_type
        
    def to_dict(self):
        """Serialize condition for persistence."""
        return {
            "condition_type": self.condition_type,
            "severity": self.severity,
            "max_severity": self.max_severity,
            "location": self.location,
            "tick_interval": self.tick_interval,
            "requires_ticker": self.requires_ticker,
            "treated": self.treated,
            "last_processed": self.last_processed,
        }
        
    @classmethod
    def from_dict(cls, data):
        """Deserialize condition from persistence."""
        condition = cls(
            data.get("condition_type", "unknown"),
            data.get("severity", 1),
            data.get("location")
        )
        condition.max_severity = data.get("max_severity", condition.severity)
        condition.tick_interval = data.get("tick_interval", 60)
        condition.requires_ticker = data.get("requires_ticker", True)
        condition.treated = data.get("treated", False)
        condition.last_processed = data.get("last_processed", clock_now())
        return condition
        
    def end_condition(self, character):
        """Clean up when condition ends."""
        # No ticker cleanup needed - script handles lifecycle
        pass
        
    def apply_treatment(self, treatment_quality="adequate"):
        """Apply medical treatment to this condition."""
        self.treated = True
        # Subclasses should override for specific treatment effects


class BleedingCondition(MedicalCondition):
    """Bleeding: blood loss over time, severity-tiered (#507).

    The "layered brakes" model:
    - **bandage** (``apply_treatment``) — reduces severity and slows
      the residual loss to ``BLEEDING_TREATED_MULTIPLIER``; buying
      time, not a fix
    - **wound-care dressing** (stabilization, PR-B) — full stop at
      the location, plus healing
    - **natural clotting** — only severity ≤
      ``BLEEDING_SELF_CLOT_MAX_SEVERITY`` self-resolves (doubled
      hazard when bandaged); arterial-tier wounds bleed until
      someone intervenes

    The blood-loss rate derives from *current* severity at tick
    time — never stored — so clotting/treatment lowering severity
    lowers the rate with it (the stale-rate bug class).
    condition_type is "bleeding"; legacy saves with "minor_bleeding"
    load transparently.
    """

    def __init__(self, severity, location=None):
        super().__init__("bleeding", severity, location, tick_interval=60)
        
    def tick_effect(self, character, elapsed_minutes=1.0):
        """Apply ``elapsed_minutes`` of blood loss; chance to clot."""
        from world.combat.debug import get_splattercast

        splattercast = get_splattercast()

        if not hasattr(character, 'medical_state'):
            return

        medical_state = character.medical_state

        # PR-B (#307): if any damaged organ at this bleeding's location
        # has been stabilized via wound_care, the bleeding is held in
        # place — no further blood loss, no severity drift.  The
        # surgeon still needs to address the underlying wound;
        # stabilization is the "buying time" channel.
        if self._location_stabilized(medical_state):
            return

        # Tourniquet (#509): an applied tourniquet holds the limb
        # completely — no loss, no severity drift, no clotting
        # progress (flow is stopped; nothing to clot).  It is NOT a
        # fix: remove it untreated and this picks right back up.
        if self._location_tourniqueted(medical_state):
            return

        # Per-minute blood loss x elapsed, derived from CURRENT
        # severity (#507: never the stale stored rate).  Bandaged
        # wounds leak at the treated multiplier — slowed, not
        # stopped; the full stop is the stabilization channel.
        rate_per_minute = self.get_blood_loss_rate()
        blood_loss = rate_per_minute * elapsed_minutes

        if blood_loss > 0:
            old_blood = medical_state.blood_level
            medical_state.blood_level = max(0, medical_state.blood_level - blood_loss)
            splattercast.msg(f"BLOOD_LOSS: {character.key} loses {blood_loss:.2f} blood ({old_blood:.1f} -> {medical_state.blood_level:.1f})")

        # Natural clotting — only wounds that plausibly clot (#507):
        # severity ≤ the self-clot cap.  Bandaging promotes clotting
        # (doubled hazard), which also gives treated wounds an
        # endpoint instead of a permanent slow leak.
        if self.severity <= BLEEDING_SELF_CLOT_MAX_SEVERITY:
            clot_hazard = BLEEDING_CLOT_HAZARD_PER_MINUTE
            if self.treated:
                clot_hazard *= 2
            if hazard_fires(clot_hazard, elapsed_minutes):
                self.severity = max(0, self.severity - 1)
                splattercast.msg(f"BLEEDING_HEAL: {character.key} bleeding severity reduced to {self.severity}")

    def _location_tourniqueted(self, medical_state) -> bool:
        """True when any organ at this location carries an applied
        tourniquet flag (#509).  Limb-only by application rules; the
        flag lives organ-level like ``stabilized``."""
        if self.location is None:
            return False
        organs = getattr(medical_state, "organs", None)
        if not organs:
            return False
        for organ in organs.values():
            container = getattr(organ, "container", None)
            if self.location != container:
                continue
            if getattr(organ, "tourniqueted", False):
                return True
        return False

    def _location_stabilized(self, medical_state) -> bool:
        """True when any damaged organ at this condition's location is
        flagged ``stabilized``.

        Stabilization is per-organ but bleeding is per-location;
        this maps the two: a chest BleedingCondition is considered
        stabilized when *any* damaged chest organ has been dressed.
        Multiple damaged organs at one location can be stabilized
        independently — once one is dressed, the location-level
        bleeding stops because the soft-tissue site is sealed.
        """
        if self.location is None:
            return False
        organs = getattr(medical_state, "organs", None)
        if not organs:
            return False
        for organ in organs.values():
            container = getattr(organ, "container", None)
            display = getattr(organ, "display_location", None)
            if self.location not in (container, display):
                continue
            if getattr(organ, "stabilized", False):
                # Only count stabilization on actually-damaged organs;
                # a stabilized-but-undamaged organ shouldn't shield an
                # unrelated bleeding source at the same location.
                if organ.current_hp < organ.max_hp:
                    return True
        return False
            
        # Note: Individual bleeding messages removed - now handled by consolidated messaging in medical script
                
    def should_end(self):
        """Bleeding ends when severity reaches 0."""
        return self.severity <= 0
        
    def get_pain_contribution(self):
        """Return pain contribution from bleeding."""
        # Bleeding causes pain proportional to severity
        return max(1, self.severity // 2)  # Half severity as pain
        
    def get_blood_loss_rate(self):
        """Per-minute blood loss, derived from current severity.

        Bandaged wounds run at the treated multiplier — slowed, not
        stopped (#507 layered brakes).
        """
        rate = BLOOD_LOSS_PER_SEVERITY.get(self.severity, 0.0)
        if self.treated:
            rate = rate * BLEEDING_TREATED_MULTIPLIER
        return rate
        
    def apply_treatment(self, treatment_quality="adequate"):
        """Apply medical treatment to bleeding."""
        super().apply_treatment(treatment_quality)
        
        # Treatment effectiveness
        effectiveness = HEALING_EFFECTIVENESS.get(treatment_quality, 0.5)
        severity_reduction = max(1, int(self.severity * effectiveness))
        
        self.severity = max(0, self.severity - severity_reduction)
        # Residual loss slows via the treated multiplier in
        # get_blood_loss_rate (derived live) — no stored rate to
        # mutate (#507).
        
    @property
    def display_name(self):
        """Severity-tiered label — "arterial bleeding", not "minor"."""
        return BLEEDING_SEVERITY_LABELS.get(
            max(1, min(10, self.severity)), "bleeding",
        )
        
    @classmethod
    def from_dict(cls, data):
        """Deserialize bleeding condition from persistence."""
        condition = cls(
            data.get("severity", 1),
            data.get("location")
        )
        condition.max_severity = data.get("max_severity", condition.severity)
        condition.tick_interval = data.get("tick_interval", 60)
        condition.requires_ticker = data.get("requires_ticker", True)
        condition.treated = data.get("treated", False)
        # Legacy "blood_loss_rate" in old saves is ignored — the rate
        # derives from severity now (#507).
        condition.last_processed = data.get("last_processed", clock_now())
        return condition


class PainCondition(MedicalCondition):
    """Pain condition that affects character abilities."""
    
    def __init__(self, severity, location=None):
        super().__init__("pain", severity, location, tick_interval=120)  # Longer interval
        
    def tick_effect(self, character, elapsed_minutes=1.0):
        """Pain naturally diminishes over time."""
        from world.combat.debug import get_splattercast
        
        splattercast = get_splattercast()
        
        # Natural pain reduction — per-minute hazard over elapsed.
        if hazard_fires(PAIN_DECAY_HAZARD_PER_MINUTE, elapsed_minutes):
            self.severity = max(0, self.severity - 1)
            splattercast.msg(f"PAIN_HEAL: {character.key} pain severity reduced to {self.severity}")
            
        # Note: Individual pain messages removed - now handled by consolidated messaging in medical script
            
    def should_end(self):
        """Pain ends when severity reaches 0."""
        return self.severity <= 0
        
    def get_pain_contribution(self):
        """Return pain contribution from this condition."""
        return self.severity  # Pain conditions contribute their full severity to total pain
        
    def apply_treatment(self, treatment_quality="adequate"):
        """Apply medical treatment to pain."""
        super().apply_treatment(treatment_quality)

        # Pain treatment is very effective
        effectiveness = HEALING_EFFECTIVENESS.get(treatment_quality, 0.5)
        severity_reduction = max(1, int(self.severity * effectiveness * 1.5))  # Extra effective

        self.severity = max(0, self.severity - severity_reduction)

    @classmethod
    def from_dict(cls, data):
        """Deserialize a pain condition from persistence.

        Subclass override — same signature mismatch issue as
        ``InfectionCondition.from_dict``.
        """
        condition = cls(
            data.get("severity", 1),
            data.get("location"),
        )
        condition.max_severity = data.get("max_severity", condition.severity)
        condition.tick_interval = data.get("tick_interval", 120)
        condition.requires_ticker = data.get("requires_ticker", True)
        condition.treated = data.get("treated", False)
        condition.last_processed = data.get("last_processed", clock_now())
        return condition


class InfectionCondition(MedicalCondition):
    """Infection condition that can worsen over time if untreated."""
    
    def __init__(self, severity, location=None):
        super().__init__("infection", severity, location, tick_interval=300)  # 5 minute interval
        self.base_progression_chance = 1.0  # Base % chance to worsen per 12s tick (adjustable by environment)
        self.last_progression_check = 0  # Track time for proper progression timing
        self.environmental_modifier = 1.0  # Multiplier for environmental conditions (sewers, etc.)
        
    def tick_effect(self, character, elapsed_minutes=1.0):
        """Infection can worsen if untreated, or improve if treated.

        #501 §5 RESTORATION: the per-tick numbers had drifted 5x from
        their design (authored against the old 12s tick).  These
        hazards restore the documented pacing — treated infection
        "improves every ~5 minutes", untreated follows the
        "realistic ~20min progression", scaled by the environmental
        modifier (the future sewers-and-neglect lever).
        """
        from world.combat.debug import get_splattercast

        splattercast = get_splattercast()

        if self.treated:
            if hazard_fires(INFECTION_IMPROVE_HAZARD_PER_MINUTE, elapsed_minutes):
                self.severity = max(0, self.severity - 1)
                splattercast.msg(f"INFECTION_HEAL: {character.key} infection severity reduced to {self.severity}")
        else:
            worsen_hazard = INFECTION_WORSEN_HAZARD_PER_MINUTE * self.environmental_modifier
            if hazard_fires(worsen_hazard, elapsed_minutes):
                self.severity = min(10, self.severity + 1)  # Cap at 10
                splattercast.msg(f"INFECTION_WORSEN: {character.key} infection severity increased to {self.severity} (env modifier: {self.environmental_modifier}x)")
    
    def set_environmental_modifier(self, modifier):
        """Set environmental infection risk modifier (e.g., 3.0 for sewers, 0.5 for sterile conditions)"""
        self.environmental_modifier = max(0.1, modifier)  # Minimum 0.1x, no maximum
                
        # Note: Infection effect messages removed - now handled by consolidated messaging in medical script
            
    def should_end(self):
        """Infection ends when severity reaches 0."""
        return self.severity <= 0

    @classmethod
    def from_dict(cls, data):
        """Deserialize an infection condition from persistence.

        Overrides ``MedicalCondition.from_dict`` because the base
        signature passes ``condition_type`` as the first positional,
        but ``InfectionCondition.__init__`` takes ``(severity,
        location)``.  Matches the pattern ``BleedingCondition`` uses.
        """
        condition = cls(
            data.get("severity", 1),
            data.get("location"),
        )
        condition.max_severity = data.get("max_severity", condition.severity)
        condition.tick_interval = data.get("tick_interval", 300)
        condition.requires_ticker = data.get("requires_ticker", True)
        condition.treated = data.get("treated", False)
        condition.last_processed = data.get("last_processed", clock_now())
        return condition

    def disables_organ_at_severity(self):
        """Critical infection (severity ≥ 10) disables organs at the
        affected location entirely — inflammation has overwhelmed
        the tissue (#307).
        """
        return self.severity >= 10

    def get_organ_functionality_modifier(self):
        """Inflammation progressively impairs organ function (#307).

        Severity ladder, matching the 1-10 scale used elsewhere:

        * 0:   ``1.0`` — cleared, awaiting removal
        * 1-3: ``0.9`` — minor; small functional drag
        * 4-6: ``0.75`` — moderate; noticeable impairment
        * 7-9: ``0.5`` — severe; organ at half-function
        * 10+: ``0.0`` — handled via :meth:`disables_organ_at_severity`

        Numbers are scaffolding — balance pass owed (proof-of-concept
        per the user; spec line 1418 also defers exact mechanics).
        """
        if self.severity <= 0:
            return 1.0
        if self.severity <= 3:
            return 0.9
        if self.severity <= 6:
            return 0.75
        if self.severity <= 9:
            return 0.5
        return 0.0  # severity 10+ — disabling check catches it too

    def apply_treatment(self, treatment_quality="adequate"):
        """Apply medical treatment to infection."""
        super().apply_treatment(treatment_quality)
        
        # Treatment is crucial for infections
        effectiveness = HEALING_EFFECTIVENESS.get(treatment_quality, 0.5)
        severity_reduction = max(1, int(self.severity * effectiveness))
        
        self.severity = max(0, self.severity - severity_reduction)
        
        # Stop progression when treated
        self.base_progression_chance = 0


def create_condition_from_damage(damage_amount, damage_type, location=None):
    """
    Create appropriate medical conditions based on damage dealt.
    
    Args:
        damage_amount: Amount of damage dealt
        damage_type: Type of damage (bullet, blade, blunt, etc.)
        location: Body location affected
        
    Returns:
        list: List of MedicalCondition instances
    """
    conditions = []
    
    # Always create bleeding for significant damage
    threshold = BLEEDING_DAMAGE_THRESHOLDS.get('minor', 5)
    
    if damage_amount >= threshold:
        bleeding_severity = min(10, max(1, damage_amount // 3))
        conditions.append(BleedingCondition(bleeding_severity, location))
    
    # Add pain for any damage
    if damage_amount > 0:
        pain_severity = min(8, max(1, damage_amount // 2))
        conditions.append(PainCondition(pain_severity, location))
    
    # Add infection risk for penetrating/dirty wounds.  #495: the old
    # gate listed 'blade'/'pierce' — ghost types no caller ever sends
    # (the real vocabulary is cut/stab/laceration/blunt/blast/bullet)
    # — so only bullets could infect and the antiseptic loop was dead.
    #
    # INTERIM MODEL: flat chance on heavy penetrating hits.  The
    # designed future model is circumstantial, not random-per-hit:
    # poor wound treatment, environment (open wounds in sewers),
    # and retained foreign bodies (an untreated bullet still in the
    # wound) should drive infection instead.
    if damage_type in ['bullet', 'cut', 'stab', 'laceration'] and damage_amount >= 8:
        if random.randint(1, 100) <= 25:  # 25% chance
            infection_severity = random.randint(1, 3)
            conditions.append(InfectionCondition(infection_severity, location))
    
    return conditions


class ConsciousnessSuppressionCondition(MedicalCondition):
    """
    Condition that directly suppresses consciousness levels.
    
    This represents the effects of drugs, knockout trauma, sedatives, 
    anesthesia, or other factors that directly impair consciousness
    without necessarily causing physical damage.
    """
    
    def __init__(self, severity, location=None, suppression_type="knockout"):
        super().__init__("consciousness_suppression", severity, location, tick_interval=180)  # 3 minute interval
        self.suppression_type = suppression_type  # "knockout", "sedative", "anesthesia", "trauma"
        self.consciousness_penalty = min(1.0, severity * 0.15)  # Up to 1.5 consciousness reduction at severity 10
        
    def tick_effect(self, character, elapsed_minutes=1.0):
        """Consciousness suppression naturally diminishes over time."""
        from world.combat.debug import get_splattercast
        
        splattercast = get_splattercast()
        
        # Natural recovery — per-minute hazard by suppression type.
        recovery_hazard = CONSCIOUSNESS_RECOVERY_HAZARD_PER_MINUTE.get(
            self.suppression_type, 0.20,
        )
        
        if hazard_fires(recovery_hazard, elapsed_minutes):
            self.severity = max(0, self.severity - 1)
            # Recalculate consciousness penalty
            self.consciousness_penalty = min(1.0, self.severity * 0.15)
            splattercast.msg(f"CONSCIOUSNESS_RECOVERY: {character.key} {self.suppression_type} severity reduced to {self.severity} (penalty: {self.consciousness_penalty:.2f})")
            
    def should_end(self):
        """Consciousness suppression ends when severity reaches 0."""
        return self.severity <= 0
        
    def get_consciousness_penalty(self):
        """Return direct consciousness penalty from this condition."""
        return self.consciousness_penalty
        
    def apply_treatment(self, treatment_quality="adequate"):
        """Apply medical treatment to consciousness suppression."""
        super().apply_treatment(treatment_quality)
        
        # Medical treatment can help with some types of suppression
        if self.suppression_type in ["sedative", "anesthesia"]:
            effectiveness = HEALING_EFFECTIVENESS.get(treatment_quality, 0.5)
            severity_reduction = max(1, int(self.severity * effectiveness))
            self.severity = max(0, self.severity - severity_reduction)
            self.consciousness_penalty = min(1.0, self.severity * 0.15)
        
    def to_dict(self):
        """Serialize condition for persistence."""
        data = super().to_dict()
        data["suppression_type"] = self.suppression_type
        data["consciousness_penalty"] = self.consciousness_penalty
        return data
        
    @classmethod
    def from_dict(cls, data):
        """Deserialize condition from persistence."""
        condition = cls(
            data.get("severity", 1),
            data.get("location"),
            data.get("suppression_type", "knockout")
        )
        condition.consciousness_penalty = data.get("consciousness_penalty", 0.15)
        condition.max_severity = data.get("max_severity", condition.severity)
        condition.tick_interval = data.get("tick_interval", 180)
        condition.requires_ticker = data.get("requires_ticker", True)
        condition.treated = data.get("treated", False)
        condition.last_processed = data.get("last_processed", clock_now())
        return condition


class AddictionCondition(MedicalCondition):
    """Flavor-first substance addiction (issue #485).

    Added by ``apply_substance`` when a consumer's lifetime dose count
    crosses the substance's addiction threshold.  Dormant while the
    habit is fed; once ``craving_after`` seconds pass without a dose:

    * each vitals refresh sees ``get_pain_contribution() == 1`` — a
      mild ache, the "and mild pain" half of the flavor-first design;
    * the medical-script tick surfaces craving prose every few ticks.

    Both clear automatically the moment the consumer doses again
    (``record_dose``).  The condition itself never ends on its own —
    treatment/recovery is future work — which means an addicted
    character keeps a medical script ticking permanently.  That's a
    deliberate cost: addiction is a PC-facing mechanic, and the
    dormant-path tick is a couple of time comparisons.

    Severity stays at 1 in v1; escalation (withdrawal stages) is the
    designed growth path once the flavor pass is tuned.
    """

    def __init__(self, substance_id, prose_key="generic",
                 craving_after=7200, severity=1, location=None):
        super().__init__("addiction", severity, location, tick_interval=60)
        self.substance_id = substance_id
        self.prose_key = prose_key
        self.craving_after = craving_after
        self.last_dose_time = time.time()
        self._last_prose_time = 0.0  # transient; not persisted

    # -- state ---------------------------------------------------

    def is_craving(self):
        """True once the consumer is overdue for a dose."""
        last = self.last_dose_time or 0
        return (time.time() - last) >= self.craving_after

    def record_dose(self):
        """A dose landed — cravings (and their ache) reset."""
        self.last_dose_time = time.time()
        self._last_prose_time = 0.0

    # -- condition contract ---------------------------------------

    def should_end(self):
        # Persistent until a future treatment system provides an exit.
        return False

    def get_pain_contribution(self):
        return 1 if self.is_craving() else 0

    def tick_effect(self, character, elapsed_minutes=1.0):
        if not self.is_craving():
            self._last_prose_time = 0.0
            return
        # Surface prose immediately on becoming overdue, then every
        # ~5 minutes of real time — pressure, not spam.  (#501:
        # converted from tick-counting to elapsed time.)
        current = clock_now()
        last = getattr(self, "_last_prose_time", 0.0)
        if current - last >= 300 or last == 0.0:
            self._last_prose_time = current
            from world.substances.registry import pick_craving_line
            line = pick_craving_line(self.prose_key)
            if line and hasattr(character, "msg"):
                character.msg(f"|x{line}|n")

    # -- persistence ----------------------------------------------

    def to_dict(self):
        data = super().to_dict()
        data.update({
            "substance_id": self.substance_id,
            "prose_key": self.prose_key,
            "craving_after": self.craving_after,
            "last_dose_time": self.last_dose_time,
        })
        return data

    @classmethod
    def from_dict(cls, data):
        condition = cls(
            data.get("substance_id", "unknown"),
            prose_key=data.get("prose_key", "generic"),
            craving_after=data.get("craving_after", 7200),
            severity=data.get("severity", 1),
            location=data.get("location"),
        )
        condition.max_severity = data.get("max_severity", condition.severity)
        condition.treated = data.get("treated", False)
        condition.last_dose_time = data.get("last_dose_time", time.time())
        condition.last_processed = data.get("last_processed", clock_now())
        return condition


def deserialize_condition(condition_dict):
    """Reconstruct a ``MedicalCondition`` from its ``to_dict`` form.

    Centralises the condition-type → class dispatch that
    ``MedicalState.from_dict`` used to do inline so any persistence
    pipeline (organ snapshot, harvest item, install pipeline, etc.)
    can deserialize a condition without reimplementing the factory.

    Args:
        condition_dict: Dict produced by ``MedicalCondition.to_dict``
            (or a subclass's override).

    Returns:
        A condition instance of the appropriate subclass.  Unknown
        condition types fall back to the ``MedicalCondition`` base
        class so the data round-trips without crashing.
    """
    condition_type = condition_dict.get("condition_type", "unknown")
    if condition_type in ("bleeding", "minor_bleeding"):  # legacy alias
        return BleedingCondition.from_dict(condition_dict)
    if condition_type == "pain":
        return PainCondition.from_dict(condition_dict)
    if condition_type == "infection":
        return InfectionCondition.from_dict(condition_dict)
    if condition_type == "addiction":
        return AddictionCondition.from_dict(condition_dict)
    if condition_type == "consciousness_suppression":
        return ConsciousnessSuppressionCondition.from_dict(condition_dict)
    return MedicalCondition.from_dict(condition_dict)


def remove_condition_by_type(character, condition_type):
    """
    Remove all conditions of a specific type from character.
    
    Args:
        character: Character to remove conditions from
        condition_type: Type of condition to remove
    """
    if not hasattr(character, 'medical_state'):
        return
        
    medical_state = character.medical_state
    conditions_to_remove = [c for c in medical_state.conditions if c.condition_type == condition_type]
    
    for condition in conditions_to_remove:
        medical_state.conditions.remove(condition)
        condition.end_condition(character)


def set_infection_environmental_risk(character, modifier, reason="environmental conditions"):
    """
    Modify infection progression risk for environmental conditions.
    
    Args:
        character: Character to modify infection risk for
        modifier: Risk multiplier (1.0 = normal, 3.0 = high risk like sewers, 0.5 = low risk like sterile)
        reason: Description for debug logging
        
    Examples:
        set_infection_environmental_risk(character, 3.0, "walking through sewers")
        set_infection_environmental_risk(character, 0.3, "sterile medical facility")
        set_infection_environmental_risk(character, 5.0, "toxic waste exposure")
    """
    if not hasattr(character, 'medical_state'):
        return
        
    from world.combat.debug import get_splattercast
    
    medical_state = character.medical_state
    infection_conditions = [c for c in medical_state.conditions if c.condition_type == "infection"]
    
    if infection_conditions:
        splattercast = get_splattercast()
        for condition in infection_conditions:
            condition.set_environmental_modifier(modifier)
        
        splattercast.msg(f"INFECTION_ENV_RISK: {character.key} infection risk set to {modifier}x due to {reason}")
    # If no infections, the modifier would apply to future infections created in this environment
