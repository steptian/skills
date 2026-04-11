"""
cmd_learn 单元测试 - 验证教训写入的安全性
"""

import json
from unittest.mock import patch

import pytest


@pytest.fixture
def harness_dir(tmp_path):
    """创建临时 .harness 目录结构。"""
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()

    # 创建最小化的 features.json
    features_file = tmp_path / "features.json"
    features_file.write_text(json.dumps({
        "features": [{"id": "F001", "status": "pending", "description": "test"}],
        "sessions": [],
        "project": {},
    }))

    return tmp_path


@pytest.fixture
def learnings_file(harness_dir):
    """返回 learnings.json 路径。"""
    return harness_dir / "memory" / "learnings.json"


@pytest.fixture
def patched_paths(harness_dir):
    """patch learnings 模块的路径常量到临时目录。"""
    from lib import core
    return {
        'MEMORY_DIR': harness_dir / "memory",
        'LEARNINGS_FILE': harness_dir / "memory" / "learnings.json",
        'LOCK_FILE': harness_dir / ".features.lock",
        'HARNESS_DIR': harness_dir,
    }


def make_args(category="debugging", confidence=8, lesson="修改前先备份",
              context="直接改 config 导致格式损坏", feature_id="F001"):
    """创建 mock args 对象。"""
    class Args:
        pass
    a = Args()
    a.category = category
    a.confidence = confidence
    a.lesson = lesson
    a.context = context
    a.feature_id = feature_id
    return a


class TestCmdLearn:
    """cmd_learn 写入测试。"""

    def test_happy_path(self, harness_dir, learnings_file, patched_paths):
        """正常写入一条教训。"""
        with patch('lib.learnings.MEMORY_DIR', patched_paths['MEMORY_DIR']), \
             patch('lib.learnings.LEARNINGS_FILE', patched_paths['LEARNINGS_FILE']), \
             patch('lib.learnings.LOCK_FILE', patched_paths['LOCK_FILE']), \
             patch('lib.learnings.HARNESS_DIR', patched_paths['HARNESS_DIR']):
            from lib.learnings import cmd_learn
            cmd_learn(make_args())

        assert learnings_file.exists()
        data = json.loads(learnings_file.read_text())
        assert len(data['entries']) == 1
        entry = data['entries'][0]
        assert entry['lesson'] == "修改前先备份"
        assert entry['category'] == "debugging"
        assert entry['confidence'] == 8
        assert entry['feature_id'] == "F001"
        assert entry['injected'] == 0
        assert entry['id'] == "L001"

    def test_file_not_exist_creates_new(self, harness_dir, learnings_file, patched_paths):
        """learnings.json 不存在时自动创建。"""
        assert not learnings_file.exists()

        with patch('lib.learnings.MEMORY_DIR', patched_paths['MEMORY_DIR']), \
             patch('lib.learnings.LEARNINGS_FILE', patched_paths['LEARNINGS_FILE']), \
             patch('lib.learnings.LOCK_FILE', patched_paths['LOCK_FILE']):
            from lib.learnings import cmd_learn
            cmd_learn(make_args())

        assert learnings_file.exists()
        data = json.loads(learnings_file.read_text())
        assert len(data['entries']) == 1

    def test_corrupted_json_rebuilds(self, harness_dir, learnings_file, patched_paths):
        """损坏的 JSON 被重建为空结构（不崩溃）。"""
        learnings_file.write_text("NOT VALID JSON{{{")

        with patch('lib.learnings.MEMORY_DIR', patched_paths['MEMORY_DIR']), \
             patch('lib.learnings.LEARNINGS_FILE', patched_paths['LEARNINGS_FILE']), \
             patch('lib.learnings.LOCK_FILE', patched_paths['LOCK_FILE']):
            from lib.learnings import cmd_learn
            cmd_learn(make_args())

        data = json.loads(learnings_file.read_text())
        assert len(data['entries']) == 1

    def test_growth_control(self, harness_dir, learnings_file, patched_paths):
        """超过 100 条时淘汰低价值条目。"""
        entries = []
        for i in range(100):
            entries.append({
                "id": f"L{i+1:03d}",
                "ts": f"2026-04-01T00:{i%60:02d}:00",
                "feature_id": "F001",
                "category": "debugging",
                "lesson": f"旧教训 {i}",
                "context": "",
                "confidence": 5,
                "injected": 0,
            })
        learnings_file.write_text(json.dumps({"entries": entries}))

        with patch('lib.learnings.MEMORY_DIR', patched_paths['MEMORY_DIR']), \
             patch('lib.learnings.LEARNINGS_FILE', patched_paths['LEARNINGS_FILE']), \
             patch('lib.learnings.LOCK_FILE', patched_paths['LOCK_FILE']):
            from lib.learnings import cmd_learn
            cmd_learn(make_args(category="architecture", confidence=9,
                                lesson="新的高价值教训", feature_id="F002"))

        data = json.loads(learnings_file.read_text())
        assert len(data['entries']) == 100
        lessons = [e['lesson'] for e in data['entries']]
        assert "新的高价值教训" in lessons

    def test_confidence_boundary(self, harness_dir, learnings_file, patched_paths):
        """confidence 被约束在 1-10 范围内。"""
        with patch('lib.learnings.MEMORY_DIR', patched_paths['MEMORY_DIR']), \
             patch('lib.learnings.LEARNINGS_FILE', patched_paths['LEARNINGS_FILE']), \
             patch('lib.learnings.LOCK_FILE', patched_paths['LOCK_FILE']):
            from lib.learnings import cmd_learn
            cmd_learn(make_args(confidence=0, lesson="test low"))
            data = json.loads(learnings_file.read_text())
            assert data['entries'][0]['confidence'] == 1

            cmd_learn(make_args(confidence=15, lesson="test high"))
            data = json.loads(learnings_file.read_text())
            assert data['entries'][1]['confidence'] == 10

    def test_sequential_writes_no_data_loss(self, harness_dir, learnings_file, patched_paths):
        """连续写入不会丢失数据。"""
        with patch('lib.learnings.MEMORY_DIR', patched_paths['MEMORY_DIR']), \
             patch('lib.learnings.LEARNINGS_FILE', patched_paths['LEARNINGS_FILE']), \
             patch('lib.learnings.LOCK_FILE', patched_paths['LOCK_FILE']):
            from lib.learnings import cmd_learn
            for i in range(5):
                cmd_learn(make_args(lesson=f"教训 {i}", feature_id=""))

        data = json.loads(learnings_file.read_text())
        assert len(data['entries']) == 5
        lessons = [e['lesson'] for e in data['entries']]
        for i in range(5):
            assert f"教训 {i}" in lessons

    def test_id_auto_increment(self, harness_dir, learnings_file, patched_paths):
        """ID 自动递增。"""
        with patch('lib.learnings.MEMORY_DIR', patched_paths['MEMORY_DIR']), \
             patch('lib.learnings.LEARNINGS_FILE', patched_paths['LEARNINGS_FILE']), \
             patch('lib.learnings.LOCK_FILE', patched_paths['LOCK_FILE']):
            from lib.learnings import cmd_learn
            for i in range(3):
                cmd_learn(make_args(lesson=f"test {i}", feature_id=""))

        data = json.loads(learnings_file.read_text())
        ids = [e['id'] for e in data['entries']]
        assert ids == ["L001", "L002", "L003"]


