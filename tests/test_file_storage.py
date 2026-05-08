"""
Unit tests for file storage implementation.

Tests the LocalFileStorage class for proper file organization,
unique filename generation, and cascade deletion functionality.

Validates: Requirements 8.1, 8.2, 8.3
"""

import os
import tempfile
import shutil
from pathlib import Path
import pytest
from app.storage.file_storage import LocalFileStorage, IFileStorage
from app.models.enums import CaptionFormat


@pytest.fixture
def temp_storage():
    """
    Create a temporary storage directory for testing.
    
    Yields a LocalFileStorage instance with a temporary base path,
    then cleans up after the test.
    """
    temp_dir = tempfile.mkdtemp()
    storage = LocalFileStorage(base_path=temp_dir)
    yield storage
    # Cleanup
    shutil.rmtree(temp_dir)


class TestLocalFileStorage:
    """Test suite for LocalFileStorage implementation."""
    
    def test_implements_interface(self, temp_storage):
        """Verify LocalFileStorage implements IFileStorage interface."""
        assert isinstance(temp_storage, IFileStorage)
    
    def test_directory_creation(self, temp_storage):
        """
        Test that all required directories are created on initialization.
        
        Validates: Requirements 8.1
        """
        assert temp_storage.uploads_dir.exists()
        assert temp_storage.watermarks_dir.exists()
        assert temp_storage.captions_dir.exists()
        assert temp_storage.outputs_dir.exists()
        
        assert temp_storage.uploads_dir.is_dir()
        assert temp_storage.watermarks_dir.is_dir()
        assert temp_storage.captions_dir.is_dir()
        assert temp_storage.outputs_dir.is_dir()
    
    def test_save_upload_creates_file(self, temp_storage):
        """
        Test that save_upload creates a file in the uploads directory.
        
        Validates: Requirements 1.1, 8.1
        """
        content = b"fake video content"
        filename = "test_video.mp4"
        
        file_id = temp_storage.save_upload(content, filename)
        
        # Verify file was created
        file_path = temp_storage.uploads_dir / file_id
        assert file_path.exists()
        assert file_path.is_file()
        
        # Verify content
        with open(file_path, 'rb') as f:
            assert f.read() == content
    
    def test_save_upload_preserves_extension(self, temp_storage):
        """
        Test that save_upload preserves the file extension.
        
        Validates: Requirements 8.2
        """
        content = b"fake video content"
        
        # Test various extensions
        for ext in ['.mp4', '.mov', '.avi']:
            filename = f"test_video{ext}"
            file_id = temp_storage.save_upload(content, filename)
            assert file_id.endswith(ext)
    
    def test_save_upload_generates_unique_filenames(self, temp_storage):
        """
        Test that save_upload generates unique filenames for each upload.
        
        Validates: Requirements 8.2
        """
        content = b"fake video content"
        filename = "test_video.mp4"
        
        # Upload same file multiple times
        file_id_1 = temp_storage.save_upload(content, filename)
        file_id_2 = temp_storage.save_upload(content, filename)
        file_id_3 = temp_storage.save_upload(content, filename)
        
        # All IDs should be different
        assert file_id_1 != file_id_2
        assert file_id_2 != file_id_3
        assert file_id_1 != file_id_3
        
        # All files should exist
        assert (temp_storage.uploads_dir / file_id_1).exists()
        assert (temp_storage.uploads_dir / file_id_2).exists()
        assert (temp_storage.uploads_dir / file_id_3).exists()
    
    def test_save_watermark_creates_file(self, temp_storage):
        """
        Test that save_watermark creates a file in the watermarks directory.
        
        Validates: Requirements 4.1, 8.1
        """
        content = b"fake png content"
        filename = "logo.png"
        
        file_id = temp_storage.save_watermark(content, filename)
        
        # Verify file was created in watermarks directory
        file_path = temp_storage.watermarks_dir / file_id
        assert file_path.exists()
        assert file_path.is_file()
        
        # Verify content
        with open(file_path, 'rb') as f:
            assert f.read() == content
    
    def test_save_watermark_generates_unique_filenames(self, temp_storage):
        """
        Test that save_watermark generates unique filenames.
        
        Validates: Requirements 8.2
        """
        content = b"fake png content"
        filename = "logo.png"
        
        file_id_1 = temp_storage.save_watermark(content, filename)
        file_id_2 = temp_storage.save_watermark(content, filename)
        
        assert file_id_1 != file_id_2
    
    def test_save_caption_srt_format(self, temp_storage):
        """
        Test that save_caption creates SRT caption file correctly.
        
        Validates: Requirements 2.3, 8.1
        """
        content = "1\n00:00:00,000 --> 00:00:02,500\nFirst caption\n\n"
        video_id = "test-video-123"
        
        file_id = temp_storage.save_caption(content, video_id, CaptionFormat.SRT)
        
        # Verify filename format
        assert file_id == f"{video_id}.srt"
        
        # Verify file was created in captions directory
        file_path = temp_storage.captions_dir / file_id
        assert file_path.exists()
        
        # Verify content
        with open(file_path, 'r', encoding='utf-8') as f:
            assert f.read() == content
    
    def test_save_caption_vtt_format(self, temp_storage):
        """
        Test that save_caption creates VTT caption file correctly.
        
        Validates: Requirements 2.3, 8.1
        """
        content = "WEBVTT\n\n00:00:00.000 --> 00:00:02.500\nFirst caption\n\n"
        video_id = "test-video-456"
        
        file_id = temp_storage.save_caption(content, video_id, CaptionFormat.VTT)
        
        # Verify filename format
        assert file_id == f"{video_id}.vtt"
        
        # Verify file was created
        file_path = temp_storage.captions_dir / file_id
        assert file_path.exists()
    
    def test_save_caption_overwrites_existing(self, temp_storage):
        """
        Test that save_caption overwrites existing caption file.
        
        This allows for caption editing functionality.
        
        Validates: Requirements 3.3
        """
        video_id = "test-video-789"
        content_1 = "First version"
        content_2 = "Second version"
        
        # Save first version
        temp_storage.save_caption(content_1, video_id, CaptionFormat.SRT)
        
        # Save second version (should overwrite)
        file_id = temp_storage.save_caption(content_2, video_id, CaptionFormat.SRT)
        
        # Verify only one file exists with updated content
        file_path = temp_storage.captions_dir / file_id
        with open(file_path, 'r', encoding='utf-8') as f:
            assert f.read() == content_2
    
    def test_save_output_moves_file(self, temp_storage):
        """
        Test that save_output moves file to outputs directory.
        
        Validates: Requirements 5.5, 8.1
        """
        # Create a temporary source file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        temp_file.write(b"processed video content")
        temp_file.close()
        
        video_id = "test-video-output"
        
        try:
            file_id = temp_storage.save_output(video_id, temp_file.name)
            
            # Verify filename format
            assert file_id == f"{video_id}.mp4"
            
            # Verify file was moved to outputs directory
            output_path = temp_storage.outputs_dir / file_id
            assert output_path.exists()
            
            # Verify source file no longer exists
            assert not os.path.exists(temp_file.name)
            
            # Verify content
            with open(output_path, 'rb') as f:
                assert f.read() == b"processed video content"
        finally:
            # Cleanup in case of test failure
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
    
    def test_delete_video_files_removes_all_associated_files(self, temp_storage):
        """
        Test that delete_video_files removes all files associated with a video.
        
        Validates: Requirements 8.3
        """
        video_id = "test-video-delete"
        
        # Create source video
        upload_id = temp_storage.save_upload(b"video content", f"{video_id}.mp4")
        # Rename to use video_id as filename (simulating how it would be stored)
        old_path = temp_storage.uploads_dir / upload_id
        new_path = temp_storage.uploads_dir / f"{video_id}.mp4"
        shutil.move(str(old_path), str(new_path))
        
        # Create captions
        temp_storage.save_caption("SRT content", video_id, CaptionFormat.SRT)
        temp_storage.save_caption("VTT content", video_id, CaptionFormat.VTT)
        
        # Create output
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        temp_file.write(b"output content")
        temp_file.close()
        temp_storage.save_output(video_id, temp_file.name)
        
        # Verify all files exist
        assert (temp_storage.uploads_dir / f"{video_id}.mp4").exists()
        assert (temp_storage.captions_dir / f"{video_id}.srt").exists()
        assert (temp_storage.captions_dir / f"{video_id}.vtt").exists()
        assert (temp_storage.outputs_dir / f"{video_id}.mp4").exists()
        
        # Delete all video files
        temp_storage.delete_video_files(video_id)
        
        # Verify all files are deleted
        assert not (temp_storage.uploads_dir / f"{video_id}.mp4").exists()
        assert not (temp_storage.captions_dir / f"{video_id}.srt").exists()
        assert not (temp_storage.captions_dir / f"{video_id}.vtt").exists()
        assert not (temp_storage.outputs_dir / f"{video_id}.mp4").exists()
    
    def test_delete_video_files_handles_missing_files(self, temp_storage):
        """
        Test that delete_video_files handles missing files gracefully.
        
        Validates: Requirements 8.3
        """
        video_id = "nonexistent-video"
        
        # Should not raise an error
        temp_storage.delete_video_files(video_id)
    
    def test_get_file_path_returns_correct_path(self, temp_storage):
        """
        Test that get_file_path returns the correct full path for existing files.
        
        Validates: Requirements 8.1
        """
        # Create a test file
        content = b"test content"
        filename = "test.mp4"
        file_id = temp_storage.save_upload(content, filename)
        
        # Get file path
        path = temp_storage.get_file_path(file_id, 'upload')
        
        assert path is not None
        assert os.path.exists(path)
        assert path.endswith(file_id)
    
    def test_get_file_path_returns_none_for_nonexistent_file(self, temp_storage):
        """
        Test that get_file_path returns None for nonexistent files.
        
        Validates: Requirements 8.1
        """
        path = temp_storage.get_file_path("nonexistent.mp4", 'upload')
        assert path is None
    
    def test_get_file_path_returns_none_for_invalid_type(self, temp_storage):
        """
        Test that get_file_path returns None for invalid file types.
        
        Validates: Requirements 8.1
        """
        path = temp_storage.get_file_path("test.mp4", 'invalid_type')
        assert path is None
    
    def test_get_file_path_works_for_all_types(self, temp_storage):
        """
        Test that get_file_path works for all file types.
        
        Validates: Requirements 8.1
        """
        # Create files of each type
        upload_id = temp_storage.save_upload(b"video", "test.mp4")
        watermark_id = temp_storage.save_watermark(b"image", "logo.png")
        caption_id = temp_storage.save_caption("caption", "vid123", CaptionFormat.SRT)
        
        # Create output
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        temp_file.write(b"output")
        temp_file.close()
        output_id = temp_storage.save_output("vid123", temp_file.name)
        
        # Verify all paths can be retrieved
        assert temp_storage.get_file_path(upload_id, 'upload') is not None
        assert temp_storage.get_file_path(watermark_id, 'watermark') is not None
        assert temp_storage.get_file_path(caption_id, 'caption') is not None
        assert temp_storage.get_file_path(output_id, 'output') is not None
    
    def test_detect_file_type(self, temp_storage):
        """
        Test file type detection from extension.
        
        Validates: Requirements 1.2, 4.1
        """
        assert temp_storage._detect_file_type("video.mp4") == "mp4"
        assert temp_storage._detect_file_type("video.MOV") == "mov"
        assert temp_storage._detect_file_type("video.AVI") == "avi"
        assert temp_storage._detect_file_type("logo.png") == "png"
        assert temp_storage._detect_file_type("logo.PNG") == "png"
    
    def test_unique_filename_format(self, temp_storage):
        """
        Test that generated filenames follow UUID format.
        
        Validates: Requirements 8.2
        """
        filename = temp_storage._generate_unique_filename("test.mp4")
        
        # Should have format: {uuid}.mp4
        parts = filename.rsplit('.', 1)
        assert len(parts) == 2
        assert parts[1] == "mp4"
        
        # UUID part should be 36 characters (including hyphens)
        uuid_part = parts[0]
        assert len(uuid_part) == 36
        assert uuid_part.count('-') == 4
