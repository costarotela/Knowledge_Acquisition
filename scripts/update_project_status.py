import os
import json
from datetime import datetime
from pathlib import Path
import subprocess
import re
from typing import Dict, Any, List

def get_git_stats() -> Dict[str, Any]:
    """Obtiene estadísticas del repositorio git."""
    stats = {}
    
    # Total de commits
    result = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        capture_output=True,
        text=True
    )
    stats["total_commits"] = int(result.stdout.strip())
    
    # Último commit
    result = subprocess.run(
        ["git", "log", "-1", "--format=%H|%an|%at"],
        capture_output=True,
        text=True
    )
    commit_hash, author, timestamp = result.stdout.strip().split("|")
    stats["last_commit"] = {
        "hash": commit_hash,
        "author": author,
        "date": datetime.fromtimestamp(int(timestamp)).isoformat()
    }
    
    return stats

def get_test_coverage() -> Dict[str, float]:
    """Obtiene métricas de cobertura de tests."""
    try:
        result = subprocess.run(
            ["pytest", "--cov=src", "--cov-report=json"],
            capture_output=True,
            text=True
        )
        with open("coverage.json") as f:
            coverage_data = json.load(f)
            
        return {
            "total": coverage_data["totals"]["percent_covered"],
            "files": len(coverage_data["files"]),
            "lines": coverage_data["totals"]["num_statements"]
        }
    except:
        return {"total": 0.0, "files": 0, "lines": 0}

def count_lines_of_code() -> Dict[str, int]:
    """Cuenta líneas de código por tipo."""
    stats = {"total": 0, "python": 0, "test": 0, "docs": 0}
    
    for root, _, files in os.walk("src"):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                with open(path) as f:
                    lines = len(f.readlines())
                    stats["python"] += lines
                    stats["total"] += lines
    
    for root, _, files in os.walk("tests"):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                with open(path) as f:
                    lines = len(f.readlines())
                    stats["test"] += lines
                    stats["total"] += lines
    
    for root, _, files in os.walk("docs"):
        for file in files:
            if file.endswith(".md"):
                path = os.path.join(root, file)
                with open(path) as f:
                    stats["docs"] += len(f.readlines())
    
    return stats

def get_dependencies() -> List[str]:
    """Obtiene lista de dependencias principales."""
    with open("setup.py") as f:
        content = f.read()
        
    # Extraer dependencias del setup.py
    deps = re.findall(r"install_requires=\[(.*?)\]", content, re.DOTALL)[0]
    return [
        dep.strip().strip("'").strip('"')
        for dep in deps.split(",")
        if dep.strip() and not dep.strip().startswith("#")
    ]

def update_readme(stats: Dict[str, Any]) -> None:
    """Actualiza el README con las últimas estadísticas."""
    readme_path = Path("project_status/README.md")
    with open(readme_path) as f:
        content = f.read()
    
    # Actualizar métricas
    metrics_section = f"""## 📈 Métricas Clave
- Cobertura de tests: {stats['coverage']['total']:.1f}%
- Líneas de código: {stats['code']['total']}
- Total commits: {stats['git']['total_commits']}
- Archivos Python: {stats['code']['python']}
- Tests: {stats['code']['test']}
- Documentación: {stats['code']['docs']}"""
    
    # Actualizar última actualización
    update_section = f"""## 🔄 Última Actualización
- Fecha: {datetime.now().strftime('%d de %B, %Y')}
- Commit: {stats['git']['last_commit']['hash'][:7]}
- Autor: {stats['git']['last_commit']['author']}"""
    
    # Reemplazar secciones en el README
    content = re.sub(
        r"## 📈 Métricas Clave.*?##",
        f"{metrics_section}\n\n##",
        content,
        flags=re.DOTALL
    )
    
    content = re.sub(
        r"## 🔄 Última Actualización.*?$",
        update_section,
        content,
        flags=re.DOTALL
    )
    
    with open(readme_path, "w") as f:
        f.write(content)

def main():
    """Función principal para actualizar el estado del proyecto."""
    stats = {
        "git": get_git_stats(),
        "coverage": get_test_coverage(),
        "code": count_lines_of_code(),
        "dependencies": get_dependencies(),
        "timestamp": datetime.now().isoformat()
    }
    
    # Guardar estadísticas
    os.makedirs("project_status/stats", exist_ok=True)
    with open(f"project_status/stats/stats_{datetime.now().strftime('%Y%m%d')}.json", "w") as f:
        json.dump(stats, f, indent=2)
    
    # Actualizar README
    update_readme(stats)

if __name__ == "__main__":
    main()
