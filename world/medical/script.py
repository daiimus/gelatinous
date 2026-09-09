"""
Medical condition script for characters.

This script manages all medical conditions for a single character,
ticking them at regular intervals and cleaning up when no conditions remain.
"""

from evennia import DefaultScript
from world.combat.debug import get_splattercast
from world.medical.constants import MEDICAL_TICK_INTERVAL


# ---------------------------------------------------------------------
# Healing tick helpers (#307, PR-C)
# ---------------------------------------------------------------------


def _healing_organs(medical_state) -> list:
    """Every organ this tick would actually restore HP to.

    ONE predicate, because there used to be two and they disagreed
    (#2495). `_has_healing_work` kept the script alive on
    `dressing_rate > 0`; `_process_healing` did the work only when
    `_hp_per_tick(rate) > 0`. With `WOUND_HEALING_DIVISOR = 5` and
    `WOUND_HEALING_FLOOR_HP_PER_TICK = 0`, a rate of 1-4 gives
    `4 // 5 = 0` — so an organ in that band satisfied the keep-alive
    test and failed the do-the-work test, leaving a medical script that
    ticked forever, healed nothing, and never deleted itself.

    No shipped item produces such a rate today; the lowest
    `wound_healing` value in the game is exactly 5 and the cliff is
    below 5, so the margin is one step.

    Note which way this resolves: a rate of 1-4 now DRESSES a wound
    without healing it, and the script stops rather than idling. If
    weak dressings should inch a wound back instead,
    `WOUND_HEALING_FLOOR_HP_PER_TICK` is the lever — that is a balance
    decision, and this is a correctness fix.
    """
    out = []
    organs = getattr(medical_state, "organs", None) or {}
    for organ in organs.values():
        if not getattr(organ, "stabilized", False):
            continue
        rate = getattr(organ, "dressing_rate", 0) or 0
        if rate <= 0:
            continue
        if organ.current_hp >= organ.max_hp:
            continue
        if _hp_per_tick(rate) <= 0:
            continue
        out.append(organ)
    return out


def _has_healing_work(medical_state) -> bool:
    """True when this tick would restore HP to something.

    Used by ``MedicalScript`` to decide whether to keep ticking after
    all active conditions are gone — a freshly-dressed wound on an
    otherwise-healthy character needs the tick to fire even with
    zero conditions on the medical state.
    """
    return bool(_healing_organs(medical_state))


def _hp_per_tick(dressing_rate: int) -> int:
    """Calculate HP restored per tick for a given dressing rate.

    Integer math: ``rating // DIVISOR``, then floored at
    ``WOUND_HEALING_FLOOR_HP_PER_TICK`` so weak dressings still
    inch wounds back when the floor is non-zero (default 0 keeps
    them stable-but-not-healing).
    """
    from world.medical.constants import (
        WOUND_HEALING_DIVISOR,
        WOUND_HEALING_FLOOR_HP_PER_TICK,
    )
    base = int(dressing_rate) // max(1, WOUND_HEALING_DIVISOR)
    return max(base, WOUND_HEALING_FLOOR_HP_PER_TICK)


def _process_healing(character, medical_state, elapsed_minutes=1.0) -> list:
    """Walk stabilized + dressed organs; restore HP per dressing rate.

    #501: the rate is per MINUTE (the old per-tick value 1:1, since
    the tick was 60s).  Fractional progress accumulates on the organ
    (``dressing_progress``, persisted) and converts to whole HP via
    ``Organ.heal`` — granularity-independent like everything else.

    Returns the list of organs that received HP this pass.  Organs
    that reach full HP clear their ``stabilized`` + ``dressing_rate``
    automatically via the ``Organ.heal`` code path.
    """
    healed = []
    for organ in _healing_organs(medical_state):
        hp_per_minute = _hp_per_tick(getattr(organ, "dressing_rate", 0) or 0)
        progress = getattr(organ, "dressing_progress", 0.0) or 0.0
        progress += hp_per_minute * elapsed_minutes
        whole = int(progress)
        organ.dressing_progress = progress - whole
        if whole > 0:
            organ.heal(whole)
            healed.append(organ)
    return healed


