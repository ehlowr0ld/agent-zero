from python.helpers.api import ApiHandler, Input, Output, Request
from python.helpers.task_scheduler import (
    TaskScheduler, ScheduledTask, AdHocTask, PlannedTask, TaskState,
    serialize_task, parse_task_schedule, parse_task_plan
)
from agent import AgentContext
from python.helpers.localization import Localization
from python.helpers import projects
from python.helpers.projects import ProjectNotFoundError, ProjectSyncError
from python.helpers.print_style import PrintStyle


class SchedulerTaskUpdate(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        """
        Update an existing task in the scheduler
        """
        def error_payload(message: str, technical: object | None = None) -> Output:
            detail = message if technical is None else f"{message} (Technical: {technical})"
            return {"ok": False, "error": detail}

        # Get timezone from input (do not set if not provided, we then rely on poll() to set it)
        if timezone := input.get("timezone", None):
            Localization.get().set_timezone(timezone)

        scheduler = TaskScheduler.get()
        await scheduler.reload()

        # Get task ID from input
        task_id: str = input.get("task_id", "")

        if not task_id:
            return error_payload("Missing required field: task_id.")

        # Get the task to update
        task = scheduler.get_task_by_uuid(task_id)

        if not task:
            return error_payload("We could not find that task. Please refresh and try again.", f"Task {task_id} not found")

        # Update fields if provided using the task's update method
        update_params = {}
        project_update_requested = "project_name" in input
        desired_project = None
        previous_project = task.project_name

        if project_update_requested:
            desired_project = input.get("project_name", None)
            if isinstance(desired_project, str):
                desired_project = desired_project.strip() or None
            elif desired_project is not None:
                return error_payload(
                    "Please select a valid project or leave the field empty.",
                    "project_name must be string or null",
                )

            if not task.is_dedicated_context():
                # Reject modifications for shared-context tasks
                if desired_project != task.project_name:
                    return error_payload(
                        "This task shares a chat context, so change the chat's project instead.",
                        "shared-context project edit blocked",
                    )
                # Ignore redundant updates that match current value
                project_update_requested = False
            else:
                # Validate dedicated-context project change
                try:
                    if desired_project:
                        projects.load_basic_project_data(desired_project)
                except ProjectNotFoundError as exc:
                    return error_payload(
                        "Please select an existing project before saving.",
                        exc,
                    )
                if desired_project != previous_project:
                    update_params["project_name"] = desired_project
                else:
                    project_update_requested = False

        if "name" in input:
            update_params["name"] = input.get("name", "")

        if "state" in input:
            update_params["state"] = TaskState(input.get("state", TaskState.IDLE))

        if "system_prompt" in input:
            update_params["system_prompt"] = input.get("system_prompt", "")

        if "prompt" in input:
            update_params["prompt"] = input.get("prompt", "")

        if "attachments" in input:
            update_params["attachments"] = input.get("attachments", [])

        # Update schedule if this is a scheduled task and schedule is provided
        if isinstance(task, ScheduledTask) and "schedule" in input:
            schedule_data = input.get("schedule", {})
            try:
                # Parse the schedule with timezone handling
                task_schedule = parse_task_schedule(schedule_data)

                # Set the timezone from the request if not already in schedule_data
                if not schedule_data.get('timezone', None) and timezone:
                    task_schedule.timezone = timezone

                update_params["schedule"] = task_schedule
            except ValueError as e:
                return error_payload("Invalid schedule format. Please review the cron fields.", e)
        elif isinstance(task, AdHocTask) and "token" in input:
            token_value = input.get("token", "")
            if token_value:  # Only update if non-empty
                update_params["token"] = token_value
        elif isinstance(task, PlannedTask) and "plan" in input:
            plan_data = input.get("plan", {})
            try:
                # Parse the plan data
                task_plan = parse_task_plan(plan_data)
                update_params["plan"] = task_plan
            except ValueError as e:
                return error_payload("Invalid plan format. Please review the timeline entries.", e)

        if not update_params and not project_update_requested:
            serialized_existing = serialize_task(task)
            return {"ok": True, "data": serialized_existing}

        # Use atomic update method to apply changes
        try:
            updated_task = await scheduler.update_task(task_id, **update_params)
        except ValueError as exc:
            PrintStyle.error(f"[scheduler_task_update] Validation error: {exc}")
            return error_payload("Unable to update the task with the provided values.", exc)

        if not updated_task:
            return error_payload(
                "We could not update this task. Please refresh and try again.",
                f"Task {task_id} not found after update",
            )

        if project_update_requested and task.is_dedicated_context() and desired_project != previous_project:
            context_id = updated_task.context_id
            context = AgentContext.get(context_id) if context_id else None
            try:
                if desired_project and context:
                    scheduler._activate_project_or_raise(
                        context_id,
                        desired_project,
                        source="scheduler_task_update",
                    )
                elif desired_project is None and context:
                    projects.deactivate_project(context_id)
            except ProjectSyncError as exc:
                await scheduler.update_task(task_id, project_name=previous_project)
                return error_payload(
                    "Unable to update this task's project right now.",
                    exc,
                )
            except Exception as exc:
                PrintStyle.error(
                    f"[scheduler_task_update] Unexpected project sync failure for context '{context_id}': {exc}"
                )
                await scheduler.update_task(task_id, project_name=previous_project)
                return error_payload(
                    "Unable to update this task's project right now.",
                    exc,
                )

        # Return the updated task using our standardized serialization function
        task_dict = serialize_task(updated_task)

        return {"ok": True, "data": task_dict}