class TestInjectLearnings:
    """教训注入测试。"""

    def test_inject_shows_recent(self, harness_dir, learnings_file, patched_paths, capsys):
        """注入最近的高 confidence 教训。"""
        entries = [
            {"id": "L001", "ts": "2026-04-10T00:00:00", "category": "debugging",
             "lesson": "旧教训", "context": "旧场景", "confidence": 7, "injected": 0},
            {"id": "L002", "ts": "2026-04-11T00:00:00", "category": "architecture",
             "lesson": "新教训", "context": "新场景", "confidence": 8, "injected": 0},
        ]
        learnings_file.write_text(json.dumps({"entries": entries}))

        with patch('lib.learnings.LEARNINGS_FILE', patched_paths['LEARNINGS_FILE']):
            from lib.learnings import inject_learnings_to_stdout
            inject_learnings_to_stdout()

        captured = capsys.readouterr()
        assert "--- PRIOR LEARNINGS ---" in captured.out
        assert "新教训" in captured.out

    def test_inject_skips_low_confidence(self, harness_dir, learnings_file, patched_paths, capsys):
        """confidence < 6 的教训不注入。"""
        entries = [
            {"id": "L001", "ts": "2026-04-11T00:00:00", "category": "debugging",
             "lesson": "低信心", "context": "", "confidence": 3, "injected": 0},
        ]
        learnings_file.write_text(json.dumps({"entries": entries}))

        with patch('lib.learnings.LEARNINGS_FILE', patched_paths['LEARNINGS_FILE']):
            from lib.learnings import inject_learnings_to_stdout
            inject_learnings_to_stdout()

        captured = capsys.readouterr()
        assert "--- PRIOR LEARNINGS ---" not in captured.out

    def test_inject_handles_missing_file(self, harness_dir, patched_paths, capsys):
        """learnings.json 不存在时不报错。"""
        with patch('lib.learnings.LEARNINGS_FILE', patched_paths['LEARNINGS_FILE']):
            from lib.learnings import inject_learnings_to_stdout
            inject_learnings_to_stdout()

        captured = capsys.readouterr()
        assert captured.out == ""