class MedicalScript(DefaultScript):
    """
    Per-character script that manages all medical conditions.
    
    This script:
    - Runs every 60 seconds to process medical conditions
    - Automatically starts when first condition is added
    - Automatically stops when no conditions remain
    - Provides centralized medical condition management

    Lifecycle (#501 §6.2):
    - CREATED by start_medical_script() when a condition lands or a
      dressing needs ticking (idempotent — returns existing script).
    - TERMINATES itself when no conditions remain and no dressed
      organ has healing work; also stop+delete on critical tick
      error (prevents per-tick retry storms).
    - SURVIVES reload (persistent Script); at_start re-asserts the
      interval from constants so persisted config can't go stale.
      Conditions apply capped elapsed time via process(), so the
      reload gap itself is billed at most one extra sampling window.
    """
    
    def at_start(self):
        """Re-assert config on every (re)start (#501 Phase 2).

        Persisted scripts must never trust persisted config: this is
        what left pre-#465 scripts ticking at a stale 12s for their
        whole lifetime.  Re-reading the constant here means interval
        changes propagate to every live script on the next reload.
        """
        if self.interval != MEDICAL_TICK_INTERVAL:
            # `start(interval=...)`, not `restart(...)` (#2592). No
            # Evennia Script has `restart`; the old call raised
            # AttributeError out of `at_start`, which is the hook the
            # start machinery runs while bringing a persisted script
            # back up. #2592 reported only the death-progression copy;
            # this is the sibling, and it is the more consequential one
            # — this is the tick that runs bleeding.
            #
            # Calling `start()` from inside `at_start` DOES re-enter the
            # hook once (`_start_task` invokes it at scripts.py:254),
            # but the second pass finds the interval already correct and
            # does not call `start()` again — so it terminates after one
            # extra pass rather than recursing. Verified by test.
            self.start(interval=MEDICAL_TICK_INTERVAL)

    def at_server_start(self):
        """Re-arm the timer on any boot that had no clean shutdown (#2938).

        A Script's timer is ``ndb._task`` -- non-persistent by design.
        Evennia restores it across a reload by *pausing* on the way down
        (``_pause_task`` records ``db._paused_time``, but ONLY if a live
        task existed) and *unpausing* on the way up (``_unpause_task``,
        which is a no-op when ``_paused_time`` is None).  Any shutdown
        that skips the pause -- a crash, a kill, the VM going away --
        leaves the row ``db_is_active=True`` with no task, and every
        subsequent clean reload no-ops on it.  Once inert, permanently
        inert, with every DB field still reading healthy.

        ``GLOBAL_SCRIPTS`` escape this because the server re-creates and
        arms them from settings at every boot -- which is why
        ``souls_heartbeat`` and ``director_routines`` kept ticking while
        eight medical scripts sat dead for up to 77 days, four of them
        holding sedations that should have cleared in minutes.

        This is the hook Evennia provides for exactly this: it runs for
        every active script at boot, AFTER ``_unpause_task``.  ``start()``
        is idempotent -- it returns immediately if a task is already
        running -- so on a clean reload this does nothing and after a
        crash it is the recovery.  Public API only; the framework is not
        patched.

        Stopgap.  The carrier itself is the fragile part at scale (see
        CONDITION_CADENCE_SPEC Phase 3 and the heartbeat redesign it now
        records); this keeps the current carrier alive until then.
        """
        # ONLY re-arm a script that is supposed to be running.  Evennia
        # calls this hook for INACTIVE scripts too (`manager.py`:
        # `for script in self.filter(db_is_active=False): at_server_start()`),
        # and an unconditional `start()` resurrected scripts that were
        # deliberately stopped -- the medical tick stops-but-preserves on
        # death "for potential revival", and that row came back ticking on
        # the next reload.  `db_is_active` IS the "should be running"
        # signal, so gating on it still catches the crash case this hook
        # exists for (active, but no `ndb._task` after an unclean
        # shutdown) while leaving deliberate stops alone.
        if not self.db_is_active:
            return
        self.start()

    def at_script_creation(self):
        """Called when script is first created."""
        self.key = "medical_script"  # Use consistent key for searching
        self.desc = f"Medical condition manager for {self.obj.key}"
        # Production tick rate — the per-tick magnitudes in
        # world/medical/constants.py (blood-loss %, recovery rates)
        # are tuned against this interval.  The old hardcoded 12s was
        # a testing leftover that ran medical progression (and its
        # per-character CPU cost) 5x fast (issue #462).
        self.interval = MEDICAL_TICK_INTERVAL
        self.persistent = True
        self.start_delay = True  # Wait before first regular execution
        
        # Schedule first medical message with a delay longer than max combat delay
        from evennia.utils import delay
        delay(5, self._initial_medical_check)  # 5s delay ensures combat messages appear first
        
    def _initial_medical_check(self):
        """Perform initial medical check after creation delay."""
        # This replaces the first at_repeat call with proper timing
        self.at_repeat()
        # Note: start_delay is managed by Evennia, not modifiable at runtime
        
    def at_repeat(self):
        """Process all medical conditions for this character."""
        try:
            # Get splattercast for debugging
            splattercast = get_splattercast()
            
            # Get character's medical state
            if not hasattr(self.obj, 'medical_state'):
                splattercast.msg(f"MEDICAL_SCRIPT: {self.obj.key} has no medical_state, stopping script")
                self.stop()
                return
                
            medical_state = self.obj.medical_state
            conditions = medical_state.conditions.copy()  # Copy to avoid modification during iteration

            # PR-C (#307): stabilized wounds with a dressing rate
            # keep the script alive so the healing tick can run
            # even when there are no active conditions.  Without
            # this check, dressing a wound on an otherwise-healthy
            # character would never tick HP back.
            has_healing_work = _has_healing_work(medical_state)

            if not conditions and not has_healing_work:
                splattercast.msg(f"MEDICAL_SCRIPT: {self.obj.key} has no conditions, stopping and deleting script")
                self.stop()
                self.delete()
                return
                
            
            # Process each condition
            conditions_to_remove = []
            total_bleeding_severity = 0
            total_pain_severity = 0
            total_infection_severity = 0
            
            for condition in conditions:
                try:
                    if hasattr(condition, 'requires_ticker') and condition.requires_ticker:
                        condition.process(self.obj)
                        
                        # Track bleeding severity for consolidated messaging
                        if condition.condition_type == "bleeding":
                            total_bleeding_severity += condition.severity
                        
                        # Track pain severity for consolidated messaging
                        if condition.condition_type == "pain":
                            total_pain_severity += condition.severity
                            
                        # Track infection severity for consolidated messaging
                        if condition.condition_type == "infection":
                            total_infection_severity += condition.severity
                        
                        # Check if condition should be removed (e.g., severity reached 0)
                        if hasattr(condition, 'should_end') and condition.should_end():
                            conditions_to_remove.append(condition)
                            
                except Exception as e:
                    splattercast.msg(f"MEDICAL_SCRIPT_ERROR: Error processing {condition.condition_type}: {e}")
                    conditions_to_remove.append(condition)
            
            # Send consolidated messaging if conditions are active
            if total_bleeding_severity > 0 or total_pain_severity > 0 or total_infection_severity > 0:
                self._send_medical_messages(total_bleeding_severity, total_pain_severity, total_infection_severity)
            
            if total_bleeding_severity > 0:
                self._create_blood_pool(total_bleeding_severity)
            
            # Remove ended conditions
            # `remove_condition`, not a raw `list.remove` (#2544):
            # `is_dead()` is read a few lines below and returns a CACHE
            # that only `_invalidate_derived_state()` clears.  Nothing
            # between here and there clears it -- `update_vital_signs`
            # assigns `pain_level` and `consciousness`, which are plain
            # attributes with no setter -- so an ended condition that
            # changed a lethal capacity was invisible to that check.
            for condition in conditions_to_remove:
                medical_state.remove_condition(condition)
                splattercast.msg(f"MEDICAL_SCRIPT: Removed {condition.condition_type}")

            # PR-C (#307): healing tick.  Walk stabilized organs that
            # carry a dressing rate; restore HP proportional to the
            # rate.  Cheap in-memory pass — no per-organ DB hits
            # beyond the medical_state fetch already done above.
            # Healing elapsed: same clock seam as conditions (#501).
            from world.medical.clock import elapsed_game_minutes
            from world.medical.clock import now as clock_now
            from world.medical.constants import ELAPSED_CAP_MINUTES
            # ndb deliberately (#501 hygiene / DB-write doctrine):
            # a per-tick persisted write here measured 4.5x tick cost
            # at N=1000.  Reload resets the marker to "now", which is
            # exactly the downtime cap's intent anyway.
            heal_now = clock_now()
            last_heal = self.ndb.last_heal_process or heal_now
            heal_elapsed = min(
                elapsed_game_minutes(last_heal, heal_now),
                ELAPSED_CAP_MINUTES,
            )
            self.ndb.last_heal_process = heal_now
            healed_organs = _process_healing(
                self.obj, medical_state, elapsed_minutes=heal_elapsed,
            )
            if healed_organs:
                splattercast.msg(
                    f"MEDICAL_SCRIPT: Healing tick restored HP on "
                    f"{len(healed_organs)} organ(s) for "
                    f"{self.obj.key}"
                )

            # Update vital signs after processing all conditions
            # This ensures consciousness includes all penalties (pain, blood loss, suppression)
            medical_state.update_vital_signs()
            
            # Check for death/unconsciousness after processing conditions
            if medical_state.is_dead():
                splattercast.msg(f"MEDICAL_SCRIPT_DEATH: {self.obj.key} has died from medical conditions")
                
                # Check if death has already been processed to prevent double death curtains
                if hasattr(self.obj, 'ndb') and getattr(self.obj.ndb, 'death_processed', False):
                    splattercast.msg(f"MEDICAL_SCRIPT_DEATH_SKIP: {self.obj.key} death already processed")
                else:
                    # Trigger full death processing (includes death analysis and death curtain)
                    self.obj.at_death()
                    
                # Stop script but preserve it for potential revival
                self.stop()
                splattercast.msg(f"MEDICAL_SCRIPT_PAUSED: {self.obj.key} medical script stopped but preserved for revival")
                return
            elif medical_state.is_unconscious():
                splattercast.msg(f"MEDICAL_SCRIPT_UNCONSCIOUS: {self.obj.key} has become unconscious")
                
                # Check if unconsciousness has already been processed to prevent double messages
                if hasattr(self.obj, 'ndb') and getattr(self.obj.ndb, 'unconsciousness_processed', False):
                    splattercast.msg(f"MEDICAL_SCRIPT_UNCONSCIOUS_SKIP: {self.obj.key} unconsciousness already processed")
                else:
                    # Use character's own unconsciousness handling method
                    self.obj._handle_unconsciousness()
            else:
                # Character is conscious - clear unconsciousness flag if it was set
                # BUT only if they're not dead (prevent "regains consciousness" when dying)
                if (hasattr(self.obj, 'ndb') and getattr(self.obj.ndb, 'unconsciousness_processed', False) 
                    and not medical_state.is_dead()):
                    splattercast.msg(f"MEDICAL_SCRIPT_RECOVERY: {self.obj.key} has regained consciousness")
                    self.obj.ndb.unconsciousness_processed = False
                    # ONE method owns the whole transition, both ways.
                    #
                    # This branch used to hand-clear the two flags it knew
                    # about and stop -- while `apply_unconscious_state`
                    # had also swapped in `UnconsciousCmdSet`, which is a
                    # PERSISTENT default. So a character who went down to
                    # pain, blood loss or sedation and recovered NATURALLY
                    # stood up in the room description holding `help`,
                    # `who`, `time` and `quit`: no look, no movement, no
                    # actions, and reconnecting did not clear it. The only
                    # things that restored the cmdset were two
                    # Builder-locked admin commands and the death
                    # transition (#2416).
                    #
                    # The medical model owned half the recovery and the
                    # command layer owned the other half, and only the
                    # first half ever ran. `remove_unconscious_state`
                    # clears the same `override_place` this branch used
                    # to, so nothing is lost by deferring to it.
                    self.obj.remove_unconscious_state()
            
            # PERSIST WHAT THIS TICK JUST CHANGED.
            #
            # `Character._medical_state` is a plain in-memory instance;
            # persistence happens only through an explicit
            # `save_medical_state()`. Nothing in this method called it,
            # so `blood_level`, condition severities, clot and pain
            # decay, `last_processed`, dressed-organ HP and
            # `dressing_progress` all lived in memory until some other
            # path happened to save -- in practice only combat damage.
            #
            # So a reload HEALED bleeding: a character who bled from 100%
            # to 40% over twenty minutes snapped back to their blood
            # level at the moment of their last wound, and a dressing
            # applied to a patient who then took no further damage was
            # silently lost (#2418).
            #
            # This contradicted the script's own lifecycle docstring --
            # "SURVIVES reload... Conditions apply capped elapsed time
            # via `process()`" -- which is only true if `last_processed`
            # round-trips. `CONDITION_CADENCE_SPEC` §4.3/§7 is marked
            # SHIPPED and states the contract explicitly.
            #
            # Saved BEFORE the stop check, so the final healed state
            # persists too rather than being dropped with the script.
            from world.medical.utils import save_medical_state
            save_medical_state(self.obj)

            # Check if we should stop (no conditions left AND no
            # stabilized wounds still healing).  PR-C: keep the
            # script alive while there's healing work to do.
            if (not medical_state.conditions
                    and not _has_healing_work(medical_state)):
                splattercast.msg(f"MEDICAL_SCRIPT: All conditions processed, stopping and deleting script for {self.obj.key}")
                self.stop()
                self.delete()
                
        except Exception as e:
            # Deliberate guard (#469): a critical tick error stops and
            # deletes the script rather than retrying the same failure
            # every tick.  Logged; the next wound re-creates the script.
            splattercast = get_splattercast()
            splattercast.msg(f"MEDICAL_SCRIPT_CRITICAL_ERROR: {getattr(self.obj, 'key', '?')}: {e}")
            self.stop()
            self.delete()
    
    def at_stop(self):
        """Called when script stops."""
        # Nothing accumulated in memory is lost when the script ends,
        # whatever ended it -- death, a full heal, deletion (#3077).
        try:
            self._flush_blood_pool()
        except Exception:  # noqa: BLE001 -- a flush must never block a stop
            pass
        splattercast = get_splattercast()
        splattercast.msg(f"MEDICAL_SCRIPT_STOP: Medical script stopped for {self.obj.key}")
    
    def _send_medical_messages(self, bleeding_severity, pain_severity, infection_severity=0):
        """Send consolidated medical messages combining bleeding, pain, and infection."""
        import random
        
        # Check if character is dead - don't send personal messages to preserve death curtain
        medical_state = getattr(self.obj, 'medical_state', None)
        is_dead = medical_state and medical_state.is_dead()
        
        # Build message components
        personal_parts = []
        room_parts = []
        
        # Add bleeding components if present
        if bleeding_severity > 0:
            if is_dead:
                # Suppress all bleeding messages for dead characters
                # Death curtain will handle death-related messaging
                pass
            else:
                # Personal prose (|.msg() to the character) is humanoid
                # and only fires for PCs (NPCs without accounts drop
                # the msg silently), so the humanoid voice is
                # appropriate here.  Room prose is species-aware
                # (#356 follow-up) so a bleeding rat reads with
                # small-mammal imagery instead of generic humanoid
                # "trail of blood" prose.
                from world.medical.medical_messages import (
                    get_bleeding_room_message,
                )
                species = getattr(
                    getattr(self.obj, "db", None), "species", None,
                )
                room_template = get_bleeding_room_message(
                    bleeding_severity, species,
                )
                # the personal line bleeds YOUR colour (species-keyed:
                # human crimson, synth cobalt, robot amber)
                from world.anatomy import get_species_blood_color
                blood = get_species_blood_color(species)
                tint, cname = blood["code"], blood["name"]
                # The NOUN follows the species too (#2778): the room prose
                # four lines up already said "amber hydraulic fluid" for a
                # robot while this told the robot it was bleeding blood.
                fluid = blood.get("fluid", "blood")
                if bleeding_severity <= 3:
                    personal_parts.append(f"{tint}You feel warm {fluid} trickling from your wounds.|n")
                elif bleeding_severity <= 7:
                    personal_parts.append(f"{tint}{fluid.capitalize()} flows freely from your wounds, leaving {cname} trails.|n")
                elif bleeding_severity <= 12:
                    personal_parts.append(f"{tint}You feel your life ebbing away as {fluid} pours from your wounds.|n")
                else:  # 13+
                    personal_parts.append(f"{tint}Your vision dims as {fluid} gushes from grievous wounds.|n")
                room_parts.append(room_template)
        
        # Add pain components if present (only for living characters)
        if pain_severity > 0 and not is_dead:
            if pain_severity <= 5:
                personal_parts.append("|rYou feel a persistent ache from your injuries.|n")
            elif pain_severity <= 12:
                personal_parts.append("|rSharp pain flares from your wounds.|n")
            elif pain_severity <= 20:
                personal_parts.append("|rAgony courses through your battered form.|n")
            else:  # 21+
                personal_parts.append("|rUnbearable agony threatens to drive you unconscious.|n")
        
        # Add infection components if present (only for living characters)
        if infection_severity > 0 and not is_dead:
            if infection_severity <= 3:
                personal_parts.append("|rYou feel a mild warmth and tenderness at your injured areas.|n")
            elif infection_severity <= 5:
                personal_parts.append("|rYour wounds throb with inflamed heat.|n")
            elif infection_severity <= 7:
                personal_parts.append("|rYour wounds feel hot and inflamed, infection spreading.|n")
            else:  # 8+
                personal_parts.append("|rFever burns through you as infection spreads through your body.|n")
        
        # Combine and send messages
        if personal_parts and not is_dead:
            # Only send personal messages to living characters to preserve death curtain
            personal_msg = " ".join(personal_parts)
            self.obj.msg(personal_msg)
        
        if room_parts:
            # Join room messages and send via identity-aware system
            room_template = f"|r{' '.join(room_parts)}|n"
            if self.obj.location:
                from world.identity_utils import msg_room_identity
                msg_room_identity(
                    location=self.obj.location,
                    template=room_template,
                    char_refs={"actor": self.obj},
                    exclude=[self.obj],
                )
    
    # ------------------------------------------------------------------
    # Blood pool (#3077)
    #
    # Painting the floor was 72% of a bleeding tick: a linear scan of
    # ``room.contents`` to find the pool, then four attribute writes on
    # the pool's row and a description rebuild -- every tick, per
    # bleeder, so N bleeders in one room were N writers contending on
    # one row sixty times a minute.  At 1,000 wounded bodies that is
    # the difference between 11% and 42% of the reactor.
    #
    # The floor does not need to be repainted every tick.  It needs to
    # be right when somebody LOOKS.  So volume accumulates in memory and
    # is flushed to the pool object when any of these is true:
    #
    #   * a player is in the room (they can see it -- full fidelity),
    #   * the pending volume would move the pool into a new rendering
    #     band (the text would change),
    #   * BLOOD_POOL_FLUSH_TICKS have elapsed (bounded loss on a crash),
    #   * the script stops (death, healed, deleted) -- nothing is lost.
    #
    # A flush is ONE incident carrying the summed severity.  Forensics
    # (world/forensics.py) de-duplicates sources on ``apparent_uid`` and
    # keeps the latest ``timestamp`` per source, so one incident per
    # bleeder per flush is the same evidence it read before, in fewer
    # rows.  The maths -- blood loss, death -- is never gated on any of
    # this: a body nobody can see still bleeds out on schedule.
    # ------------------------------------------------------------------

    @staticmethod
    def _room_is_watched(room):
        """True when any puppeted session is standing in ``room``."""
        try:
            from evennia.server.sessionhandler import SESSIONS
        except Exception:  # noqa: BLE001 -- no session layer in some harnesses
            return False
        for sess in SESSIONS.get_sessions():
            puppet = sess.get_puppet() if hasattr(sess, "get_puppet") else None
            if puppet is not None and puppet.location == room:
                return True
        return False

    @staticmethod
    def _find_blood_pool(room):
        """The room's pool, via a per-room cache that validates itself.

        A pool that was cleaned or emptied is deleted (``pk`` becomes
        None) and one that was moved has a different ``location``, so a
        stale cache entry fails validation and we fall back to the scan
        that used to run every tick.
        """
        cached = getattr(room.ndb, "_blood_pool", None)
        if cached is not None and cached.pk and cached.location == room \
                and cached.db.is_blood_pool:
            return cached
        for obj in room.contents:
            if hasattr(obj, "db") and obj.db.is_blood_pool:
                room.ndb._blood_pool = obj
                return obj
        room.ndb._blood_pool = None
        return None

    def _create_blood_pool(self, severity):
        """Account this tick's bleeding; paint the floor only when it
        would show.  Name kept for the callers and tests that know it."""
        room = self.obj.location
        if not room:
            return
        # BLOOD STAYS WHERE IT WAS SHED (#3079 follow-up).  The pending
        # volume rides the script, but the flush used to read
        # `self.obj.location` at flush TIME -- so a bleeder who walked
        # between accumulating and flushing painted the previous room's
        # blood in the new one.  Measured: 1.0 units shed in room A
        # landed in room B.  Blood is forensic evidence; relocating it is
        # worse than the write cost being saved.  So a room change flushes
        # what is owed to the OLD room before accumulating for the new.
        shed_in = self.ndb._pool_room
        if shed_in is not None and shed_in != room:
            self._flush_blood_pool(room=shed_in)
        self.ndb._pool_room = room
        pending = float(self.ndb._pool_pending or 0.0) + float(severity)
        ticks = int(self.ndb._pool_ticks or 0) + 1
        self.ndb._pool_pending = pending
        self.ndb._pool_ticks = ticks

        from world.medical.constants import BLOOD_POOL_FLUSH_TICKS
        flush = ticks >= BLOOD_POOL_FLUSH_TICKS or self._room_is_watched(room)
        if not flush:
            pool = self._find_blood_pool(room)
            from typeclasses.objects import BloodPool
            have = (pool.db.total_volume or 0) if pool else 0
            if pool is None or BloodPool.volume_band(have + pending) \
                    != BloodPool.volume_band(have):
                flush = True          # the text would change
        if flush:
            self._flush_blood_pool()

    def _flush_blood_pool(self, room=None):
        """Write the accumulated volume to a room's pool as one incident.

        ``room`` defaults to where the body is now, but the caller passes
        the room the blood was SHED in when the body has since moved.
        """
        pending = float(self.ndb._pool_pending or 0.0)
        if room is None:
            room = self.ndb._pool_room or getattr(self.obj, "location", None)
        self.ndb._pool_pending = 0.0
        self.ndb._pool_ticks = 0
        self.ndb._pool_room = None
        if pending <= 0 or not room:
            return

        # THE PROPERTY.  `sleeve_uid` is an
        # `AttributeProperty(category="identity")`, so `.db.sleeve_uid`
        # reads a different row and is always None on a Character --
        # which is why all 326 bleeding incidents in the live database
        # recorded `sleeve_uid=None` and not one carried a real UID
        # (#2420).  `death_progression.py` documents the same trap.
        sleeve_uid = getattr(self.obj, "sleeve_uid", None)

        # Identity signature + apparent UID snapshot for the Forensic
        # Recognition Engine (PR-E), computed at FLUSH time rather than
        # every tick.  Reads default to None for legacy incidents.
        signature = None
        apparent_uid = None
        try:
            from world.identity import get_identity_signature, get_apparent_uid
            signature = get_identity_signature(self.obj)
            apparent_uid = get_apparent_uid(self.obj)
        except (AttributeError, TypeError, ValueError):
            pass

        from world.anatomy import get_species_blood_color
        blood_color = get_species_blood_color(getattr(self.obj.db, "species", None))

        pool = self._find_blood_pool(room)
        if pool is None:
            from evennia import create_object
            from typeclasses.objects import BloodPool
            pool = create_object(BloodPool, key="blood stains", location=room)
            room.ndb._blood_pool = pool
        pool.add_bleeding_incident(
            self.obj.key, pending, sleeve_uid=sleeve_uid,
            signature=signature, apparent_uid=apparent_uid,
            blood_color=blood_color,
        )


def start_medical_script(character):
    """
    Start or get the medical script for a character.
    
    Args:
        character: The character to start medical script for
        
    Returns:
        MedicalScript: The active medical script
    """
    # Don't create scripts for dead characters
    if hasattr(character, 'medical_state') and character.medical_state.is_dead():
        get_splattercast().msg(f"START_MEDICAL_SCRIPT: {character.key} is dead, not creating medical script")
        return None

    # Check if script already exists
    existing_script = character.scripts.get("medical_script")
    if existing_script:
        return existing_script.first() if existing_script else None

    # Create new script
    get_splattercast().msg(f"START_MEDICAL_SCRIPT: Creating new script for {character.key}")
    return character.scripts.add(MedicalScript)


def stop_medical_script(character):
    """
    Stop and delete the medical script for a character.
    
    Args:
        character: The character to stop medical script for
    """
    # Find and delete all medical scripts (active or stopped)
    existing_scripts = character.scripts.get("medical_script")
    if existing_scripts:
        for script in existing_scripts:
            get_splattercast().msg(f"STOP_MEDICAL_SCRIPT: Deleting script for {character.key}")
            script.stop()
            script.delete()
