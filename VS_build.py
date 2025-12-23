#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# VS_build.py (minimal v2, MSBuild Copy вместо xcopy/cmd)
#
# VS2022 C++ (x64) проект под SDL2 + SDL2_image (динамические либы).
# Опционально: --full (SDL2_ttf + SDL2_mixer), --git (git init)
#
# Делает:
# - Создаёт папку проекта: <out>\<ProjectName>\
# - Создаёт папки: src, include\<ProjectName>, assets
# - Копирует dotFiles: .clang-format .editorconfig .gitignore readme.md
# - Генерирует скелетон: include\<ProjectName>\app.h, src\app.cpp, src\main.cpp
# - Генерирует: .sln, .vcxproj, .vcxproj.filters
# - Additional Include Directories: $(ProjectDir)include + SDL includes
# - Линкует SDL2/SDL2_image (+ ttf/mixer при --full)
# - Копирует DLL после сборки средствами MSBuild <Copy> (без cmd/xcopy!)
# - Проверяет наличие .lib/.dll и предупреждает (или падает при --fail-on-missing)

import argparse
import uuid
import shutil
import subprocess
from pathlib import Path

# ---- Пути по умолчанию ----
DEFAULT_OUT_DIR = r"D:\Code\Again"

SDL2_INCLUDE = r"D:\Code\SDL_Dev\SDL2-2.30.0\include"
SDL2_LIB_X64  = r"D:\Code\SDL_Dev\SDL2-2.30.0\lib\x64"

SDL2_IMAGE_INCLUDE = r"D:\Code\SDL_Dev\SDL2_image-2.8.2\include"
SDL2_IMAGE_LIB_X64 = r"D:\Code\SDL_Dev\SDL2_image-2.8.2\lib\x64"

# FULL (если --full)
SDL2_TTF_INCLUDE = r"D:\Code\SDL_Dev\SDL2_ttf-2.22.0\include"
SDL2_TTF_LIB_X64 = r"D:\Code\SDL_Dev\SDL2_ttf-2.22.0\lib\x64"

SDL2_MIXER_INCLUDE = r"D:\Code\SDL_Dev\SDL2_mixer-2.8.0\include"
SDL2_MIXER_LIB_X64 = r"D:\Code\SDL_Dev\SDL2_mixer-2.8.0\lib\x64"

# DLL dirs (по умолчанию из lib\x64)
SDL2_DLL_DIR       = SDL2_LIB_X64
SDL2_IMAGE_DLL_DIR = SDL2_IMAGE_LIB_X64
SDL2_TTF_DLL_DIR   = SDL2_TTF_LIB_X64
SDL2_MIXER_DLL_DIR = SDL2_MIXER_LIB_X64

# dotFiles
DOTFILES_DIR = r"D:\Code\SDL_Dev\dotFiles"
DOTFILES = [".clang-format", ".editorconfig", ".gitignore", "readme.md"]

# ---- Шаблоны ----
SLN_TEMPLATE = r"""Microsoft Visual Studio Solution File, Format Version 12.00
# Visual Studio Version 17
VisualStudioVersion = 17.3.32929.385
MinimumVisualStudioVersion = 10.0.40219.1
Project("{{8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942}}") = "{proj_name}", "{proj_name}.vcxproj", "{{{proj_guid}}}"
EndProject
Global
    GlobalSection(SolutionConfigurationPlatforms) = preSolution
        Debug|x64 = Debug|x64
        Release|x64 = Release|x64
    EndGlobalSection
    GlobalSection(ProjectConfigurationPlatforms) = postSolution
        {{{proj_guid}}}.Debug|x64.ActiveCfg = Debug|x64
        {{{proj_guid}}}.Debug|x64.Build.0 = Debug|x64
        {{{proj_guid}}}.Release|x64.ActiveCfg = Release|x64
        {{{proj_guid}}}.Release|x64.Build.0 = Release|x64
    EndGlobalSection
    GlobalSection(SolutionProperties) = preSolution
        HideSolutionNode = FALSE
    EndGlobalSection
    GlobalSection(ExtensibilityGlobals) = postSolution
        SolutionGuid = {{{sln_guid}}}
    EndGlobalSection
EndGlobal
"""

