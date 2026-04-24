# WallLift

Локальная утилита для пакетного изменения размера изображений и опционального AI-апскейла.

## Запуск

```powershell
python walllift.py
```

## Real-ESRGAN

AI-апскейл использует стороннюю программу Real-ESRGAN ncnn Vulkan. Она не хранится в этом репозитории.

Оригинальный репозиторий:
https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan

Для работы AI-режима скачайте Windows-сборку Real-ESRGAN ncnn Vulkan и распакуйте ее в папку `rnv/` рядом с файлами проекта так, чтобы путь к исполняемому файлу был:

```text
rnv/realesrgan-ncnn-vulkan.exe
```
