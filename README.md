# VS SDL2 Project Generator

Минималистичный Python-скрипт для генерации **Visual Studio 2022 C++ (x64)** проектов  
с библиотеками **SDL2** и **SDL2_image**, с опциональной поддержкой  
**SDL2_ttf** и **SDL2_mixer**.

Проект создаётся сразу в рабочем виде: со структурой папок, стартовым кодом,
подключёнными библиотеками и автоматическим копированием DLL.

> Скрипт написан для Windows + Visual Studio 2022  
> Проверен на MSBuild без зависимостей от `cmd`, `xcopy` и PATH.

---

## Возможности

- Генерация `.sln`, `.vcxproj`, `.vcxproj.filters`
- Структура проекта:

- 

ProjectName/
├─ src/
│ ├─ main.cpp
│ └─ app.cpp
├─ include/
│ └─ ProjectName/
│ └─ app.h
├─ assets/
├─ bin/
├─ intermediate/

- Подключение:
- SDL2
- SDL2_image
- опционально: SDL2_ttf + SDL2_mixer (`--full`)
- Автоматическое копирование DLL после сборки  
(через **MSBuild `<Copy>`**, без `cmd/xcopy`)
- Копирование dotFiles:
- `.clang-format`
- `.editorconfig`
- `.gitignore`
- `readme.md`
- Опциональная инициализация git (`--git`)
- Проверка наличия `.lib` / `.dll` / директорий (`--fail-on-missing`)
- Чистый, стабильный проект **без wildcard-предупреждений Visual Studio**

---

## Требования

- Windows 10 / 11
- Visual Studio 2022 (v143 toolset)
- Python 3.9+
- Установленные библиотеки SDL:
D:\Code\SDL_Dev
├─ SDL2-2.30.0
├─ SDL2_image-2.8.2
├─ SDL2_ttf-2.22.0 (опционально)
└─ SDL2_mixer-2.8.0 (опционально)


> Пути можно переопределять аргументами командной строки.

---

## Использование

### Базовый проект (SDL2 + SDL2_image)

```bash
python3 VS_build.py TestProject
```


Полный проект (+ SDL2_ttf и SDL2_mixer)
```bash
python3 VS_build.py TestProject --full
```

С инициализацией git
```bash
python3 VS_build.py TestProject --git
```


Строгий режим (ошибка при отсутствии файлов)
```bash
python3 VS_build.py TestProject --fail-on-missing
```

Основные параметры
Параметр	Описание
name	Имя проекта и папки
--out	Папка, где создаётся проект
--full	Добавить SDL2_ttf и SDL2_mixer
--git	Выполнить git init
--fail-on-missing	Прервать выполнение, если не найдены .lib/.dll
--dotfiles-dir	Папка с dotFiles

Почему MSBuild Copy вместо xcopy

Скрипт не использует cmd, xcopy или PowerShell для post-build шагов.

DLL копируются через нативную MSBuild-задачу:

<Copy SourceFiles="@(SdlDlls)" DestinationFolder="$(OutDir)" />


Преимущества:

не зависит от PATH

работает в изолированном окружении MSBuild

стабильнее и быстрее

корректно работает в Visual Studio

Стартовый код

Проект создаётся сразу с простым App-классом:

App::init() — инициализация SDL и окна

App::run() — основной цикл

App::shutdown() — корректное завершение

main.cpp минимален и чист.

Заметки

Проект создаётся как Console Application

Используется стандарт C++20

Все пути и библиотеки легко переопределяются аргументами

Скрипт рассчитан на личное использование и быструю инициализацию проектов

Лицензия

Свободное использование.

