"""main.py — Lossless PNG Converter для Android (Kivy)."""
from pathlib import Path
from PIL import Image, ImageOps

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.utils import platform

SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif"}

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    SUPPORTED_EXT |= {".heic", ".heif"}
except Exception:
    pass


def default_output_dir() -> Path:
    if platform == "android":
        base = Path("/storage/emulated/0/Pictures/PNG_converted")
    else:
        base = Path.home() / "PNG_converted"
    try:
        base.mkdir(parents=True, exist_ok=True)
    except Exception:
        base = Path.home()
    return base


def convert_one(src_path: Path, out_dir: Path):
    try:
        with Image.open(src_path) as im:
            im = ImageOps.exif_transpose(im)
            if im.mode in ("P", "PA"):
                im = im.convert("RGBA")
            elif im.mode == "CMYK":
                im = im.convert("RGB")
            elif im.mode not in ("RGB", "RGBA", "L", "LA", "I;16", "I"):
                im = im.convert("RGBA" if "A" in im.getbands() else "RGB")

            exif_bytes = im.info.get("exif")
            icc = im.info.get("icc_profile")
            out_path = out_dir / f"{src_path.stem}.png"

            kwargs = {"format": "PNG", "compress_level": 6, "optimize": False}
            if exif_bytes:
                kwargs["exif"] = exif_bytes
            if icc:
                kwargs["icc_profile"] = icc
            im.save(out_path, **kwargs)
        return True, f"OK  {src_path.name}"
    except Exception as e:
        return False, f"ERR {src_path.name}: {e}"


def request_perms():
    if platform != "android":
        return
    try:
        from android.permissions import request_permissions, Permission
        perms = []
        for name in ("READ_MEDIA_IMAGES", "READ_EXTERNAL_STORAGE", "WRITE_EXTERNAL_STORAGE"):
            p = getattr(Permission, name, None)
            if p:
                perms.append(p)
        if perms:
            request_permissions(perms)
    except Exception:
        pass


class Root(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", padding=12, spacing=10, **kw)
        self.out_dir = default_output_dir()
        self.add_widget(Label(text="Lossless PNG Converter",
                              size_hint_y=None, height=40, font_size=20, bold=True))
        self.add_widget(Label(text=f"Output: {self.out_dir}",
                              size_hint_y=None, height=30, font_size=11))
        self.add_widget(Button(text="Convert single file…", size_hint_y=None,
                               height=56, on_release=self.pick_file))
        self.add_widget(Button(text="Convert whole folder…", size_hint_y=None,
                               height=56, on_release=self.pick_folder))
        self.log = TextInput(readonly=True, font_size=11)
        self.add_widget(self.log)

    def write(self, s):
        self.log.text += s + "\n"

    def pick_file(self, *_): self._open_chooser(False)
    def pick_folder(self, *_): self._open_chooser(True)

    def _open_chooser(self, dirselect):
        start = "/storage/emulated/0" if platform == "android" else str(Path.home())
        fc = FileChooserListView(path=start)
        box = BoxLayout(orientation="vertical")
        box.add_widget(fc)
        btns = BoxLayout(size_hint_y=None, height=50, spacing=8)
        popup = Popup(title="Choose", content=box, size_hint=(0.95, 0.95))

        def on_ok(*_):
            popup.dismiss()
            if dirselect:
                files = [p for p in Path(fc.path).rglob("*")
                         if p.is_file() and p.suffix.lower() in SUPPORTED_EXT]
            else:
                files = [Path(p) for p in fc.selection
                         if Path(p).suffix.lower() in SUPPORTED_EXT]
            self._run_batch(files)

        btns.add_widget(Button(text="Cancel", on_release=lambda *_: popup.dismiss()))
        btns.add_widget(Button(text="OK", on_release=on_ok))
        box.add_widget(btns)
        popup.open()

    def _run_batch(self, files):
        if not files:
            self.write("No files selected.")
            return
        self.write(f"Converting {len(files)} file(s)…")
        Clock.schedule_once(lambda dt: self._do(files), 0.1)

    def _do(self, files):
        ok = err = 0
        for f in files:
            success, msg = convert_one(f, self.out_dir)
            self.write(msg)
            ok += success
            err += not success
        self.write(f"Done. OK={ok}, ERR={err}")


class PngApp(App):
    def build(self):
        request_perms()
        return Root()


if __name__ == "__main__":
    PngApp().run()
