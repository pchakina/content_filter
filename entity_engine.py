from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from lxml import etree

from constants import RuleAction
from condition import ConditionEvaluator

logger = logging.getLogger("content_filter")


class EntityEngine:

    def __init__(self, entity_cfg: dict, scriptlets: dict):
        self.entity_tag     = entity_cfg["entity"]
        self.primary_key    = entity_cfg["primary_key"]
        self.default_action = entity_cfg.get("default_action", RuleAction.REJECT).upper()
        self._scriptlets    = scriptlets

        rules = sorted(entity_cfg.get("rules", []), key=lambda r: r["priority"])
        self._record_rules = [r for r in rules if r.get("type", "record") == "record"]
        self._group_rules  = [r for r in rules if r.get("type") == "group"]

    def filter(self, elements: list, dry_run: bool = False, message_id: str = None) -> set:
        state = {}
        for idx, el in enumerate(elements):
            action, rule_id = self._run_record_rules(el)
            state[idx] = {"el": el, "action": action, "rule": rule_id, "pk": self._pk(el)}

        groups = defaultdict(list)
        for idx, rec in state.items():
            groups[rec["pk"]].append(idx)

        for indices in groups.values():
            if len(indices) >= 2:
                self._run_group_rules(indices, state)

        for rec in state.values():
            if rec["action"] == RuleAction.DEFER:
                action, rule_id = self._run_record_rules(rec["el"], skip_defer=True)
                rec["action"] = action if action != RuleAction.DEFER else self.default_action
                rec["rule"]   = rule_id if action != RuleAction.DEFER else "DEFAULT"

        rejected = set()
        for rec in state.values():
            logger.debug("%s | entity=%s id=%s action=%s rule=%s%s",
                message_id or "-", self.entity_tag,
                rec["el"].get("ID", "?"), rec["action"], rec["rule"],
                " [DRY-RUN]" if dry_run else "")
            if rec["action"] != RuleAction.ACCEPT:
                rejected.add(id(rec["el"]))

        return rejected

    def _pk(self, element):
        return tuple(ConditionEvaluator.get_field(element, f) for f in self.primary_key)

    def _run_record_rules(self, element, skip_defer=False):
        for rule in self._record_rules:
            cond = rule.get("condition", {})
            if "min_size" in cond or "member_filter" in cond:
                continue
            if cond and not ConditionEvaluator.evaluate(element, cond):
                continue
            scriptlet = self._scriptlets.get(rule["id"])
            if scriptlet is not None:
                try:
                    if not scriptlet(element):
                        continue
                except Exception as e:
                    logger.warning("Scriptlet error in rule '%s': %s — skipping", rule["id"], e)
                    continue
            action = rule["action"].upper()
            if skip_defer and action == RuleAction.DEFER:
                continue
            return action, rule["id"]
        return self.default_action, "DEFAULT"

    def _run_group_rules(self, indices, state):
        for rule in self._group_rules:
            cond          = rule.get("condition", {})
            min_size      = cond.get("min_size", 2)
            member_filter = cond.get("member_filter", "ANY").upper()
            action        = rule["action"].upper()

            candidates = [i for i in indices if member_filter == "ANY" or state[i]["action"] == member_filter]
            if len(candidates) < min_size:
                continue

            scriptlet = self._scriptlets.get(rule["id"])
            if scriptlet is not None:
                try:
                    elements = [state[i]["el"] for i in candidates]
                    keep     = {id(el) for el in scriptlet(elements)}
                    for i in candidates:
                        state[i]["action"] = RuleAction.ACCEPT if id(state[i]["el"]) in keep else RuleAction.REJECT
                        state[i]["rule"]   = rule["id"]
                except Exception as e:
                    logger.warning("Scriptlet error in group rule '%s': %s — skipping", rule["id"], e)
                continue

            match action:
                case "KEEP_LATEST" | "KEEP_EARLIEST":
                    self._dedup_date(candidates, state, rule, keep_latest=(action == "KEEP_LATEST"))
                case "KEEP_MAX" | "KEEP_MIN":
                    self._dedup_numeric(candidates, state, rule, keep_max=(action == "KEEP_MAX"))
                case "KEEP_FIRST":
                    for rank, idx in enumerate(candidates):
                        state[idx]["action"] = RuleAction.ACCEPT if rank == 0 else RuleAction.REJECT
                        state[idx]["rule"]   = rule["id"]
                case "KEEP_LAST":
                    for rank, idx in enumerate(candidates):
                        state[idx]["action"] = RuleAction.ACCEPT if rank == len(candidates) - 1 else RuleAction.REJECT
                        state[idx]["rule"]   = rule["id"]
                case "REJECT_ALL":
                    for idx in candidates:
                        state[idx]["action"] = RuleAction.REJECT
                        state[idx]["rule"]   = rule["id"]
                case "ACCEPT_ALL":
                    for idx in candidates:
                        state[idx]["action"] = RuleAction.ACCEPT
                        state[idx]["rule"]   = rule["id"]

    def _dedup_date(self, candidates, state, rule, keep_latest):
        field = rule.get("compare_field")
        fmt   = rule.get("date_format")
        tie   = rule.get("tie_break", "KEEP_FIRST").upper()

        def key(idx):
            val = ConditionEvaluator.get_field(state[idx]["el"], field)
            try:    return ConditionEvaluator.parse_date(val, fmt)
            except: return datetime.min

        best    = key(sorted(candidates, key=key, reverse=keep_latest)[0])
        winners = [i for i in candidates if key(i) == best]
        losers  = [i for i in candidates if key(i) != best]

        for idx in losers:
            state[idx]["action"] = RuleAction.REJECT
            state[idx]["rule"]   = rule["id"]

        if tie == "KEEP_ALL":
            for idx in winners:
                state[idx]["action"] = RuleAction.ACCEPT
                state[idx]["rule"]   = rule["id"]
        else:
            winner = min(winners) if tie != "KEEP_LAST" else max(winners)
            for idx in winners:
                state[idx]["action"] = RuleAction.ACCEPT if idx == winner else RuleAction.REJECT
                state[idx]["rule"]   = rule["id"]

    def _dedup_numeric(self, candidates, state, rule, keep_max):
        field = rule.get("compare_field")
        tie   = rule.get("tie_break", "KEEP_FIRST").upper()

        def key(idx):
            val = ConditionEvaluator.get_field(state[idx]["el"], field)
            try:    return float(val)
            except: return float("-inf")

        best    = key(sorted(candidates, key=key, reverse=keep_max)[0])
        winners = [i for i in candidates if key(i) == best]
        losers  = [i for i in candidates if key(i) != best]

        for idx in losers:
            state[idx]["action"] = RuleAction.REJECT
            state[idx]["rule"]   = rule["id"]

        if tie == "KEEP_ALL":
            for idx in winners:
                state[idx]["action"] = RuleAction.ACCEPT
                state[idx]["rule"]   = rule["id"]
        else:
            winner = min(winners) if tie != "KEEP_LAST" else max(winners)
            for idx in winners:
                state[idx]["action"] = RuleAction.ACCEPT if idx == winner else RuleAction.REJECT
                state[idx]["rule"]   = rule["id"]
