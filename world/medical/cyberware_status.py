"""``/system`` — cyberware diagnostic readout (#567).

A one-shot self-diagnostic of the character's own installed cyberware,
rendered in the operate-menu house aesthetic (label box + branching
tree).  Not interactive — a status check, not a menu.

Grouping (grounded in the real organ substrate): a cyber limb is several
organs across its containers (a cyber arm = humerus + forearm hardpoint
at ``right_arm`` plus metacarpals at ``right_hand``), so limb-container
organs group by container ("right arm", "right hand").  Head/torso cyber
organs group by organ name instead ("jaw", "left eye"), since the
container ("head") would mislabel a cyber jaw.  Flesh-mount abilities
(Nailz) live on flesh hosts, not chrome, so they group by ability across
their host containers ("both hands").

The header is our own flavor (no CPU/processor model — that's the parked
capacity thread); it leaves room for a future cortical-stack readout.
"""

from __future__ import annotations

from world.medical.augments import _ability_state

# Mirror the operate-menu glyph metrics (commands/CmdOperate.py) so the
# readout shares the surgical UI's visual idiom.
_BOX_W = 15
_GUTTER = " " * (_BOX_W + 2 + 2)  # aligns the trunk under the box corner
_MUTED = "|520"

# Containers that are NOT limbs: their cyber organs label by organ name
# (a cyber jaw sits at the "head" container but reads as "jaw").
_NON_LIMB = {"head", "neck", "chest", "abdomen", "back", "groin"}


def _label_box(label: str) -> tuple[str, str, str]:
    label = label.upper()
    pad = _BOX_W - len(label)
    left = pad // 2
    text = " " * left + label + " " * (pad - left)
    return f"╔{'═' * _BOX_W}╗", f"║{text}║", f"╚{'═' * _BOX_W}╝"


def _cyber_organs(character):
    """Return ``(name, organ, data)`` for every cyber-relevant organ:
    chrome (``inorganic`` / ``prosthetic_frame``) or any organ carrying
    an ability (catches flesh-mount modules like Nailz)."""
    state = getattr(character, "medical_state", None)
    organs = getattr(state, "organs", None) if state else None
    out = []
    if not organs:
        return out
    for name, organ in organs.items():
        data = getattr(organ, "data", None) or {}
        if data.get("inorganic") or data.get("prosthetic_frame") or data.get("abilities"):
            out.append((name, organ, data))
    return out


def _status_tag(ratio: float) -> tuple[str, str]:
    """(colored ONLINE/DAMAGED/OFFLINE tag, condition prose) from an
    HP ratio.  Prose-only — no raw numbers (matches look / diagnose)."""
    if ratio <= 0:
        return "|rOFFLINE|n", "wrecked"
    if ratio < 0.7:
        return "|yDAMAGED|n", "degraded"
    return "|gONLINE|n", "intact"


def _ability_lines(organ, data) -> list[str]:
    """Hardpoint / system lines for one chrome organ."""
    lines = []
    hardpoint = data.get("hardpoint")
    abilities = data.get("abilities") or {}
    if hardpoint and not abilities:
        lines.append(f"hardpoint ...... {_MUTED}empty · 1 slot|n")
    for aname in abilities:
        state = "|rDEPLOYED|n" if _ability_state(organ, aname).get("deployed") else "retracted"
        label = "hardpoint" if hardpoint else "system"
        lines.append(f"{label} ...... {aname} — {state}")
    return lines


def render_system(character) -> str:
    cyber = _cyber_organs(character)
    if not cyber:
        return (
            "Self-diagnostic: your wetware is all meat. "
            "No cybernetics installed."
        )

    chrome = [(n, o, d) for n, o, d in cyber
              if d.get("inorganic") or d.get("prosthetic_frame")]
    flesh_mods = [(n, o, d) for n, o, d in cyber
                  if not (d.get("inorganic") or d.get("prosthetic_frame"))
                  and d.get("abilities")]

    # --- Chrome devices: group limb organs by container, head/torso by name.
    groups: dict = {}
    order: list = []
    for name, organ, data in chrome:
        container = getattr(organ, "container", None) or ""
        if container in _NON_LIMB:
            key, label = ("organ", name), name.replace("_", " ")
        else:
            key, label = ("limb", container), container.replace("_", " ")
        if key not in groups:
            groups[key] = {"label": label, "organs": []}
            order.append(key)
        groups[key]["organs"].append((organ, data))

    devices: list = []  # (label, tag, [fields])
    for key in order:
        group = groups[key]
        organs = group["organs"]
        worst = min(
            (o.current_hp / o.max_hp) if o.max_hp else 0 for o, _ in organs
        )
        tag, condition = _status_tag(worst)
        fields = [
            f"condition ...... {condition}",
            "feedback ....... live · pain registers",
        ]
        for organ, data in organs:
            fields.extend(_ability_lines(organ, data))
        devices.append((f"cybernetic {group['label']}", tag, fields))

    # --- Flesh-mount abilities: group by ability across host containers.
    flesh_abilities: dict = {}
    for name, organ, data in flesh_mods:
        for aname in (data.get("abilities") or {}):
            entry = flesh_abilities.setdefault(
                aname, {"hosts": [], "organ": organ}
            )
            entry["hosts"].append(getattr(organ, "container", "") or "")
    for aname, entry in flesh_abilities.items():
        hosts = set(entry["hosts"])
        if hosts >= {"left_hand", "right_hand"}:
            where = "both hands"
        else:
            where = " · ".join(sorted(h.replace("_", " ") for h in hosts))
        state = (
            "|rDEPLOYED|n"
            if _ability_state(entry["organ"], aname).get("deployed")
            else "retracted"
        )
        devices.append((
            aname.capitalize(),
            "|gONLINE|n",
            [
                f"mount .......... {where} · flesh",
                "feedback ....... host tissue · pain registers",
                f"edge ........... {state}",
            ],
        ))

    # --- Render: header box + inline tee + device tree.
    top, mid, bot = _label_box("CYBER SYSTEMS")
    count = len(devices)
    plural = "s" if count != 1 else ""
    out = [
        top,
        f"{mid}──┬──  self-diagnostic handshake ok",
        f"{bot}  │     {_MUTED}{count} system{plural} registered · "
        f"neural feedback nominal|n",
        f"{_GUTTER}│",
    ]
    for index, (label, tag, fields) in enumerate(devices):
        last = index == count - 1
        joint = "└──" if last else "├──"
        trunk = " " if last else "│"
        out.append(f"{_GUTTER}{joint}[ {tag} ]  {label}")
        for field in fields:
            out.append(f"{_GUTTER}{trunk}      {field}")
        if not last:
            out.append(f"{_GUTTER}│")
    return "\n".join(out)
