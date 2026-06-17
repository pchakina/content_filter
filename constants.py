class RuleAction:
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    DEFER  = "DEFER"

    DATE_FORMATS = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m-%d-%Y",
    ]
