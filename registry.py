from __future__ import annotations

import importlib
import logging
import sys

from config import RulesConfig
from entity_engine import EntityEngine

logger = logging.getLogger("content_filter")


class EngineRegistry:

    def __init__(self, config: RulesConfig):
        self._engines: dict[str, EntityEngine] = {}
        for ecfg in config.entities:
            scriptlets = self._load_scriptlets(ecfg, config.rules_dir)
            self._engines[ecfg["entity"]] = EntityEngine(ecfg, scriptlets)
        logger.info("EngineRegistry ready — %d entities: %s",
                    len(self._engines), list(self._engines.keys()))

    def _load_scriptlets(self, entity_cfg: dict, rules_dir: str) -> dict:
        scriptlets = {}
        for rule in entity_cfg.get("rules", []):
            ref = rule.get("scriptlet")
            if ref:
                scriptlets[rule["id"]] = self._load_scriptlet(ref, rules_dir)
                logger.debug("Loaded scriptlet '%s' for rule '%s'", ref, rule["id"])
        return scriptlets

    def _load_scriptlet(self, ref: str, rules_dir: str) -> callable:
        parts = ref.rsplit(".", 1)
        if len(parts) != 2:
            raise ValueError(f"Scriptlet must be 'module.function', got: {ref!r}")
        module_name, func_name = parts
        if rules_dir not in sys.path:
            sys.path.insert(0, rules_dir)
        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            raise ImportError(f"Cannot import scriptlet module '{module_name}': {e}") from e
        func = getattr(module, func_name, None)
        if func is None or not callable(func):
            raise AttributeError(f"'{func_name}' not found or not callable in '{module_name}'.")
        return func

    @property
    def entity_tags(self):
        return set(self._engines.keys())

    def get(self, tag: str) -> EntityEngine | None:
        return self._engines.get(tag)
