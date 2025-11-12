import threading
from types import SimpleNamespace

import pytest
from flask import Flask

from agent import AgentContext
from python.api.scheduler_task_create import SchedulerTaskCreate
from python.helpers import projects
from python.helpers.api import ApiHandler
from python.helpers.task_scheduler import TaskScheduler


class StubScheduler:
    def __init__(self) -> None:
        self.tasks = {}
        self.add_calls = 0

    async def reload(self) -> None:
        return None

    async def add_task(self, task) -> None:
        self.add_calls += 1
        self.tasks[task.uuid] = task

    def get_task_by_uuid(self, task_id):
        return self.tasks.get(task_id)


class StubContext:
    def __init__(self, project_name: str | None) -> None:
        self._project_name = project_name

    def get_data(self, key: str, recursive: bool = True):
        if key == projects.CONTEXT_DATA_KEY_PROJECT:
            return self._project_name
        return None


@pytest.fixture
def handler() -> SchedulerTaskCreate:
    app = Flask("scheduler-task-create-test")
    instance = SchedulerTaskCreate.__new__(SchedulerTaskCreate)
    ApiHandler.__init__(instance, app=app, thread_lock=threading.Lock())
    return instance


@pytest.mark.asyncio
async def test_scheduler_task_create_rejects_shared_project_mismatch(monkeypatch, handler):
    stub_scheduler = StubScheduler()
    monkeypatch.setattr(TaskScheduler, "get", classmethod(lambda cls: stub_scheduler))

    context = StubContext("Project Alpha")
    monkeypatch.setattr(AgentContext, "get", staticmethod(lambda ctx_id: context if ctx_id == "ctx-123" else None))
    monkeypatch.setattr(projects, "load_basic_project_data", lambda name: {"name": name})

    response = await handler.process(
        {
            "name": "Example Task",
            "prompt": "Do something",
            "attachments": [],
            "context_id": "ctx-123",
            "project_name": "Project Beta",
            "dedicated_context": False,
        },
        request=None,
    )

    assert response["ok"] is False
    assert "Shared-context tasks follow the chat's active project" in response["error"]
    assert stub_scheduler.add_calls == 0


@pytest.mark.asyncio
async def test_scheduler_task_create_aligns_shared_project_with_chat(monkeypatch, handler):
    stub_scheduler = StubScheduler()
    monkeypatch.setattr(TaskScheduler, "get", classmethod(lambda cls: stub_scheduler))

    context = StubContext("Project Alpha")
    monkeypatch.setattr(AgentContext, "get", staticmethod(lambda ctx_id: context if ctx_id == "ctx-123" else None))
    monkeypatch.setattr(projects, "load_basic_project_data", lambda name: {"name": name})

    response = await handler.process(
        {
            "name": "Example Task",
            "prompt": "Do something",
            "attachments": [],
            "context_id": "ctx-123",
            "project_name": "Project Alpha",
            "dedicated_context": False,
        },
        request=None,
    )

    assert response["ok"] is True
    assert stub_scheduler.add_calls == 1
    created_task = next(iter(stub_scheduler.tasks.values()))
    assert created_task.project_name == "Project Alpha"
    assert created_task.is_dedicated_context() is False
    assert created_task.context_id == "ctx-123"


@pytest.mark.asyncio
async def test_scheduler_task_create_preserves_dedicated_context_flag(monkeypatch, handler):
    stub_scheduler = StubScheduler()
    monkeypatch.setattr(TaskScheduler, "get", classmethod(lambda cls: stub_scheduler))

    monkeypatch.setattr(AgentContext, "get", staticmethod(lambda ctx_id: None))
    monkeypatch.setattr(projects, "load_basic_project_data", lambda name: {"name": name})

    response = await handler.process(
        {
            "name": "Dedicated Task",
            "prompt": "Work in dedicated context",
            "attachments": [],
            "project_name": "Project Gamma",
            "dedicated_context": True,
        },
        request=None,
    )

    assert response["ok"] is True
    assert stub_scheduler.add_calls == 1
    created_task = next(iter(stub_scheduler.tasks.values()))
    assert created_task.is_dedicated_context() is True
    assert created_task.project_name == "Project Gamma"


@pytest.mark.asyncio
async def test_scheduler_task_create_defaults_to_dedicated_when_no_context(monkeypatch, handler):
    stub_scheduler = StubScheduler()
    monkeypatch.setattr(TaskScheduler, "get", classmethod(lambda cls: stub_scheduler))

    monkeypatch.setattr(projects, "load_basic_project_data", lambda name: {"name": name})

    response = await handler.process(
        {
            "name": "UI Task",
            "prompt": "Created from scheduler UI",
            "attachments": [],
            "project_name": "Project Delta",
        },
        request=None,
    )

    assert response["ok"] is True
    created_task = next(iter(stub_scheduler.tasks.values()))
    assert created_task.is_dedicated_context() is True
    assert created_task.context_id == created_task.uuid
    assert created_task.project_name == "Project Delta"
