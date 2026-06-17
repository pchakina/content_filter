import os
import yaml


class RulesConfig:

    def __init__(self, path: str):
        self.path      = os.path.abspath(path)
        self.rules_dir = os.path.dirname(self.path)

        with open(self.path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        self._entities = self._validate(raw)

    @property
    def entities(self):
        return list(self._entities)

    @property
    def entity_tags(self):
        return [e["entity"] for e in self._entities]

    def _validate(self, raw):
        if not isinstance(raw, dict) or "entities" not in raw:
            raise ValueError(f"{self.path}: missing top-level 'entities' list.")

        entities = raw["entities"]
        if not isinstance(entities, list) or not entities:
            raise ValueError(f"{self.path}: 'entities' must be a non-empty list.")

        for i, e in enumerate(entities):
            for field in ("entity", "primary_key"):
                if field not in e:
                    raise ValueError(f"{self.path}: entity[{i}] missing '{field}'.")

            for rule in e.get("rules", []):
                for field in ("id", "priority", "action"):
                    if field not in rule:
                        raise ValueError(
                            f"{self.path}: rule '{rule.get('id', '?')}' "
                            f"in entity '{e['entity']}' missing '{field}'."
                        )
                if not rule.get("condition") and not rule.get("scriptlet"):
                    raise ValueError(
                        f"{self.path}: rule '{rule['id']}' in '{e['entity']}' "
                        f"needs at least a condition or a scriptlet."
                    )

        tags = [e["entity"] for e in entities]
        dupes = {t for t in tags if tags.count(t) > 1}
        if dupes:
            raise ValueError(f"{self.path}: duplicate entity tags: {dupes}")

        return entities