# ВАЖНО: DLL копируем MSBuild Copy target'ом (см. CopySdlDlls)
VCXPROJ_TEMPLATE = r"""<?xml version="1.0" encoding="utf-8"?>
<Project DefaultTargets="Build" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
  <ItemGroup Label="ProjectConfigurations">
    <ProjectConfiguration Include="Debug|x64">
      <Configuration>Debug</Configuration>
      <Platform>x64</Platform>
    </ProjectConfiguration>
    <ProjectConfiguration Include="Release|x64">
      <Configuration>Release</Configuration>
      <Platform>x64</Platform>
    </ProjectConfiguration>
  </ItemGroup>

  <PropertyGroup Label="Globals">
    <VCProjectVersion>17.0</VCProjectVersion>
    <Keyword>Win32Proj</Keyword>
    <ProjectGuid>{{{proj_guid}}}</ProjectGuid>
    <RootNamespace>{proj_name}</RootNamespace>
    <ProjectName>{proj_name}</ProjectName>
    <WindowsTargetPlatformVersion>10.0</WindowsTargetPlatformVersion>
  </PropertyGroup>

  <Import Project="$(VCTargetsPath)\Microsoft.Cpp.Default.props" />

  <PropertyGroup Condition="'$(Configuration)|$(Platform)'=='Debug|x64'" Label="Configuration">
    <ConfigurationType>Application</ConfigurationType>
    <UseDebugLibraries>true</UseDebugLibraries>
    <PlatformToolset>v143</PlatformToolset>
    <CharacterSet>Unicode</CharacterSet>
  </PropertyGroup>

  <PropertyGroup Condition="'$(Configuration)|$(Platform)'=='Release|x64'" Label="Configuration">
    <ConfigurationType>Application</ConfigurationType>
    <UseDebugLibraries>false</UseDebugLibraries>
    <PlatformToolset>v143</PlatformToolset>
    <WholeProgramOptimization>true</WholeProgramOptimization>
    <CharacterSet>Unicode</CharacterSet>
  </PropertyGroup>

  <Import Project="$(VCTargetsPath)\Microsoft.Cpp.props" />

  <ImportGroup Label="ExtensionSettings" />
  <ImportGroup Label="Shared" />

  <ImportGroup Label="PropertySheets" Condition="'$(Configuration)|$(Platform)'=='Debug|x64'">
    <Import Project="$(UserRootDir)\Microsoft.Cpp.$(Platform).user.props" Condition="exists('$(UserRootDir)\Microsoft.Cpp.$(Platform).user.props')" Label="LocalAppDataPlatform" />
  </ImportGroup>
  <ImportGroup Label="PropertySheets" Condition="'$(Configuration)|$(Platform)'=='Release|x64'">
    <Import Project="$(UserRootDir)\Microsoft.Cpp.$(Platform).user.props" Condition="exists('$(UserRootDir)\Microsoft.Cpp.$(Platform).user.props')" Label="LocalAppDataPlatform" />
  </ImportGroup>

  <PropertyGroup Label="UserMacros" />

  <PropertyGroup>
    <OutDir>$(ProjectDir)bin\$(Configuration)\</OutDir>
    <IntDir>$(ProjectDir)intermediate\$(Configuration)\</IntDir>
  </PropertyGroup>

  <ItemDefinitionGroup Condition="'$(Configuration)|$(Platform)'=='Debug|x64'">
    <ClCompile>
      <WarningLevel>Level3</WarningLevel>
      <SDLCheck>true</SDLCheck>
      <ConformanceMode>true</ConformanceMode>
      <LanguageStandard>stdcpp20</LanguageStandard>
      <PreprocessorDefinitions>_DEBUG;_CRT_SECURE_NO_WARNINGS;NOMINMAX;%(PreprocessorDefinitions)</PreprocessorDefinitions>
      <AdditionalIncludeDirectories>$(ProjectDir)include;{all_includes};%(AdditionalIncludeDirectories)</AdditionalIncludeDirectories>
    </ClCompile>
    <Link>
      <SubSystem>Console</SubSystem>
      <GenerateDebugInformation>true</GenerateDebugInformation>
      <AdditionalLibraryDirectories>{all_libdirs};%(AdditionalLibraryDirectories)</AdditionalLibraryDirectories>
      <AdditionalDependencies>{all_libs};%(AdditionalDependencies)</AdditionalDependencies>
    </Link>
  </ItemDefinitionGroup>

  <ItemDefinitionGroup Condition="'$(Configuration)|$(Platform)'=='Release|x64'">
    <ClCompile>
      <WarningLevel>Level3</WarningLevel>
      <FunctionLevelLinking>true</FunctionLevelLinking>
      <IntrinsicFunctions>true</IntrinsicFunctions>
      <SDLCheck>true</SDLCheck>
      <ConformanceMode>true</ConformanceMode>
      <LanguageStandard>stdcpp20</LanguageStandard>
      <PreprocessorDefinitions>NDEBUG;_CRT_SECURE_NO_WARNINGS;NOMINMAX;%(PreprocessorDefinitions)</PreprocessorDefinitions>
      <AdditionalIncludeDirectories>$(ProjectDir)include;{all_includes};%(AdditionalIncludeDirectories)</AdditionalIncludeDirectories>
    </ClCompile>
    <Link>
      <SubSystem>Console</SubSystem>
      <EnableCOMDATFolding>true</EnableCOMDATFolding>
      <OptimizeReferences>true</OptimizeReferences>
      <AdditionalLibraryDirectories>{all_libdirs};%(AdditionalLibraryDirectories)</AdditionalLibraryDirectories>
      <AdditionalDependencies>{all_libs};%(AdditionalDependencies)</AdditionalDependencies>
    </Link>
  </ItemDefinitionGroup>

  <!-- Явный список файлов (без wildcard'ов, чтобы VS не ругался) -->
  <ItemGroup>
    <ClCompile Include="src\main.cpp" />
    <ClCompile Include="src\app.cpp" />
  </ItemGroup>

  <ItemGroup>
    <ClInclude Include="include\{proj_name}\app.h" />
  </ItemGroup>

  <ItemGroup>
    <None Include="assets\.keep" />
  </ItemGroup>

  <!-- Копирование DLL после сборки (без cmd/xcopy) -->
  <Target Name="CopySdlDlls" AfterTargets="Build">
    <ItemGroup>
      <SdlDlls Include="{dll_globs}" />
    </ItemGroup>

    <Copy
      SourceFiles="@(SdlDlls)"
      DestinationFolder="$(OutDir)"
      SkipUnchangedFiles="true"
      Retries="2"
      RetryDelayMilliseconds="250"
      Condition="'@(SdlDlls)' != ''" />
  </Target>

  <Import Project="$(VCTargetsPath)\Microsoft.Cpp.targets" />
  <ImportGroup Label="ExtensionTargets" />
</Project>
"""

