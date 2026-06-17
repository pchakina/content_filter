from datetime import datetime
from lxml import etree


def reject_expired_today(element: etree._Element) -> bool:
    raw = element.findtext("ExpirationDate") or ""
    try:
        return datetime.strptime(raw[:10], "%Y-%m-%d").date() < datetime.today().date()
    except ValueError:
        return False


def keep_highest_coverage(elements: list) -> list:
    def total(el):
        occ = float(el.findtext("CoverageAmountOccurrence") or 0)
        agg = float(el.findtext("CoverageAmountAggregate") or 0)
        return occ + agg

    return [max(elements, key=total)] if elements else []
