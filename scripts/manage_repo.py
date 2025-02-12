#!/usr/bin/env python3
"""
Script para automatizar la gestión del repositorio.
Incluye actualización de documentación, limpieza y subida a GitHub.
"""
import os
import sys
import subprocess
from typing import List, Tuple
import shutil
from pathlib import Path

def run_command(command: str, cwd: str = None) -> Tuple[int, str, str]:
    """Ejecuta un comando y retorna (código_salida, stdout, stderr)."""
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd
    )
    stdout, stderr = process.communicate()
    return (
        process.returncode,
        stdout.decode('utf-8'),
        stderr.decode('utf-8')
    )

def clean_cache_files(root_dir: str) -> None:
    """Limpia archivos de caché y temporales."""
    patterns = [
        '**/__pycache__',
        '**/.pytest_cache',
        '**/.coverage',
        '**/htmlcov',
        '**/*.pyc',
        '**/*.pyo',
        '**/*.pyd',
        '**/.DS_Store'
    ]
    
    for pattern in patterns:
        for path in Path(root_dir).glob(pattern):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
    
    print("✅ Archivos de caché limpiados")

def update_dependencies() -> None:
    """Actualiza los archivos de dependencias."""
    # Actualizar environment.yml
    run_command("conda env export > environment.yml")
    
    # Actualizar requirements.txt
    run_command("pip freeze > requirements.txt")
    
    print("✅ Archivos de dependencias actualizados")

def git_operations(commit_msg: str) -> bool:
    """Realiza operaciones de git."""
    commands = [
        "git add .",
        f'git commit -m "{commit_msg}"',
        "git push origin main"
    ]
    
    for cmd in commands:
        code, out, err = run_command(cmd)
        if code != 0:
            print(f"❌ Error en git: {err}")
            return False
    
    print("✅ Cambios subidos a GitHub")
    return True

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root_dir)
    
    steps = [
        ("Limpiando archivos de caché", lambda: clean_cache_files(root_dir)),
        ("Actualizando dependencias", update_dependencies)
    ]
    
    for desc, func in steps:
        print(f"\n🔄 {desc}...")
        result = func()
        if isinstance(result, bool) and not result:
            print("\n❌ Proceso abortado debido a errores")
            sys.exit(1)
    
    commit_msg = input("\n📝 Ingrese mensaje de commit: ")
    if not git_operations(commit_msg):
        print("\n❌ Error en operaciones de git")
        sys.exit(1)
    
    print("\n✨ ¡Proceso completado exitosamente!")

if __name__ == "__main__":
    main()
