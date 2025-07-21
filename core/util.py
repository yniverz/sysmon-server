
import dataclasses
from io import BytesIO
import json
from pathlib import Path
from PIL import Image
from typing import Any, Final, Sequence, Type

from dataclasses import dataclass

from flask import Response
from models import model_registry



@dataclass
class Config:
    dashboard_host: str = "localhost"
    dashboard_port: int = 5000
    dashboard_application_root: str = ""
    dashboard_username: str = "admin"
    dashboard_password: str = "admin"
    websocket_host: str = "0.0.0.0"
    websocket_port: int = 8765



class DataclassJSONEncoder(json.JSONEncoder):
    """
    Recursively adds a __type__ key to all dataclass instances
    """
    def default(self, obj: Any) -> Any:
        print(f"Encoding object of type {type(obj)}")
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
    


@dataclass
class SystemImage:

    base_name: str
    max_stack: int = 1
    stack_shift_x: int = 0
    stack_shift_y: int = 0
    base_folder: str = "core/templates/system_images"
    stackable: bool = True

    _PNG_MIMETYPE: Final[str] = "image/png"
    _CROP_MARGIN: Final[int] = 10       # px
    _MIN_SIZE: Final[int] = 1000        # px

    # ------------------------------------------------------------------ #
    #  Public interface                                                  #
    # ------------------------------------------------------------------ #
    def image(self, variations: Sequence[str]) -> Response:
        """
        Build an icon composed of the requested *variations* (bottom → top)
        and return it as a ready-to-send ``flask.Response``.

        Examples
        --------
        ``return battery_icon.image(["off", "dark", "on"])``
        """
        if not variations:
            raise ValueError("`variations` must contain at least one item")

        # Normal single‑frame response when stacking isn't needed / allowed
        if (
            len(variations) == 1
            or not self.stackable
            or self.max_stack <= 1
        ):
            pil_img = self._load(variations[0])
        else:
            pil_img = self._compose_layers(list(variations)[: self.max_stack])

        buf = BytesIO()
        pil_img.save(buf, format="PNG")
        return Response(buf.getvalue(), mimetype=self._PNG_MIMETYPE)

    def _compose_layers(self, variations: Sequence[str]) -> Image.Image:
        """Stack the given *variations* then crop & centre the result."""
        layers = [self._load(v) for v in variations]
        w, h = layers[0].size

        dx_total = self.stack_shift_x * (len(layers) - 1)
        dy_total = self.stack_shift_y * (len(layers) - 1)

        canvas = Image.new(
            "RGBA",
            (w + abs(dx_total), h + abs(dy_total)),
            (0, 0, 0, 0),
        )

        x0 = max(0, dx_total if self.stack_shift_x < 0 else 0)
        y0 = max(0, dy_total if self.stack_shift_y < 0 else 0)

        for i, layer in enumerate(layers):
            ox = x0 + i * self.stack_shift_x
            oy = y0 + i * self.stack_shift_y
            canvas.paste(layer, (ox, oy), layer)

        return self._crop_and_center(canvas)

    def _crop_and_center(self, img: Image.Image) -> Image.Image:
        """
        Crop to non-transparent pixels (±10 px margin), then ensure the
        canvas is at least 1000x1000 px and centre the glyph on it.
        """
        alpha = img.split()[-1]
        bbox = alpha.getbbox()  # (l, u, r, d) or None

        if bbox is None:                       # fully transparent
            cropped = img
        else:
            l, u, r, d = bbox
            l = max(l - self._CROP_MARGIN, 0)
            u = max(u - self._CROP_MARGIN, 0)
            r = min(r + self._CROP_MARGIN, img.width)
            d = min(d + self._CROP_MARGIN, img.height)
            cropped = img.crop((l, u, r, d))

        cw, ch = cropped.size
        final_w = max(cw, self._MIN_SIZE)
        final_h = max(ch, self._MIN_SIZE)

        if final_w == cw and final_h == ch:
            return cropped  # already meets min size

        canvas = Image.new("RGBA", (final_w, final_h), (0, 0, 0, 0))
        x_off = (final_w - cw) // 2
        y_off = (final_h - ch) // 2
        canvas.paste(cropped, (x_off, y_off), cropped)
        return canvas

    def _load(self, variation: str) -> Image.Image:
        """Load '<base_name>_<variation>.png' and return as RGBA PIL.Image."""
        path = Path(self.base_folder) / f"{self.base_name}_{variation}.png"
        return Image.open(path).convert("RGBA")



class SystemImageRegistry:
    def __init__(self):
        self._images: dict[str, SystemImage] = {}

    def register(self, image: SystemImage) -> None:
        self._images[image.base_name] = image

    # def get(self, base_name: str) -> SystemImage | None:
    #     return self._images.get(base_name)

    def get(self, base_name: str, variations: Sequence[str] = None) -> Response:
        if base_name not in self._images:
            raise ValueError(f"SystemImage '{base_name}' not registered.")
        image = self._images[base_name]
        if variations is None:
            variations = ["on"]
        return image.image(variations)
    
SYSTEM_IMAGES = SystemImageRegistry()
SYSTEM_IMAGES.register(SystemImage("server", max_stack=4, stack_shift_x=0, stack_shift_y=-115))
SYSTEM_IMAGES.register(SystemImage("desktop", max_stack=2, stack_shift_x=190, stack_shift_y=92))
SYSTEM_IMAGES.register(SystemImage("mini_desktop", max_stack=4, stack_shift_x=0, stack_shift_y=0))
SYSTEM_IMAGES.register(SystemImage("laptop", max_stack=1, stack_shift_x=0, stack_shift_y=0))
SYSTEM_IMAGES.register(SystemImage("mobile", max_stack=1, stack_shift_x=0, stack_shift_y=0))