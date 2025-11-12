import json
import os

from agent import AgentContext
from python.helpers.api import ApiHandler, Input, Output, Request
from python.helpers import projects, persist_chat, files
from python.helpers.print_style import PrintStyle
from python.helpers.task_scheduler import TaskScheduler


class ProjectDeletionBlockedError(Exception):
    def __init__(
        self,
        message: str,
        *,
        project_name: str,
        project_title: str,
        blocking_tasks: list[dict],
    ):
        super().__init__(message)
        self.project_name = project_name
        self.project_title = project_title
        self.blocking_tasks = blocking_tasks


class Projects(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        action = input.get("action", "")
        ctxid = input.get("context_id", None)

        if ctxid:
            _context = self.use_context(ctxid)

        try:
            if action == "list":
                data = self.get_active_projects_list()
            elif action == "load":
                data = self.load_project(input.get("name", None))
            elif action == "create":
                data = self.create_project(input.get("project", None))
            elif action == "update":
                data = self.update_project(input.get("project", None))
            elif action == "delete":
                data = await self.delete_project(input.get("name", None))
            elif action == "activate":
                data = self.activate_project(ctxid, input.get("name", None))
            elif action == "deactivate":
                data = self.deactivate_project(ctxid)
            else:
                raise Exception("Invalid action")

            return {
                "ok": True,
                "data": data,
            }
        except ProjectDeletionBlockedError as exc:
            return {
                "ok": False,
                "error": str(exc),
                "data": {
                    "project": {
                        "name": exc.project_name,
                        "title": exc.project_title,
                    },
                    "blocking_tasks": exc.blocking_tasks,
                },
            }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
            }

    def get_active_projects_list(self):
        return projects.get_active_projects_list()

    def create_project(self, project: dict|None):
        if project is None:
            raise Exception("Project data is required")
        data = projects.BasicProjectData(**project)
        name = projects.create_project(project["name"], data)
        return projects.load_edit_project_data(name)

    def load_project(self, name: str|None):
        if name is None:
            raise Exception("Project name is required")
        return projects.load_edit_project_data(name)

    def update_project(self, project: dict|None):
        if project is None:
            raise Exception("Project data is required")
        data = projects.EditProjectData(**project)
        name = projects.update_project(project["name"], data)
        return projects.load_edit_project_data(name)

    async def delete_project(self, name: str|None):
        if name is None:
            raise Exception("Project name is required")
        normalized = name.strip()
        if not normalized:
            raise Exception("Project name is required")

        scheduler = TaskScheduler.get()
        await scheduler.reload()
        blocking_tasks = scheduler.get_tasks_by_project_name(normalized)

        if blocking_tasks:
            project_header = projects.load_basic_project_data(normalized)
            project_title = project_header.get("title", "") or normalized
            blocking_payload = []
            segments = []

            for task in blocking_tasks:
                context_id = task.context_id or ""
                context_label = self._resolve_context_label(context_id)
                blocking_payload.append(
                    {
                        "task_id": task.uuid,
                        "task_name": task.name,
                        "context_id": context_id,
                        "context_name": context_label,
                        "project_name": normalized,
                    }
                )
                context_display = context_label or "chat"
                context_identifier = context_id or "no-context"
                task_display = task.name or "Untitled task"
                segments.append(
                    f"{task_display} ({task.uuid}) in {context_display} ({context_identifier})"
                )

            message = (
                f"Cannot delete project '{project_title}' ({normalized}) because these scheduler tasks still reference it: "
                + "; ".join(segments)
            )
            PrintStyle.error(f"[projects.delete] {message}")
            raise ProjectDeletionBlockedError(
                message,
                project_name=normalized,
                project_title=project_title,
                blocking_tasks=blocking_payload,
            )

        return projects.delete_project(normalized)

    def activate_project(self, context_id: str|None, name: str|None):
        if not context_id:
            raise Exception("Context ID is required")
        if not name:
            raise Exception("Project name is required")
        return projects.activate_project(context_id, name)

    def deactivate_project(self, context_id: str|None):
        if not context_id:
            raise Exception("Context ID is required")
        return projects.deactivate_project(context_id)

    @staticmethod
    def _resolve_context_label(context_id: str | None) -> str:
        if not context_id:
            return "Global Task"
        context = AgentContext.get(context_id)
        if context and context.name:
            return context.name
        try:
            chat_path = os.path.join(
                persist_chat.get_chat_folder_path(context_id),
                persist_chat.CHAT_FILE_NAME,
            )
            raw = files.read_file(chat_path)
            data = json.loads(raw)
            name = data.get("name")
            if name:
                return name
        except Exception:
            pass
        return context_id