VCXPROJ_FILTERS = r"""<?xml version="1.0" encoding="utf-8"?>
<Project ToolsVersion="4.0" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
  <ItemGroup>
    <Filter Include="Source Files">
      <UniqueIdentifier>{SOURCE_GUID}</UniqueIdentifier>
    </Filter>
    <Filter Include="Header Files">
      <UniqueIdentifier>{HEADER_GUID}</UniqueIdentifier>
    </Filter>
    <Filter Include="Asset Files">
      <UniqueIdentifier>{ASSET_GUID}</UniqueIdentifier>
    </Filter>
  </ItemGroup>

  <ItemGroup>
    <ClCompile Include="src\main.cpp">
      <Filter>Source Files</Filter>
    </ClCompile>
    <ClCompile Include="src\app.cpp">
      <Filter>Source Files</Filter>
    </ClCompile>
  </ItemGroup>

  <ItemGroup>
    <ClInclude Include="include\{proj_name}\app.h">
      <Filter>Header Files</Filter>
    </ClInclude>
  </ItemGroup>

  <ItemGroup>
    <None Include="assets\.keep">
      <Filter>Asset Files</Filter>
    </None>
  </ItemGroup>
</Project>
"""

# ---- Скелетон ----
APP_H = r"""#pragma once

#include <SDL.h>
#include <SDL_image.h>

class App {
public:
    bool init();
    void run();
    void shutdown();

private:
    SDL_Window* window_ = nullptr;
    SDL_Renderer* renderer_ = nullptr;
    bool running_ = false;
};
"""

