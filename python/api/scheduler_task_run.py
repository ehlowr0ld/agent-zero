from python.helpers.api import ApiHandler, Input, Output, Request
from python.helpers.task_scheduler import TaskScheduler, TaskState
from python.helpers.projects import ProjectSyncError
from python.helpers.print_style import PrintStyle
from python.helpers.localization import Localization


class SchedulerTaskRun(ApiHandler):

    _printer: PrintStyle = PrintStyle(italic=True, font_color="green", padding=False)

    async def process(self, input: Input, request: Request) -> Output:
        """
        Manually run a task from the scheduler by ID
        """
        def error_payload(message: str, technical: object | None = None) -> Output:
            detail = message if technical is None else f"{message} (Technical: {technical})"
            return {"ok": False, "error": detail}

        # Get timezone from input (do not set if not provided, we then rely on poll() to set it)
        if timezone := input.get("timezone", None):
            Localization.get().set_timezone(timezone)

        # Get task ID from input
        task_id: str = input.get("task_id", "")

        if not task_id:
            return error_payload("Missing required field: task_id.")

        self._printer.print(f"SchedulerTaskRun: On-Demand running task {task_id}")

        scheduler = TaskScheduler.get()
        await scheduler.reload()

        # Check if the task exists first
        task = scheduler.get_task_by_uuid(task_id)
        if not task:
            self._printer.error(f"SchedulerTaskRun: Task with ID '{task_id}' not found")
            return error_payload("We could not find that task. Please refresh and try again.", f"Task {task_id} not found")

        # Check if task is already running
        if task.state == TaskState.RUNNING:
            # Return task details along with error for better frontend handling
            serialized_task = scheduler.serialize_task(task_id)
            self._printer.error(f"SchedulerTaskRun: Task '{task_id}' is in state '{task.state}' and cannot be run")
            return error_payload(
                f"Task '{task_id}' is already running. Please wait for it to finish.",
                f"state={task.state}",
            )

        # Run the task, which now includes atomic state checks and updates
        try:
            await scheduler.run_task_by_uuid(task_id)
            self._printer.print(f"SchedulerTaskRun: Task '{task_id}' started successfully")
            # Get updated task after run starts
            serialized_task = scheduler.serialize_task(task_id)
            if serialized_task:
                return {"ok": True, "data": serialized_task}
            return {"ok": True, "data": None}
        except ValueError as e:
            self._printer.error(f"SchedulerTaskRun: Task '{task_id}' failed to start: {str(e)}")
            return error_payload("Unable to run the task.", e)
        except ProjectSyncError as e:
            self._printer.error(f"SchedulerTaskRun: Task '{task_id}' project sync failed: {str(e)}")
            return error_payload("Unable to activate the required project for this task.", e)
        except Exception as e:
            self._printer.error(f"SchedulerTaskRun: Task '{task_id}' failed to start: {str(e)}")
            return error_payload(f"Failed to run task '{task_id}'.", e)
