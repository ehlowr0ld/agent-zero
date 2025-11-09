import os
from typing import Literal, TypedDict, TYPE_CHECKING

from python.helpers import files, dirty_json, persist_chat
from python.helpers.print_style import PrintStyle


if TYPE_CHECKING:
    from agent import AgentContext

PROJECTS_PARENT_DIR = "usr/projects"
PROJECT_META_DIR = ".a0proj"
PROJECT_INSTRUCTIONS_DIR = "instructions"
PROJECT_HEADER_FILE = "project.json"

CONTEXT_DATA_KEY_PROJECT = "project"
PROJECT_ERROR_FLAG = "_project_error_notified"


class ProjectNotFoundError(Exception):
    def __init__(
        self,
        name: str,
        message: str | None = None,
        context_id: str | None = None,
    ):
        if message is None:
            message = f"Project '{name}' not found or metadata is invalid"
        super().__init__(message)
        self.name = name
        self.context_id = context_id


class BasicProjectData(TypedDict):
    title: str
    description: str
    instructions: str
    color: str
    memory: Literal["own", "global"]  # in the future we can add cutom and point to another existing folder


class EditProjectData(BasicProjectData):
    name: str
    instruction_files_count: int
    variables: str
    secrets: str


def get_projects_parent_folder():
    return files.get_abs_path(PROJECTS_PARENT_DIR)


def get_project_folder(name: str):
    return files.get_abs_path(get_projects_parent_folder(), name)


def get_project_meta_folder(name: str):
    return files.get_abs_path(get_project_folder(name), PROJECT_META_DIR)


def delete_project(name: str):
    abs_path = files.get_abs_path(PROJECTS_PARENT_DIR, name)
    files.delete_dir(abs_path)
    deactivate_project_in_chats(name)
    return name


def create_project(name: str, data: BasicProjectData):
    abs_path = files.create_dir_safe(
        files.get_abs_path(PROJECTS_PARENT_DIR, name), rename_format="{name}_{number}"
    )
    files.create_dir(
        files.get_abs_path(abs_path, PROJECT_META_DIR, PROJECT_INSTRUCTIONS_DIR)
    )
    data = _normalizeBasicData(data)
    save_project_header(name, data)
    return name


def load_project_header(name: str):
    abs_path = files.get_abs_path(
        PROJECTS_PARENT_DIR, name, PROJECT_META_DIR, PROJECT_HEADER_FILE
    )
    try:
        raw = files.read_file(abs_path)
        header: dict = dirty_json.parse(raw)  # type: ignore
    except FileNotFoundError as exc:
        raise ProjectNotFoundError(name) from exc
    except Exception as exc:
        raise ProjectNotFoundError(
            name, f"Project '{name}' metadata could not be read: {exc}"
        ) from exc
    header["name"] = name
    return header


def _normalizeBasicData(data: BasicProjectData):
    return BasicProjectData(
        title=data.get("title", ""),
        description=data.get("description", ""),
        instructions=data.get("instructions", ""),
        color=data.get("color", ""),
        memory=data.get("memory", "own"),
    )


def _normalizeEditData(data: EditProjectData):
    return EditProjectData(
        name=data.get("name", ""),
        title=data.get("title", ""),
        description=data.get("description", ""),
        instructions=data.get("instructions", ""),
        variables=data.get("variables", ""),
        color=data.get("color", ""),
        instruction_files_count=data.get("instruction_files_count", 0),
        secrets=data.get("secrets", ""),
        memory=data.get("memory", "own"),
    )


def _edit_data_to_basic_data(data: EditProjectData):
    return _normalizeBasicData(data)  # type: ignore


def _basic_data_to_edit_data(data: BasicProjectData):
    return _normalizeEditData(data)  # type: ignore


def update_project(name: str, data: EditProjectData):
    # merge with current state
    current = load_edit_project_data(name)
    current.update(data)
    current = _normalizeEditData(current)

    # save header data
    header = _edit_data_to_basic_data(current)
    save_project_header(name, header)

    # save secrets
    save_project_variables(name, current["variables"])
    save_project_secrets(name, current["secrets"])

    reactivate_project_in_chats(name)
    return name