APP_CPP = r"""#include "{proj_name}/app.h"
#include <iostream>

bool App::init()
{{
    if (SDL_Init(SDL_INIT_VIDEO) != 0) {{
        std::cerr << "SDL_Init Error: " << SDL_GetError() << std::endl;
        return false;
    }}

    int imgFlags = IMG_INIT_PNG | IMG_INIT_JPG;
    if (!(IMG_Init(imgFlags) & imgFlags)) {{
        std::cerr << "IMG_Init Error: " << IMG_GetError() << std::endl;
        SDL_Quit();
        return false;
    }}

    window_ = SDL_CreateWindow(
        "{proj_name}",
        SDL_WINDOWPOS_CENTERED,
        SDL_WINDOWPOS_CENTERED,
        800, 600,
        SDL_WINDOW_SHOWN
    );

    if (!window_) {{
        std::cerr << "SDL_CreateWindow Error: " << SDL_GetError() << std::endl;
        IMG_Quit();
        SDL_Quit();
        return false;
    }}

    renderer_ = SDL_CreateRenderer(window_, -1, SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC);
    if (!renderer_) {{
        std::cerr << "SDL_CreateRenderer Error: " << SDL_GetError() << std::endl;
        SDL_DestroyWindow(window_);
        window_ = nullptr;
        IMG_Quit();
        SDL_Quit();
        return false;
    }}

    running_ = true;
    return true;
}}

void App::run()
{{
    while (running_) {{
        SDL_Event e;
        while (SDL_PollEvent(&e)) {{
            if (e.type == SDL_QUIT) running_ = false;
        }}

        SDL_SetRenderDrawColor(renderer_, 30, 30, 36, 255);
        SDL_RenderClear(renderer_);
        SDL_RenderPresent(renderer_);
    }}
}}

void App::shutdown()
{{
    if (renderer_) {{
        SDL_DestroyRenderer(renderer_);
        renderer_ = nullptr;
    }}
    if (window_) {{
        SDL_DestroyWindow(window_);
        window_ = nullptr;
    }}
    IMG_Quit();
    SDL_Quit();
}}
"""

MAIN_CPP = r"""#include "{proj_name}/app.h"

int main(int, char**)
{{
    App app;
    if (!app.init()) return 1;
    app.run();
    app.shutdown();
    return 0;
}}
"""

