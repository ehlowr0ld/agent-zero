from python.helpers.tool import Tool, Response
from python.helpers.aider import (
    create_streaming_aider_coder,
)
from python.helpers.print_style import PrintStyle


class CodingAgentTool(Tool):

    async def execute(self, **kwargs):
        files = kwargs.get("files", [])
        if not isinstance(files, list):
            if files:
                files = [files]
            else:
                files = []

        read_only_files = kwargs.get("read_only_files", [])
        if not isinstance(read_only_files, list):
            if read_only_files:
                read_only_files = [read_only_files]
            else:
                read_only_files = []

        dry_run = kwargs.get("dry_run", False)

        root_path = kwargs.get("root_path", None)
        if not root_path:
            return Response(message="No root path provided", break_loop=False)

        task = kwargs.get("task", None)
        if not task:
            return Response(message="No task provided", break_loop=False)

        def log_callback(response_type: str, content: str):
            self.log.stream(content=output_capture.get_output())

        response = None
        try:
            coder, output_capture = create_streaming_aider_coder(
                files=files,
                git_repo_path=root_path,
                dry_run=bool(dry_run),
                verbose=False,
                suppress_terminal_output=True,
                read_only_fnames=read_only_files,
            )

            coder.add_response_callback(log_callback)
            result = await coder.run_with_streaming_async(task)
            if result.get("success"):
                response = result.get("result", "No response provided by agent")
            else:
                response = "Error: " + result.get("result", "No response provided by agent")
            # PrintStyle().print(output_capture.get_output())
        except Exception as e:
            PrintStyle().error(f"Error: {e}")
            response = f"Error: {e}"

        return Response(message=response, break_loop=False)
