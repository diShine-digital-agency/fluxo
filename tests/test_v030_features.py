"""Tests for v0.3.0 features: channel templates, normalization, collections."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fluxo.models.channel import Channel
from fluxo.models.channel_template import ChannelTemplate
from fluxo.models.collection import Collection
from fluxo.models.project import Project
from fluxo.services.normalization import NormalizationService
from fluxo.services.template_service import TemplateService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_channel(**kwargs) -> Channel:
    defaults = {"name": "Test Channel", "url": "http://example.com/stream"}
    defaults.update(kwargs)
    return Channel(**defaults)


# ---------------------------------------------------------------------------
# ChannelTemplate model
# ---------------------------------------------------------------------------


class TestChannelTemplate:
    """ChannelTemplate creation and serialization."""

    def test_create_template(self):
        t = ChannelTemplate(name="Sports")
        assert t.name == "Sports"
        assert t.group_title == ""
        assert t.tags == []

    def test_create_template_with_fields(self):
        t = ChannelTemplate(
            name="News",
            group_title="News & Info",
            tvg_logo="http://logo.png",
            catchup="default",
            catchup_days="3",
            extra_attributes={"x-provider": "acme"},
            tags=["news", "live"],
        )
        assert t.group_title == "News & Info"
        assert t.catchup_days == "3"
        assert t.extra_attributes == {"x-provider": "acme"}
        assert t.tags == ["news", "live"]

    def test_template_serialization_roundtrip(self):
        t = ChannelTemplate(
            name="Sports",
            group_title="Sports",
            tvg_logo="http://logo.png",
            tags=["hd", "premium"],
        )
        data = t.to_dict()
        restored = ChannelTemplate.from_dict(data)
        assert restored.name == t.name
        assert restored.group_title == t.group_title
        assert restored.tvg_logo == t.tvg_logo
        assert restored.tags == t.tags


# ---------------------------------------------------------------------------
# TemplateService
# ---------------------------------------------------------------------------


class TestTemplateService:
    """Template service: save_as_template and apply_template."""

    def test_save_as_template_from_channel(self):
        ch = _make_channel(
            group_title="Movies",
            tvg_logo="http://logo.png",
            catchup="default",
            catchup_days="7",
            extra_attributes={"x-region": "us"},
            tags=["vod"],
        )
        t = TemplateService.save_as_template(ch, "Movie Template")
        assert t.name == "Movie Template"
        assert t.group_title == "Movies"
        assert t.tvg_logo == "http://logo.png"
        assert t.catchup == "default"
        assert t.catchup_days == "7"
        assert t.extra_attributes == {"x-region": "us"}
        assert t.tags == ["vod"]

    def test_apply_template_to_channel(self):
        ch = _make_channel(group_title="Old Group", tags=["old"])
        t = ChannelTemplate(
            name="Sports",
            group_title="Sports",
            tvg_logo="http://sports.png",
            catchup="append",
            catchup_days="5",
            extra_attributes={"x-quality": "hd"},
            tags=["live", "sports"],
        )
        TemplateService.apply_template(ch, t)
        assert ch.group_title == "Sports"
        assert ch.tvg_logo == "http://sports.png"
        assert ch.catchup == "append"
        assert ch.catchup_days == "5"
        assert ch.extra_attributes == {"x-quality": "hd"}
        assert ch.tags == ["live", "sports"]
        # Channel identity fields should be untouched
        assert ch.name == "Test Channel"
        assert ch.url == "http://example.com/stream"

    def test_apply_template_does_not_share_mutable_refs(self):
        t = ChannelTemplate(
            name="T", extra_attributes={"k": "v"}, tags=["a"]
        )
        ch = _make_channel()
        TemplateService.apply_template(ch, t)
        ch.extra_attributes["new"] = "x"
        ch.tags.append("b")
        assert "new" not in t.extra_attributes
        assert "b" not in t.tags

    def test_save_and_load_templates(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            TemplateService,
            "_templates_path",
            staticmethod(lambda: tmp_path / "templates.json"),
        )
        templates = [
            ChannelTemplate(name="A", group_title="GroupA"),
            ChannelTemplate(name="B", tags=["x"]),
        ]
        TemplateService.save_templates(templates)
        loaded = TemplateService.load_templates()
        assert len(loaded) == 2
        assert loaded[0].name == "A"
        assert loaded[0].group_title == "GroupA"
        assert loaded[1].tags == ["x"]

    def test_load_templates_empty_when_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            TemplateService,
            "_templates_path",
            staticmethod(lambda: tmp_path / "nonexistent.json"),
        )
        assert TemplateService.load_templates() == []

    def test_list_templates_delegates_to_load(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            TemplateService,
            "_templates_path",
            staticmethod(lambda: tmp_path / "templates.json"),
        )
        TemplateService.save_templates([ChannelTemplate(name="Only")])
        result = TemplateService.list_templates()
        assert len(result) == 1
        assert result[0].name == "Only"


# ---------------------------------------------------------------------------
# NormalizationService
# ---------------------------------------------------------------------------


class TestNormalizationService:
    """Normalization rules for channel metadata."""

    def test_normalize_group_names(self):
        channels = [
            _make_channel(group_title="  sports  "),
            _make_channel(group_title="NEWS & info"),
            _make_channel(group_title="Already Title"),
        ]
        count = NormalizationService.normalize_group_names(channels)
        assert channels[0].group_title == "Sports"
        assert channels[1].group_title == "News & Info"
        assert channels[2].group_title == "Already Title"
        assert count == 2

    def test_clean_channel_names(self):
        channels = [
            _make_channel(name="ESPN HD"),
            _make_channel(name="BBC FHD"),
            _make_channel(name="Discovery 4K"),
            _make_channel(name="CNN"),
        ]
        count = NormalizationService.clean_channel_names(channels)
        assert channels[0].name == "ESPN"
        assert channels[1].name == "BBC"
        assert channels[2].name == "Discovery"
        assert channels[3].name == "CNN"
        assert count == 3

    def test_clean_channel_names_case_insensitive(self):
        channels = [_make_channel(name="Channel hd")]
        NormalizationService.clean_channel_names(channels)
        assert channels[0].name == "Channel"

    def test_fix_urls(self):
        channels = [
            _make_channel(url="  http://example.com/stream  "),
            _make_channel(url="https://secure.com/stream"),
            _make_channel(url="http://plain.com/stream"),
        ]
        count = NormalizationService.fix_urls(channels)
        assert channels[0].url == "https://example.com/stream"
        assert channels[1].url == "https://secure.com/stream"
        assert channels[2].url == "https://plain.com/stream"
        assert count == 2

    def test_remove_empty_groups(self):
        channels = [
            _make_channel(group_title=""),
            _make_channel(group_title="   "),
            _make_channel(group_title="Sports"),
        ]
        count = NormalizationService.remove_empty_groups(channels)
        assert channels[0].group_title == "Uncategorized"
        assert channels[1].group_title == "Uncategorized"
        assert channels[2].group_title == "Sports"
        assert count == 2

    def test_apply_all(self):
        channels = [
            _make_channel(
                name="ESPN HD",
                url="  http://example.com/espn  ",
                group_title="  sports  ",
            ),
            _make_channel(
                name="CNN FHD",
                url="https://cnn.com/live",
                group_title="",
            ),
        ]
        total = NormalizationService.apply_all(channels)
        assert total > 0
        assert channels[0].name == "ESPN"
        assert channels[0].url == "https://example.com/espn"
        assert channels[0].group_title == "Sports"
        assert channels[1].name == "CNN"
        assert channels[1].group_title == "Uncategorized"

    def test_apply_all_no_changes_needed(self):
        channels = [
            _make_channel(
                name="Clean",
                url="https://ok.com/stream",
                group_title="Valid Group",
            ),
        ]
        total = NormalizationService.apply_all(channels)
        assert total == 0


# ---------------------------------------------------------------------------
# Collection model
# ---------------------------------------------------------------------------


class TestCollection:
    """Collection creation and serialization."""

    def test_create_collection(self):
        c = Collection(name="Favorites")
        assert c.name == "Favorites"
        assert c.channel_ids == []
        assert c.description == ""
        assert isinstance(c.created_at, datetime)

    def test_create_collection_with_channels(self):
        ids = [uuid4(), uuid4()]
        c = Collection(name="Sports", channel_ids=ids, description="My sports channels")
        assert len(c.channel_ids) == 2
        assert c.channel_ids == ids
        assert c.description == "My sports channels"

    def test_collection_serialization_roundtrip(self):
        ids = [uuid4(), uuid4()]
        now = datetime.now(timezone.utc)
        c = Collection(
            name="News",
            channel_ids=ids,
            description="News channels",
            created_at=now,
        )
        data = c.to_dict()
        restored = Collection.from_dict(data)
        assert restored.name == c.name
        assert restored.channel_ids == c.channel_ids
        assert restored.description == c.description
        assert restored.created_at == c.created_at

    def test_collection_string_uuid_conversion(self):
        uid = uuid4()
        c = Collection(name="Test", channel_ids=[str(uid)])
        assert c.channel_ids[0] == uid


# ---------------------------------------------------------------------------
# Project model – collections integration
# ---------------------------------------------------------------------------


class TestProjectCollections:
    """Project should support collections."""

    def test_project_default_empty_collections(self):
        p = Project()
        assert p.collections == []

    def test_project_with_collections(self):
        col = Collection(name="My List", channel_ids=[uuid4()])
        p = Project(collections=[col])
        assert len(p.collections) == 1
        assert p.collections[0].name == "My List"

    def test_project_serialization_with_collections(self):
        col = Collection(name="Watch Later", description="Save for later")
        p = Project(name="Test Project", collections=[col])
        data = p.to_dict()
        restored = Project.from_dict(data)
        assert len(restored.collections) == 1
        assert restored.collections[0].name == "Watch Later"
        assert restored.collections[0].description == "Save for later"

    def test_project_serialization_without_collections_backward_compat(self):
        data = {"name": "Old Project"}
        p = Project.from_dict(data)
        assert p.collections == []