def load_basic_project_data(name: str) -> BasicProjectData:
    try:
        data = BasicProjectData(**load_project_header(name))
    except ProjectNotFoundError:
        raise
    except Exception as exc:
        raise ProjectNotFoundError(
            name, f"Project '{name}' metadata is invalid: {exc}"
        ) from exc
    normalized = _normalizeBasicData(data)
    return normalized


def load_edit_project_data(name: str) -> EditProjectData:
    try:
        data = load_basic_project_data(name)
        additional_instructions = get_additional_instructions_files(
            name
        )  # for additional info
        variables = load_project_variables(name)
        secrets = load_project_secrets_masked(name)
        data = EditProjectData(
            **data,
            name=name,
            instruction_files_count=len(additional_instructions),
            variables=variables,
            secrets=secrets,
        )
    except ProjectNotFoundError:
        raise
    except Exception as exc:
        raise ProjectNotFoundError(
            name, f"Project '{name}' metadata is invalid: {exc}"
        ) from exc
    data = _normalizeEditData(data)
    return data


def _project_error_group(context_id: str) -> str:
    return f"project-missing-{context_id}"


def has_project_error(context: "AgentContext") -> bool:
    return bool(context.get_data(PROJECT_ERROR_FLAG))


def clear_project_error(context: "AgentContext"):
    if has_project_error(context):
        context.data.pop(PROJECT_ERROR_FLAG, None)
        persist_chat.save_tmp_chat(context)


def mark_project_error(
    context: "AgentContext",
    project_name: str,
    message: str,
    *,
    source: str | None = None,
):
    first_detection = not has_project_error(context)
    if first_detection:
        context.set_data(PROJECT_ERROR_FLAG, True)
    detail = message
    if source:
        detail = f"{message}\nSource: {source}"
    if first_detection:
        PrintStyle.error(
            f"Context {context.id}: project '{project_name}' unavailable. {detail}"
        )
        context.log.log(
            type="error",
            heading="Project unavailable",
            content=detail,
            kvps={"project": project_name, "context": context.id},
        )
        from python.helpers.notification import (
            NotificationManager,
            NotificationPriority,
            NotificationType,
        )

        NotificationManager.send_notification(
            NotificationType.ERROR,
            NotificationPriority.HIGH,
            f"Project '{project_name}' is unavailable for context {context.id}.",
            title="Project unavailable",
            detail=detail,
            display_time=60,
            group=_project_error_group(context.id),
        )
    persist_chat.save_tmp_chat(context)


def ensure_context_project_ready(
    context: "AgentContext", source: str | None = None
):
    project_name = get_context_project_name(context)
    if not project_name:
        clear_project_error(context)
        return
    try:
        load_basic_project_data(project_name)
        clear_project_error(context)
    except ProjectNotFoundError as exc:
        mark_project_error(context, project_name, str(exc), source=source)
        raise ProjectNotFoundError(
            project_name, str(exc), context_id=context.id
        ) from exc


def save_project_header(name: str, data: BasicProjectData):
    # save project header file
    header = dirty_json.stringify(data)
    abs_path = files.get_abs_path(
        PROJECTS_PARENT_DIR, name, PROJECT_META_DIR, PROJECT_HEADER_FILE
    )

    files.write_file(abs_path, header)


def get_active_projects_list():
    return _get_projects_list(get_projects_parent_folder())


def _get_projects_list(parent_dir):
    projects = []

    # folders in project directory
    for name in os.listdir(parent_dir):
        try:
            abs_path = os.path.join(parent_dir, name)
            if os.path.isdir(abs_path):
                project_data = load_basic_project_data(name)
                projects.append(
                    {
                        "name": name,
                        "title": project_data.get("title", ""),
                        "description": project_data.get("description", ""),
                        "color": project_data.get("color", ""),
                    }
                )
        except Exception as e:
            PrintStyle.error(f"Error loading project {name}: {str(e)}")

    # sort projects by name
    projects.sort(key=lambda x: x["name"])
    return projects


