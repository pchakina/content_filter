from __future__ import annotations

import logging
from io import BytesIO
from lxml import etree

from config import RulesConfig
from registry import EngineRegistry

logger = logging.getLogger("content_filter")


class XmlFilter:
    """
    Instantiate once, reuse across all messages.

        xf = XmlFilter("rules.yaml")
        filtered = xf.process_string(xml, message_id="MSG-001")
    """

    def __init__(self, rules_path: str):
        self._registry = EngineRegistry(RulesConfig(rules_path))

    def process_file(self, input_path: str, output_path: str,
                     dry_run: bool = False, message_id: str = None) -> None:
        with open(input_path, "rb") as f:
            data = f.read()
        result = self.process_bytes(data, dry_run=dry_run, message_id=message_id)
        if not dry_run:
            with open(output_path, "wb") as f:
                f.write(result)

    def process_string(self, xml_text: str,
                       dry_run: bool = False, message_id: str = None) -> str:
        return self.process_bytes(
            xml_text.encode("utf-8"), dry_run=dry_run, message_id=message_id
        ).decode("utf-8")

    def process_bytes(self, xml_bytes: bytes,
                      dry_run: bool = False, message_id: str = None) -> bytes:
        is_fragment, tree = self._parse(xml_bytes)
        root = tree.getroot()

        accepted = rejected = 0

        for tag in self._registry.entity_tags:
            engine   = self._registry.get(tag)
            elements = root.findall(f".//{tag}")
            if root.tag == tag:
                elements = [root] + elements
            if not elements:
                continue

            to_reject = engine.filter(elements, dry_run=dry_run, message_id=message_id)
            accepted += len(elements) - len(to_reject)
            rejected += len(to_reject)

            for el in elements:
                if id(el) in to_reject:
                    parent = el.getparent()
                    if parent is not None:
                        parent.remove(el)

        logger.info("%s | accepted=%d rejected=%d%s",
                    message_id or "-", accepted, rejected,
                    " [DRY-RUN]" if dry_run else "")

        if is_fragment:
            return b"\n".join(etree.tostring(c, pretty_print=True) for c in root) + b"\n"

        return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="utf-8")

    @staticmethod
    def _parse(xml_bytes: bytes) -> tuple[bool, etree._ElementTree]:
        try:
            tree = etree.parse(BytesIO(xml_bytes))
            XmlFilter._strip_namespaces(tree)
            return False, tree
        except etree.XMLSyntaxError:
            pass

        try:
            tree = etree.parse(BytesIO(b"<Root>\n" + xml_bytes + b"\n</Root>"))
            XmlFilter._strip_namespaces(tree)
            return True, tree
        except etree.XMLSyntaxError as e:
            raise ValueError(f"XML could not be parsed: {e}") from e

    @staticmethod
    def _strip_namespaces(tree: etree._ElementTree):
        for el in tree.iter():
            if isinstance(el.tag, str) and "{" in el.tag:
                el.tag = el.tag.split("}", 1)[1]
            stripped = {(k.split("}", 1)[1] if "{" in k else k): v for k, v in el.attrib.items()}
            el.attrib.clear()
            el.attrib.update(stripped)
