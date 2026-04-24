# WallLift

Local desktop utility for batch image resizing and optional AI upscaling.

## Run

```powershell
python walllift.py
```

## Languages

Interface language packs are stored in the `lang/` folder. WallLift currently includes English and Russian packs.

On first launch, the app asks which available language to use and saves that choice in the settings file.

## Real-ESRGAN

AI upscaling uses the third-party Real-ESRGAN ncnn Vulkan application. It is not included in this repository.

Original repository:
https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan

To use AI mode, download the Windows build of Real-ESRGAN ncnn Vulkan and extract it into the `rnv/` folder next to the project files, so the executable path is:

```text
rnv/realesrgan-ncnn-vulkan.exe
```
