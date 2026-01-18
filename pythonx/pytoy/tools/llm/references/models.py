import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal, Self, assert_never, Any, Sequence
from urllib.parse import urlparse

import requests
from pydantic import Field, BaseModel, field_validator

type InfoSource = Literal["local", "web"]

type Extension = str  # It repesents the kind of resource.


class ReferencePathPair(BaseModel):
    info_path: Path
    markdown_path: Path


class ResourceUri(BaseModel, frozen=True):
    path: str
    source_type: InfoSource

    @classmethod
    def from_any(cls, value: Any) -> Self:
        if isinstance(value, Path):
            return cls(path=value.as_posix(), source_type="local")
        if isinstance(value, str):
            if value.startswith("http"):
                return cls(path=value, source_type="web")
        return cls.model_validate(value)

    @property
    def hash_id(self) -> str:
        return hashlib.sha256(self.path.encode()).hexdigest()[:16]

    @property
    def name(self) -> str:
        if self.source_type == "web":
            parsed = urlparse(self.path)
            return parsed.path.split("/")[-1] or parsed.netloc
        return Path(self.path).name

    @property
    def extension(self) -> Extension:
        return Path(self.name).suffix

    @property
    def hierarchy(self) -> list[str]:
        match self.source_type:
            case "web":
                parsed = urlparse(self.path)
                return [parsed.netloc] + [p for p in parsed.path.split("/") if p]
            case "local":
                p = Path(self.path)
                parts = list(p.parts)
                if len(parts) > 1:
                    _ = parts.pop()
                cleaned_parts = [item.replace(os.sep, "").replace("/", "") for item in parts if item]
                return [cp for cp in cleaned_parts if cp]
            case _:
                assert_never(self.source_type)


class ReferenceInfo(BaseModel):
    uri: Annotated[ResourceUri, Field(description="Location of the file")]
    timestamp: Annotated[float, Field(description="The updated time of `uri`.")]

    @field_validator("uri", mode="before")
    @classmethod
    def validate(cls, value: Any) -> ResourceUri:
        return ResourceUri.from_any(value)

    @classmethod
    def from_path(cls, path: Path, root_folder: Path) -> Self:
        timestamp = os.path.getmtime(path)
        relative_path = path.absolute().relative_to(root_folder.absolute())
        timestamp = os.path.getmtime(path)
        return cls(uri=ResourceUri.from_any(relative_path), timestamp=timestamp)

    @classmethod
    def from_address(cls, address: str) -> Self:
        try:
            response = requests.head(address, allow_redirects=True)
        except requests.HTTPError:
            timestamp = datetime.now().timestamp()
        else:
            last_mod = response.headers.get("Last-Modified")
            date_header = response.headers.get("Date")
            if last_mod:
                timestamp = datetime.strptime(last_mod, "%a, %d %b %Y %H:%M:%S %Z").timestamp()
            elif date_header:
                dt = datetime.strptime(date_header, "%a, %d %b %Y %H:%M:%S %Z")
                timestamp = dt.timestamp()
            else:
                timestamp = datetime.now().timestamp()
        return cls(
            uri=ResourceUri.from_any(address),
            timestamp=timestamp,
        )

    @property
    def source_type(self):
        return self.uri.source_type

    @property
    def hash_id(self) -> str:
        return self.uri.hash_id

    @property
    def hierarchy(self) -> list[str]:
        return self.uri.hierarchy

    @property
    def name(self) -> str:
        return self.uri.name

    @property
    def extension(self) -> str | None:
        return self.uri.extension


class DatasetMeta(BaseModel):
    root_folder: Path


class ReferenceDataset(BaseModel):
    meta: DatasetMeta
    path_pairs: Sequence[ReferencePathPair]

    def dump(self, folder: str | Path):
        folder = Path(folder)
        folder.mkdir(exist_ok=True, parents=True)
        data_dict = self.model_dump(mode="json")
        (folder / "meta.json").write_text(json.dumps(data_dict["meta"], indent=4, ensure_ascii=False), encoding="utf8", )
        (folder / "path_pairs.json").write_text(json.dumps(data_dict["path_pairs"], indent=4, ensure_ascii=False), encoding="utf8")

    @classmethod
    def load(cls, folder: str | Path) -> Self:
        folder = Path(folder)
        meta = json.loads( (folder / "meta.json").read_text(encoding="utf8"))
        path_pairs = json.loads( (folder / "path_pairs.json").read_text(encoding="utf8" ))
        return cls.model_validate({"meta": meta, "path_pairs": path_pairs})
