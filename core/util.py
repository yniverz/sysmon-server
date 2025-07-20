
import dataclasses
import json
from typing import Any, Type

from attr import dataclass
from models import model_registry



@dataclass
class Config:
    dashboard_host: str = "0.0.0.0"
    dashboard_port: int = 5000
    dashboard_application_root: str = ""
    dashboard_username: str = "admin"
    dashboard_password: str = "admin"
    websocket_host: str = "0.0.0.0"
    websocket_port: int = 8765



class DataclassJSONEncoder(json.JSONEncoder):
    """
    Recursively adds a __type__ key to all dataclass instances,
    including nested ones like proxies inside clients.
    """
    def default(self, obj: Any) -> Any:
        if dataclasses.is_dataclass(obj):
            return self._encode_dataclass(obj)
        return super().default(obj)

    def _encode_dataclass(self, obj: Any) -> dict:
        result = {"__type__": obj.__class__.__name__}
        for field in dataclasses.fields(obj):
            value = getattr(obj, field.name)
            result[field.name] = self._encode_value(value)
        return result

    def _encode_value(self, value: Any) -> Any:
        if dataclasses.is_dataclass(value):
            return self._encode_dataclass(value)
        elif isinstance(value, list):
            return [self._encode_value(v) for v in value]
        elif isinstance(value, dict):
            return {k: self._encode_value(v) for k, v in value.items()}
        else:
            return value


class DataclassJSONDecoder(json.JSONDecoder):
    """
    Recreates nested dataclasses automatically via object_hook.
    """
    _registry: dict[str, Type] = model_registry

    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self._hook, *args, **kwargs)

    def _hook(self, obj: dict) -> Any:
        cls_name = obj.pop("__type__", None)
        if cls_name is not None:
            cls = self._registry.get(cls_name)
            if cls is None:
                raise ValueError(f"Unknown dataclass type: {cls_name}")
            # The inner objects (if any) have already been processed
            return cls(**obj)
        return obj
    
