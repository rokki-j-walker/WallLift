# WallLift

WallLift is a local desktop utility for preparing wallpapers and other image batches.
It resizes images to a target minimum size while preserving aspect ratio, and can
optionally use AI upscaling when an image needs to be enlarged.

## Features

- Batch resize images from a folder or a manually selected file list.
- Preserve image proportions while targeting common monitor sizes.
- Save as JPG, PNG, WEBP, BMP, TIFF, or keep the source format.
- Copy originals unchanged when resizing is not needed.
- Run normal single-threaded processing or multithreaded processing without AI.
- Use Real-ESRGAN AI upscaling for enlargement.
- Automatically analyze image style with CLIP and choose an appropriate Real-ESRGAN model.
- Show progress, copied files, processed files, and errors during processing.
- Store settings in the user profile instead of the project folder.
- Provide English and Russian interface language packs.

## Run

```powershell
.\.venv\Scripts\python.exe .\walllift.py
```

If the virtual environment is missing or dependencies were installed into a
different Python, recreate the local environment:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Build EXE

Build the Windows application with PyInstaller:

```powershell
.\build_exe.ps1
```

The executable is created at `dist\WallLift\WallLift.exe`.

Prebuilt Windows releases are available on GitHub:

```text
https://github.com/rokki-j-walker/ImageSizer/releases/download/v0.1.1/WallLift-0.1.1-windows-x64.zip
```

## Settings And Downloaded Assets

WallLift stores user settings and downloaded AI assets in the application settings
folder. On Windows this is:

```text
%APPDATA%\WallLift
```

AI assets are stored under:

```text
%APPDATA%\WallLift\ai
```

WallLift asks before downloading external AI files, shows the destination path, and
displays download progress.

## AI Upscaling

AI upscaling uses Real-ESRGAN through the ncnn Vulkan command-line runtime. The
runtime and model files are not committed to this repository.

WallLift currently supports these pinned external assets:

- Runtime: Real-ESRGAN ncnn Vulkan `v0.2.0`
  https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan/releases/tag/v0.2.0
- Models: Real-ESRGAN `v0.2.5.0`
  https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.5.0

When AI mode is used and the supported runtime or models are missing, WallLift can
download them automatically into:

```text
%APPDATA%\WallLift\ai\tools\realesrgan-ncnn-vulkan
```

## Automatic Style Analysis

When automatic style analysis is enabled, WallLift uses CLIP to classify the image
style and pick a Real-ESRGAN model. For example, anime and illustration-like images
are routed to the anime model.

The supported CLIP model is:

- `openai/clip-vit-base-patch32`
  https://huggingface.co/openai/clip-vit-base-patch32

WallLift downloads this model only after asking the user. It is stored in:

```text
%APPDATA%\WallLift\ai\models\clip-vit-base-patch32
```

If CLIP is unavailable or analysis fails, WallLift falls back to the selected
Real-ESRGAN model and continues processing.

## Third-Party Projects

WallLift uses or integrates with:

- CustomTkinter for the desktop UI:
  https://github.com/TomSchimansky/CustomTkinter
- Pillow for standard image loading, resizing, and saving:
  https://python-pillow.org/
- Real-ESRGAN ncnn Vulkan for portable AI upscaling:
  https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan
- Real-ESRGAN model releases:
  https://github.com/xinntao/Real-ESRGAN
- Hugging Face Transformers and CLIP for automatic style analysis:
  https://github.com/huggingface/transformers
  https://huggingface.co/openai/clip-vit-base-patch32

## Languages

Interface language packs are stored in the `lang/` folder. WallLift currently
includes English and Russian packs.

On first launch, the app asks which available language to use and saves that choice
in the settings file.
