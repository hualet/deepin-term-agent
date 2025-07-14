"""Tests for built-in tools."""

import asyncio
import tempfile
import os
from pathlib import Path

import pytest

from deepin_term_agent.tools.builtin import (
    CommandRunner,
    FileReader,
    FileWriter,
    LogReader,
    DirectoryLister,
)


class TestCommandRunner:
    
    @pytest.mark.asyncio
    async def test_successful_command(self):
        """Test successful command execution."""
        result = await CommandRunner.execute({"command": "echo 'hello world'"})
        
        assert result["success"] is True
        assert result["return_code"] == 0
        assert "hello world" in result["stdout"]
    
    @pytest.mark.asyncio
    async def test_failed_command(self):
        """Test failed command execution."""
        result = await CommandRunner.execute({"command": "false"})
        
        assert result["success"] is False
        assert result["return_code"] == 1
    
    @pytest.mark.asyncio
    async def test_timeout(self):
        """Test command timeout."""
        result = await CommandRunner.execute({
            "command": "sleep 2",
            "timeout": 1
        })
        
        assert result["success"] is False
        assert "timeout" in result["error"]


class TestFileReader:
    
    @pytest.mark.asyncio
    async def test_read_existing_file(self):
        """Test reading an existing file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            result = await FileReader.execute({"file_path": temp_path})
            
            assert result["success"] is True
            assert result["content"] == "test content"
            assert result["size"] > 0
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self):
        """Test reading a non-existent file."""
        result = await FileReader.execute({"file_path": "/nonexistent/file"})
        
        assert result["success"] is False
        assert "not found" in result["error"]


class TestFileWriter:
    
    @pytest.mark.asyncio
    async def test_write_file(self):
        """Test writing to a file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.txt")
            
            result = await FileWriter.execute({
                "file_path": file_path,
                "content": "test content"
            })
            
            assert result["success"] is True
            assert os.path.exists(file_path)
            
            with open(file_path) as f:
                assert f.read() == "test content"
    
    @pytest.mark.asyncio
    async def test_create_directories(self):
        """Test creating directories when writing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "new", "dir", "test.txt")
            
            result = await FileWriter.execute({
                "file_path": file_path,
                "content": "test",
                "create_directories": True
            })
            
            assert result["success"] is True
            assert os.path.exists(file_path)


class TestDirectoryLister:
    
    @pytest.mark.asyncio
    async def test_list_current_directory(self):
        """Test listing current directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some test files
            Path(temp_dir, "file1.txt").write_text("test")
            Path(temp_dir, "subdir").mkdir()
            
            result = await DirectoryLister.execute({"directory": temp_dir})
            
            assert result["success"] is True
            assert result["directory"] == str(Path(temp_dir).resolve())
            assert result["total"] >= 2
            
            # Check if our test files are listed
            names = [item["name"] for item in result["items"]]
            assert "file1.txt" in names
            assert "subdir" in names
    
    @pytest.mark.asyncio
    async def test_list_nonexistent_directory(self):
        """Test listing non-existent directory."""
        result = await DirectoryLister.execute({"directory": "/nonexistent/dir"})
        
        assert result["success"] is False
        assert "not found" in result["error"]