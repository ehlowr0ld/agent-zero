import os
import uuid
from datetime import datetime
from typing import ClassVar
from pydantic import BaseModel, Field, PrivateAttr

from python.helpers.files import get_abs_path, exists, read_file, write_file


class Note(BaseModel):
    uid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class Notepad(BaseModel):
    uid: str
    notes: list[Note] = Field(default_factory=list)

    # Global notepad uid
    GLOBAL_NOTEPAD_UID: ClassVar[str] = "global"

    __instance: ClassVar[dict[str, "Notepad"]] = PrivateAttr(default=dict())

    @classmethod
    def get_instance(cls, uid: str | None = None) -> "Notepad":
        if uid is None:
            uid = str(uuid.uuid4())
        if uid not in cls.__instance:
            path = get_abs_path("memory/notepads", f"{uid}.json")
            if not exists(path):
                cls.__instance[uid] = cls(uid=uid)
                write_file(path, cls.__instance[uid].model_dump_json())
            else:
                cls.__instance[uid] = cls.model_validate_json(read_file(path))
        return cls.__instance[uid]

    @classmethod
    def get_global_instance(cls) -> "Notepad":
        return cls.get_instance(cls.GLOBAL_NOTEPAD_UID)

    @classmethod
    def delete_instance(cls, uid: str):
        path = get_abs_path("memory/notepads", f"{uid}.json")
        if exists(path):
            os.remove(path)
        if uid in cls.__instance:
            del cls.__instance[uid]

    def add_note(self, note: Note):
        self.notes.append(note)
        self._save()

    def update_note(self, uid: str, new_content: str):
        if note := self.get_note(uid):
            note.content = new_content
            self._save()
        else:
            raise ValueError(f"Note with uid {uid} not found")

    def get_note(self, uid: str) -> Note | None:
        return next((note for note in self.notes if note.uid == uid), None)

    def delete_note(self, uid: str):
        self.notes = [note for note in self.notes if note.uid != uid]
        self._save()

    def clear(self):
        self.notes = []
        self._save()

    def get_notes(self) -> list[Note]:
        return self.notes

    def get_notes_for_rendering(self) -> list[dict]:
        return [note.model_dump(mode="json", include={"uid", "content", "timestamp"}) for note in self.notes]

    def _save(self):
        path = get_abs_path("memory/notepads", f"{self.uid}.json")
        write_file(path, self.model_dump_json())
