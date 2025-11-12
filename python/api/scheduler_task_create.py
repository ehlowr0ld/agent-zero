from python.helpers.api import ApiHandler, Input, Output, Request
from agent import AgentContext
from python.helpers.task_scheduler import (
    TaskScheduler, ScheduledTask, AdHocTask, PlannedTask, TaskSchedule,
    serialize_task, parse_task_schedule, parse_task_plan, TaskType
)
from python.helpers.localization import Localization
from python.helpers.print_style import PrintStyle
from python.helpers import projects
from python.helpers.projects import ProjectSyncError
import random


class SchedulerTaskCreate(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        """
        Create a new task in the scheduler
        """
        printer = PrintStyle(italic=True, font_color="blue", padding=False)

        def error_payload(message: str, technical: object | None = None) -> Output:
            detail = message if technical is None else f"{message} (Technical: {technical})"
            return {"ok": False, "error": detail}

        # Get timezone from input (do not set if not provided, we then rely on poll() to set it)
        if timezone := input.get("timezone", None):
            Localization.get().set_timezone(timezone)

        scheduler = TaskScheduler.get()
        await scheduler.reload()

        # Get common fields from input
        name = input.get("name")
        system_prompt = input.get("system_prompt", "")
        prompt = input.get("prompt")
        attachments = input.get("attachments", [])
        context_id = input.get("context_id", None)

        raw_dedicated_context = input.get("dedicated_context", None)
        if raw_dedicated_context is None:
            dedicated_context = context_id is None
        elif isinstance(raw_dedicated_context, bool):
            dedicated_context = raw_dedicated_context
        else:
            return error_payload(
                "Please refresh the page and try again.",
                "dedicated_context must be a boolean if provided",
            )

        # Check if schedule is provided (for ScheduledTask)
        schedule = input.get("schedule", {})
        token: str = input.get("token", "")

        # Debug log the token value
        printer.print(f"Token received from frontend: '{token}' (type: {type(token)}, length: {len(token) if token else 0})")

        # Generate a random token if empty or not provided
        if not token:
            token = str(random.randint(1000000000000000000, 9999999999999999999))
            printer.print(f"Generated new token: '{token}'")

        plan = input.get("plan", {})

        raw_project_name = input.get("project_name", None)
        if isinstance(raw_project_name, str):
            project_name = raw_project_name.strip() or None
        elif raw_project_name is None:
            project_name = None
        else:
            return error_payload(
                "Please choose a valid project or leave the field empty.",
                "project_name must be a string or null",
            )

        context_project_name = None
        if context_id:
            context = AgentContext.get(context_id)
            if not context:
                return error_payload(
                    "The selected chat is no longer available. Please refresh and try again.",
                    f"context {context_id} not found",
                )
            context_project_name = projects.get_context_project_name(context)
            if isinstance(context_project_name, str):
                context_project_name = context_project_name.strip() or None

        if not dedicated_context:
            if not context_id:
                return error_payload(
                    "Shared-context tasks must be created from within a chat via the scheduler tool. Either call the tool inside the desired chat or create a dedicated-context task instead.",
                    "context_id missing for shared task",
                )
            if project_name is not None and project_name != context_project_name:
                return error_payload(
                    "Shared-context tasks follow the chat's active project. Switch the chat project or choose a dedicated context.",
                    f"shared-context project mismatch (chat={context_project_name}, submitted={project_name})",
                )
            project_name = context_project_name
        else:
            # Dedicated tasks keep the manually selected project (if any)
            project_name = project_name

        if project_name:
            try:
                projects.load_basic_project_data(project_name)
            except projects.ProjectNotFoundError as exc:
                return error_payload(
                    "The selected project no longer exists. Please refresh and try again.",
                    exc,
                )

        # Validate required fields
        if not name or not prompt:
            return error_payload(
                "Missing required fields: name and prompt must be provided.",
                "name/prompt missing",
            )

        try:
            task = None
            if schedule:
                if isinstance(schedule, str):
                    parts = schedule.split(' ')
                    task_schedule = TaskSchedule(
                        minute=parts[0] if len(parts) > 0 else "*",
                        hour=parts[1] if len(parts) > 1 else "*",
                        day=parts[2] if len(parts) > 2 else "*",
                        month=parts[3] if len(parts) > 3 else "*",
                        weekday=parts[4] if len(parts) > 4 else "*"
                    )
                elif isinstance(schedule, dict):
                    try:
                        task_schedule = parse_task_schedule(schedule)
                    except ValueError as exc:
                        return error_payload("Schedule format is invalid. Please review the cron fields.", exc)
                else:
                    return error_payload("Invalid schedule format. Must be string or object.")

                task = ScheduledTask.create(
                    name=name,
                    system_prompt=system_prompt,
                    prompt=prompt,
                    schedule=task_schedule,
                    attachments=attachments,
                    context_id=context_id,
                    timezone=timezone,
                    project_name=project_name,
                    dedicated_context=dedicated_context,
                )
            elif plan:
                try:
                    task_plan = parse_task_plan(plan)
                except ValueError as exc:
                    return error_payload("Plan format is invalid. Please verify the timeline entries.", exc)

                task = PlannedTask.create(
                    name=name,
                    system_prompt=system_prompt,
                    prompt=prompt,
                    plan=task_plan,
                    attachments=attachments,
                    context_id=context_id,
                    project_name=project_name,
                    dedicated_context=dedicated_context,
                )
            else:
                printer.print(f"Creating AdHocTask with token: '{token}'")
                task = AdHocTask.create(
                    name=name,
                    system_prompt=system_prompt,
                    prompt=prompt,
                    token=token,
                    attachments=attachments,
                    context_id=context_id,
                    project_name=project_name,
                    dedicated_context=dedicated_context,
                )
                if isinstance(task, AdHocTask):
                    printer.print(f"AdHocTask created with token: '{task.token}'")

            await scheduler.add_task(task)

            saved_task = scheduler.get_task_by_uuid(task.uuid)
            if saved_task:
                if saved_task.type == TaskType.AD_HOC and isinstance(saved_task, AdHocTask):
                    printer.print(f"Task verified after save, token: '{saved_task.token}'")
                else:
                    printer.print("Task verified after save, not an adhoc task")
            else:
                printer.print("WARNING: Task not found after save!")

            task_dict = serialize_task(task)
            if task_dict and task_dict.get('type') == 'adhoc':
                printer.print(f"Serialized adhoc task, token in response: '{task_dict.get('token')}'")

            return {"ok": True, "data": task_dict}

        except ValueError as exc:
            PrintStyle.error(f"[scheduler_task_create] Validation error: {exc}")
            return error_payload("Unable to create the task with the provided information.", exc)
        except ProjectSyncError as exc:
            PrintStyle.error(f"[scheduler_task_create] Project synchronization failed: {exc}")
            return error_payload(
                "Unable to associate this task with the selected project right now.",
                exc,
            )
        except Exception as exc:
            PrintStyle.error(f"[scheduler_task_create] Unexpected failure: {exc}")
            return error_payload("Unexpected error while creating the task.", exc)