def write_text(path: Path, data: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")
    print(f"  wrote {path}")

def norm(p: str) -> str:
    return Path(p).as_posix().replace("/", "\\")

def ensure_dirs(project_root: Path, project_name: str):
    (project_root / "src").mkdir(parents=True, exist_ok=True)
    (project_root / "assets").mkdir(parents=True, exist_ok=True)
    (project_root / "include" / project_name).mkdir(parents=True, exist_ok=True)

    keep = project_root / "assets" / ".keep"
    if not keep.exists():
        keep.write_text("", encoding="utf-8")
        print(f"  wrote {keep}")

def copy_dotfiles(project_root: Path, dotfiles_dir: str, fail_on_missing: bool):
    src_dir = Path(dotfiles_dir)
    problems = []
    for fname in DOTFILES:
        src = src_dir / fname
        dst = project_root / fname
        if not src.exists():
            problems.append(f"[dotfile] missing: {src}")
            continue
        shutil.copy2(src, dst)
        print(f"  copied {src} -> {dst}")

    if problems:
        print("\n=== DOTFILES WARNINGS ===")
        for msg in problems:
            print(" -", msg)
        print("=========================\n")
        if fail_on_missing:
            raise SystemExit("Missing dotFiles. Aborting due to --fail-on-missing.")

def git_init(project_root: Path):
    try:
        subprocess.run(["git", "init"], cwd=str(project_root), check=True, capture_output=True, text=True)
        print("  git init: OK")
    except FileNotFoundError:
        print("  git init: SKIP (git not found in PATH)")
    except subprocess.CalledProcessError as e:
        print("  git init: FAILED")
        if e.stdout:
            print(e.stdout.strip())
        if e.stderr:
            print(e.stderr.strip())

def check_paths_and_files(
    includes: list[str],
    libdirs: list[str],
    dll_dirs: list[str],
    expected_libs: list[tuple[str, str]],
    expected_dll_patterns: list[tuple[str, str]],
    fail_on_missing: bool,
) -> None:
    problems = []

    for p in includes:
        if not Path(p).exists():
            problems.append(f"[dir] include not found: {p}")
    for p in libdirs:
        if not Path(p).exists():
            problems.append(f"[dir] lib not found: {p}")
    for p in dll_dirs:
        if not Path(p).exists():
            problems.append(f"[dir] dll dir not found: {p}")

    for base, fname in expected_libs:
        if not Path(base, fname).exists():
            problems.append(f"[lib] {fname} not found in: {base}")

    for base, pattern in expected_dll_patterns:
        bp = Path(base)
        if bp.exists() and not list(bp.glob(pattern)):
            problems.append(f"[dll] {pattern} not found in: {base}")

    if problems:
        print("\n=== CHECK WARNINGS ===")
        for msg in problems:
            print(" -", msg)
        print("======================\n")
        if fail_on_missing:
            raise SystemExit("Missing required files/dirs. Aborting due to --fail-on-missing.")

def build_config(full: bool, args) -> dict:
    includes = [args.sdl2_inc, args.sdl2img_inc]
    libdirs  = [args.sdl2_lib, args.sdl2img_lib]
    dll_dirs = [args.sdl2_dll_dir, args.sdl2img_dll_dir]

    libs = ["SDL2.lib", "SDL2main.lib", "SDL2_image.lib"]

    expected_libs = [
        (args.sdl2_lib, "SDL2.lib"),
        (args.sdl2_lib, "SDL2main.lib"),
        (args.sdl2img_lib, "SDL2_image.lib"),
    ]
    expected_dll_patterns = [
        (args.sdl2_dll_dir, "SDL2.dll"),
        (args.sdl2img_dll_dir, "SDL2_image*.dll"),
    ]

    if full:
        includes += [args.sdl2ttf_inc, args.sdl2mixer_inc]
        libdirs  += [args.sdl2ttf_lib, args.sdl2mixer_lib]
        dll_dirs += [args.sdl2ttf_dll_dir, args.sdl2mixer_dll_dir]

        libs += ["SDL2_ttf.lib", "SDL2_mixer.lib"]

        expected_libs += [
            (args.sdl2ttf_lib, "SDL2_ttf.lib"),
            (args.sdl2mixer_lib, "SDL2_mixer.lib"),
        ]
        expected_dll_patterns += [
            (args.sdl2ttf_dll_dir, "SDL2_ttf*.dll"),
            (args.sdl2mixer_dll_dir, "SDL2_mixer*.dll"),
        ]

    # MSBuild <Copy> умеет wildcard'ы в Include
    dll_globs = ";".join([f"{d}\\*.dll" for d in dll_dirs])

    return {
        "includes": includes,
        "libdirs": libdirs,
        "dll_dirs": dll_dirs,
        "libs": libs,
        "expected_libs": expected_libs,
        "expected_dll_patterns": expected_dll_patterns,
        "dll_globs": dll_globs,
    }

def generate_skeleton(project_root: Path, project_name: str):
    write_text(project_root / "include" / project_name / "app.h", APP_H)
    write_text(project_root / "src" / "app.cpp", APP_CPP.format(proj_name=project_name))
    write_text(project_root / "src" / "main.cpp", MAIN_CPP.format(proj_name=project_name))

def generate(project_name: str, out_dir: str, full: bool, do_git: bool, fail_on_missing: bool, args):
    cfg = build_config(full, args)

    check_paths_and_files(
        includes=cfg["includes"],
        libdirs=cfg["libdirs"],
        dll_dirs=cfg["dll_dirs"],
        expected_libs=cfg["expected_libs"],
        expected_dll_patterns=cfg["expected_dll_patterns"],
        fail_on_missing=fail_on_missing,
    )

    sln_guid = str(uuid.uuid4()).upper()
    proj_guid = str(uuid.uuid4()).upper()

    source_guid = str(uuid.uuid4()).upper()
    header_guid = str(uuid.uuid4()).upper()
    asset_guid  = str(uuid.uuid4()).upper()

    project_root = Path(out_dir) / project_name
    ensure_dirs(project_root, project_name)
    copy_dotfiles(project_root, args.dotfiles_dir, fail_on_missing)
    generate_skeleton(project_root, project_name)

    sln_path = project_root / f"{project_name}.sln"
    proj_path = project_root / f"{project_name}.vcxproj"
    filters_path = project_root / f"{project_name}.vcxproj.filters"

    sln_text = SLN_TEMPLATE.format(
        sln_guid=sln_guid,
        proj_guid=proj_guid,
        proj_name=project_name
    )

    vcx_text = VCXPROJ_TEMPLATE.format(
        proj_guid=proj_guid,
        proj_name=project_name,
        all_includes=";".join(cfg["includes"]),
        all_libdirs=";".join(cfg["libdirs"]),
        all_libs=";".join(cfg["libs"]),
        dll_globs=cfg["dll_globs"],
    )

    filters_text = VCXPROJ_FILTERS.format(
        proj_name=project_name,
        SOURCE_GUID="{" + source_guid + "}",
        HEADER_GUID="{" + header_guid + "}",
        ASSET_GUID="{" + asset_guid + "}",
    )

    write_text(sln_path, sln_text)
    write_text(proj_path, vcx_text)
    write_text(filters_path, filters_text)

    if do_git:
        git_init(project_root)

    print("\nDone.")
    print(f"Solution: {sln_path}")
    print(f"Project:  {proj_path}")
    print(f"Full:     {full}")
    print(f"Git:      {do_git}")

def main():
    p = argparse.ArgumentParser(
        description="VS2022 SDL2 project generator (minimal v2). SDL2 + SDL2_image, optional SDL2_ttf+SDL2_mixer. DLL copy via MSBuild <Copy>."
    )
    p.add_argument("name", nargs="?", help="Имя проекта (и папки)")
    p.add_argument("-n", "--name", dest="name_opt", help="Имя проекта (альтернатива позиционному)")
    p.add_argument("--out", default=DEFAULT_OUT_DIR, help=f"Папка вывода (по умолчанию {DEFAULT_OUT_DIR})")

    p.add_argument("--sdl2-inc", default=SDL2_INCLUDE)
    p.add_argument("--sdl2-lib", default=SDL2_LIB_X64)
    p.add_argument("--sdl2img-inc", default=SDL2_IMAGE_INCLUDE)
    p.add_argument("--sdl2img-lib", default=SDL2_IMAGE_LIB_X64)

    p.add_argument("--sdl2-dll-dir", default=SDL2_DLL_DIR)
    p.add_argument("--sdl2img-dll-dir", default=SDL2_IMAGE_DLL_DIR)

    p.add_argument("--full", action="store_true", help="Добавить SDL2_ttf + SDL2_mixer")
    p.add_argument("--sdl2ttf-inc", default=SDL2_TTF_INCLUDE)
    p.add_argument("--sdl2ttf-lib", default=SDL2_TTF_LIB_X64)
    p.add_argument("--sdl2ttf-dll-dir", default=SDL2_TTF_DLL_DIR)

    p.add_argument("--sdl2mixer-inc", default=SDL2_MIXER_INCLUDE)
    p.add_argument("--sdl2mixer-lib", default=SDL2_MIXER_LIB_X64)
    p.add_argument("--sdl2mixer-dll-dir", default=SDL2_MIXER_DLL_DIR)

    p.add_argument("--dotfiles-dir", default=DOTFILES_DIR)
    p.add_argument("--git", action="store_true")
    p.add_argument("--fail-on-missing", action="store_true")

    args = p.parse_args()
    proj_name = args.name or args.name_opt
    if not proj_name:
        p.error("Не указано имя проекта. Пример: python3 VS_build.py TestProject")

    # normalize
    args.out = norm(args.out)

    args.sdl2_inc = norm(args.sdl2_inc)
    args.sdl2_lib = norm(args.sdl2_lib)
    args.sdl2img_inc = norm(args.sdl2img_inc)
    args.sdl2img_lib = norm(args.sdl2img_lib)
    args.sdl2_dll_dir = norm(args.sdl2_dll_dir)
    args.sdl2img_dll_dir = norm(args.sdl2img_dll_dir)

    args.sdl2ttf_inc = norm(args.sdl2ttf_inc)
    args.sdl2ttf_lib = norm(args.sdl2ttf_lib)
    args.sdl2ttf_dll_dir = norm(args.sdl2ttf_dll_dir)

    args.sdl2mixer_inc = norm(args.sdl2mixer_inc)
    args.sdl2mixer_lib = norm(args.sdl2mixer_lib)
    args.sdl2mixer_dll_dir = norm(args.sdl2mixer_dll_dir)

    args.dotfiles_dir = norm(args.dotfiles_dir)

    generate(
        project_name=proj_name,
        out_dir=args.out,
        full=args.full,
        do_git=args.git,
        fail_on_missing=args.fail_on_missing,
        args=args,
    )

if __name__ == "__main__":
    main()
