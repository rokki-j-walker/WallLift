# WallLift

WallLift is a Windows desktop app for preparing wallpapers and image batches. It
resizes images to a target minimum size while preserving proportions, and can use
AI upscaling when an image needs to be enlarged.

## Downloads

Prebuilt Windows packages are available on GitHub:

- Installer:
  https://github.com/rokki-j-walker/WallLift/releases/download/v0.1.2/WallLift-0.1.2-setup-windows-x64.exe
- Portable version:
  https://github.com/rokki-j-walker/WallLift/releases/download/v0.1.2/WallLift-0.1.2-windows-x64.zip

## Main Features

- Resize images from a folder or a manually selected file list.
- Preserve image proportions while targeting common monitor sizes.
- Save as JPG, PNG, WEBP, BMP, TIFF, or keep the source format.
- Copy originals unchanged when resizing is not needed.
- Process images in normal mode or multithreaded mode.
- Upscale enlarged images with Real-ESRGAN.
- Automatically analyze image style with CLIP and choose a suitable Real-ESRGAN model.
- Show progress, copied files, processed files, and errors during processing.
- Store settings and downloaded AI assets in the user profile.
- Check for new WallLift releases from the app.
- Provide English and Russian interface language packs.

## Run From Source

Create a virtual environment and install the runtime dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Start the app:

```powershell
.\.venv\Scripts\python.exe .\walllift.py
```

## User Data

WallLift stores settings and downloaded AI files in the Windows app data folder:

```text
%APPDATA%\WallLift
```

AI files are stored under:

```text
%APPDATA%\WallLift\ai
```

The app asks before downloading external AI components, shows the destination path,
and displays download progress.

The installer also offers an uninstall option to remove saved settings and
downloaded AI files.

## AI Upscaling

AI upscaling uses Real-ESRGAN through the ncnn Vulkan command-line runtime. Runtime
and model files are downloaded on demand and are not committed to this repository.

Pinned external assets:

- Real-ESRGAN ncnn Vulkan runtime `v0.2.0`:
  https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan/releases/tag/v0.2.0
- Real-ESRGAN models `v0.2.5.0`:
  https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.5.0

When AI mode is selected and required files are missing, WallLift can download them
into:

```text
%APPDATA%\WallLift\ai\tools\realesrgan-ncnn-vulkan
```

## Automatic Style Analysis

Automatic style analysis uses CLIP to classify an image and select a Real-ESRGAN
model. Anime and illustration-like images are routed to the anime model.

The main WallLift package does not bundle PyTorch or Transformers. Style analysis
runs through a separate helper executable that is downloaded only when automatic
style analysis is enabled.

Supported CLIP model:

- `openai/clip-vit-base-patch32`:
  https://huggingface.co/openai/clip-vit-base-patch32

The CLIP model is downloaded only after user confirmation and is stored in:

```text
%APPDATA%\WallLift\ai\models\clip-vit-base-patch32
```

If CLIP is unavailable or analysis fails, WallLift falls back to the selected
Real-ESRGAN model and continues processing.

## Updates

WallLift checks the latest GitHub release when the update button is pressed in the
settings window. If a newer installer is available, the app can download it to a
temporary folder and launch it.

## Localization

Interface language packs are stored in `lang/`. WallLift currently includes
English and Russian.

On first launch, the app asks which available language to use and saves that choice
in the settings file.

## Third-Party Projects

WallLift uses or integrates with:

- CustomTkinter: https://github.com/TomSchimansky/CustomTkinter
- Pillow: https://python-pillow.org/
- Real-ESRGAN ncnn Vulkan: https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan
- Real-ESRGAN models: https://github.com/xinntao/Real-ESRGAN
- Hugging Face Transformers: https://github.com/huggingface/transformers
- CLIP model: https://huggingface.co/openai/clip-vit-base-patch32
