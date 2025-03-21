import json
import os

from python.helpers import files


class ChatNames:
    _instance = None
    _names_file = "chat_names.json"

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ChatNames()
            cls._instance._names_file = files.get_abs_path("tmp") + "/" + cls._names_file
        return cls._instance

    def _read_names(self) -> dict:
        """Read current names from file"""
        try:
            if os.path.exists(self._names_file):
                with open(self._names_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error reading chat names: {e}")
        return {}

    def _save_names(self, names: dict):
        """Save names to file"""
        try:
            with open(self._names_file, 'w') as f:
                json.dump(names, f, indent=2)
        except Exception as e:
            print(f"Error saving chat names: {e}")

    def set_name(self, chat_id: str, name: str):
        names = self._read_names()
        names[chat_id] = name
        self._save_names(names)

    def get_name(self, chat_id: str) -> str:
        names = self._read_names()
        return names.get(chat_id, f"Chat #{chat_id[:8]}")

    def remove_chat(self, chat_id: str):
        print("Removing chat name: ", chat_id)
        names = self._read_names()
        if chat_id in names:
            del names[chat_id]
            print("Chat name removed: ", chat_id)
            self._save_names(names)
