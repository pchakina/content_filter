from __future__ import annotations

from datetime import datetime
from lxml import etree

from constants import RuleAction


class ConditionEvaluator:

    @staticmethod
    def get_field(element: etree._Element, path: str) -> str | None:
        node = element
        for part in path.split("/"):
            node = node.find(part)
            if node is None:
                return None
        return node.text.strip() if node is not None and node.text else None

    @staticmethod
    def parse_date(value: str, fmt: str | None) -> datetime:
        for f in ([fmt] if fmt else []) + RuleAction.DATE_FORMATS:
            if not f:
                continue
            try:
                return datetime.strptime(value, f)
            except (ValueError, TypeError):
                continue
        raise ValueError(f"Cannot parse date: {value!r}")

    @classmethod
    def evaluate(cls, element: etree._Element, cond: dict) -> bool:
        if "all" in cond:
            return all(cls.evaluate(element, c) for c in cond["all"])
        if "any" in cond:
            return any(cls.evaluate(element, c) for c in cond["any"])
        if "not" in cond:
            return not cls.evaluate(element, cond["not"])
        return cls._eval_leaf(element, cond)

    @classmethod
    def _eval_leaf(cls, element: etree._Element, cond: dict) -> bool:
        field    = cond.get("field")
        operator = cond.get("operator", "eq")
        expected = cond.get("value")
        actual   = cls.get_field(element, field) if field else None

        match operator:
            case "eq":        return actual == str(expected) if expected is not None else actual is None
            case "ne":        return actual != str(expected)
            case "in":        return actual in [str(v) for v in (expected or [])]
            case "not_in":    return actual not in [str(v) for v in (expected or [])]
            case "is_empty":  return not actual
            case "not_empty": return bool(actual)
            case "gt":
                try:    return float(actual) > float(expected)
                except: return False
            case "lt":
                try:    return float(actual) < float(expected)
                except: return False
            case _:
                raise ValueError(f"Unknown operator: {operator!r}")