def activate_project(context_id: str, name: str):
    from agent import AgentContext

    data = load_edit_project_data(name)
    context = AgentContext.get(context_id)
    if context is None:
        raise Exception("Context not found")
    display_name = str(data.get("title", name))
    display_name = display_name[:22] + "..." if len(display_name) > 25 else display_name
    context.set_data(CONTEXT_DATA_KEY_PROJECT, name)
    context.set_output_data(
        CONTEXT_DATA_KEY_PROJECT,
        {"name": name, "title": display_name, "color": data.get("color", "")},
    )
    clear_project_error(context)

    # persist
    persist_chat.save_tmp_chat(context)


def deactivate_project(context_id: str):
    from agent import AgentContext

    context = AgentContext.get(context_id)
    if context is None:
        raise Exception("Context not found")
    context.set_data(CONTEXT_DATA_KEY_PROJECT, None)
    context.set_output_data(CONTEXT_DATA_KEY_PROJECT, None)
    clear_project_error(context)

    # persist
    persist_chat.save_tmp_chat(context)


def reactivate_project_in_chats(name: str):
    from agent import AgentContext

    for context in AgentContext.all():
        if context.get_data(CONTEXT_DATA_KEY_PROJECT) == name:
            try:
                activate_project(context.id, name)
            except ProjectNotFoundError as exc:
                mark_project_error(
                    context,
                    name,
                    str(exc),
                    source="reactivate_project_in_chats",
                )
        persist_chat.save_tmp_chat(context)


def deactivate_project_in_chats(name: str):
    from agent import AgentContext

    for context in AgentContext.all():
        if context.get_data(CONTEXT_DATA_KEY_PROJECT) == name:
            deactivate_project(context.id)
        persist_chat.save_tmp_chat(context)


def build_system_prompt_vars(name: str):
    project_data = load_basic_project_data(name)
    main_instructions = project_data.get("instructions", "") or ""
    additional_instructions = get_additional_instructions_files(name)
    complete_instructions = (
        main_instructions
        + "\n\n".join(
            additional_instructions[k] for k in sorted(additional_instructions)
        )
    ).strip()
    return {
        "project_name": project_data.get("title", ""),
        "project_description": project_data.get("description", ""),
        "project_instructions": complete_instructions or "",
        "project_path": files.normalize_a0_path(get_project_folder(name)),
    }


def get_additional_instructions_files(name: str):
    instructions_folder = files.get_abs_path(
        get_project_folder(name), PROJECT_META_DIR, PROJECT_INSTRUCTIONS_DIR
    )
    return files.read_text_files_in_dir(instructions_folder)


def get_context_project_name(context: "AgentContext") -> str | None:
    return context.get_data(CONTEXT_DATA_KEY_PROJECT)


def load_project_variables(name: str):
    try:
        abs_path = files.get_abs_path(
            get_project_meta_folder(name), "variables.env"
        )
        return files.read_file(abs_path)
    except Exception:
        return ""


def save_project_variables(name: str, variables: str):
    abs_path = files.get_abs_path(
        get_project_meta_folder(name), "variables.env"
    )
    files.write_file(abs_path, variables)


def load_project_secrets_masked(name: str, merge_with_global=False):
    from python.helpers import secrets
    mgr = secrets.get_project_secrets_manager(name, merge_with_global)
    return mgr.get_masked_secrets()


def save_project_secrets(name: str, secrets: str):
    from python.helpers.secrets import get_project_secrets_manager
    secrets_manager = get_project_secrets_manager(name)
    secrets_manager.save_secrets_with_merge(secrets)


def get_context_memory_subdir(context: "AgentContext") -> str | None:
    # if a project is active and has memory isolation set, return the project memory subdir
    project_name = get_context_project_name(context)
    if project_name:
        project_data = load_basic_project_data(project_name)
        if project_data["memory"] == "own":
            return "projects/" + project_name
    return None  # no memory override
