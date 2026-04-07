"""Integration tests for import/edit/export workflows."""
from __future__ import annotations

import tempfile
from pathlib import Path

from fluxo.models.project import Project
from fluxo.parsers.m3u_parser import M3UParser
from fluxo.services.bulk_operations import BulkOperationService
from fluxo.services.export_service import ExportService
from fluxo.services.project_manager import ProjectManager


class TestImportEditExport:
    def test_import_edit_export_roundtrip(self, sample_m3u_path: Path):
        """Full workflow: import -> edit -> export -> re-import and verify."""
        parser = M3UParser()
        export_svc = ExportService()

        # Import
        result = parser.parse_file(str(sample_m3u_path))
        assert result.playlist.channel_count == 8

        # Edit: rename first channel
        result.playlist.channels[0].name = "CNN Edited"
        result.playlist.channels[0].group_title = "News Edited"

        # Export
        with tempfile.NamedTemporaryFile(suffix=".m3u", mode="w", delete=False) as f:
            content = export_svc.export_m3u(result.playlist)
            f.write(content)
            tmp_path = f.name

        # Re-import
        result2 = parser.parse_file(tmp_path)
        assert result2.playlist.channel_count == 8
        assert result2.playlist.channels[0].name == "CNN Edited"
        assert result2.playlist.channels[0].group_title == "News Edited"

        # Cleanup
        Path(tmp_path).unlink()

    def test_bulk_rename_workflow(self, sample_m3u_content: str):
        parser = M3UParser()
        bulk_svc = BulkOperationService()

        result = parser.parse(sample_m3u_content)
        # Bulk rename: replace "HD" suffix
        news_channels = result.playlist.get_channels_by_group("News")
        count = bulk_svc.bulk_rename(news_channels, "International", "Intl")
        assert count >= 1

    def test_project_save_load_roundtrip(self, sample_m3u_content: str):
        parser = M3UParser()
        pm = ProjectManager()

        result = parser.parse(sample_m3u_content)
        project = Project(name="Test Project")
        project.playlist = result.playlist

        with tempfile.NamedTemporaryFile(suffix=".fluxo", delete=False) as f:
            tmp_path = f.name

        pm.save_project(project, tmp_path)
        loaded = pm.load_project(tmp_path)

        assert loaded.name == "Test Project"
        assert loaded.playlist.channel_count == result.playlist.channel_count

        Path(tmp_path).unlink()
