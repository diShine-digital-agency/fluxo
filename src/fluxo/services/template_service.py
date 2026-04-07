"""Service for managing channel templates (save, load, apply)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fluxo.models.channel import Channel
from fluxo.models.channel_template import ChannelTemplate
from fluxo.persistence.settings import Settings

logger = logging.getLogger(__name__)

_TEMPLATES_FILENAME = "channel_templates.json"


class TemplateService:
    """Manage reusable channel metadata templates.

    Templates are persisted as a JSON array in the user's config directory.
    """

    @staticmethod
    def save_as_template(channel: Channel, name: str) -> ChannelTemplate:
        """Create a :class:`ChannelTemplate` from an existing channel's metadata."""
        return ChannelTemplate(
            name=name,
            group_title=channel.group_title,
            tvg_logo=channel.tvg_logo,
            catchup=channel.catchup,
            catchup_days=channel.catchup_days,
            extra_attributes=dict(channel.extra_attributes),
            tags=list(channel.tags),
        )

    @staticmethod
    def apply_template(channel: Channel, template: ChannelTemplate) -> None:
        """Apply a template's metadata onto *channel*, overwriting matching fields."""
        channel.group_title = template.group_title
        channel.tvg_logo = template.tvg_logo
        channel.catchup = template.catchup
        channel.catchup_days = template.catchup_days
        channel.extra_attributes = dict(template.extra_attributes)
        channel.tags = list(template.tags)

    @staticmethod
    def list_templates() -> list[ChannelTemplate]:
        """Return all saved templates (convenience alias for :meth:`load_templates`)."""
        return TemplateService.load_templates()

    @staticmethod
    def save_templates(templates: list[ChannelTemplate]) -> None:
        """Persist *templates* to the config directory as JSON."""
        path = TemplateService._templates_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [t.to_dict() for t in templates]
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def load_templates() -> list[ChannelTemplate]:
        """Load templates from the config directory.

        Returns an empty list when the file does not exist or cannot be read.
        """
        path = TemplateService._templates_path()
        if not path.is_file():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return [ChannelTemplate.from_dict(entry) for entry in data]
        except (json.JSONDecodeError, OSError, KeyError) as exc:
            logger.warning("Failed to load templates from %s: %s", path, exc)
            return []

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _templates_path() -> Path:
        return Settings.get_config_dir() / _TEMPLATES_FILENAME
