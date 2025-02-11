"""
Script de verificación automática de código.
"""
import os
import sys
import ast
import logging
from pathlib import Path
from typing import List, Dict, Any
import pylint.lint
import pytest
import black
import mypy.api

class CodeVerifier:
    """Verifica la calidad del código."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.src_dir = project_root / "src"
        self.tests_dir = project_root / "tests"
        self.logger = logging.getLogger("verifier")
    
    def verify_all(self) -> Dict[str, Any]:
        """Ejecuta todas las verificaciones."""
        results = {
            "style": self.check_style(),
            "types": self.check_types(),
            "tests": self.run_tests(),
            "docs": self.check_docs(),
            "complexity": self.check_complexity()
        }
        
        return self._summarize_results(results)
    
    def check_style(self) -> Dict[str, Any]:
        """Verifica el estilo del código."""
        # Ejecutar black en modo check
        black_args = ["--check", str(self.src_dir)]
        try:
            black.main(black_args)
            style_ok = True
        except SystemExit:
            style_ok = False
        
        # Ejecutar pylint
        pylint_args = [str(self.src_dir)]
        pylint.lint.Run(pylint_args, do_exit=False)
        
        return {
            "black_ok": style_ok,
            "pylint_ran": True
        }
    
    def check_types(self) -> Dict[str, Any]:
        """Verifica tipos con mypy."""
        result = mypy.api.run([str(self.src_dir)])
        
        return {
            "output": result[0],
            "errors": result[1],
            "status": result[2]
        }
    
    def run_tests(self) -> Dict[str, Any]:
        """Ejecuta tests con pytest."""
        pytest_args = [
            str(self.tests_dir),
            "-v",
            "--cov=src",
            "--cov-report=term-missing"
        ]
        
        try:
            result = pytest.main(pytest_args)
            success = result == 0
        except Exception as e:
            success = False
            self.logger.error(f"Error en tests: {e}")
        
        return {
            "success": success
        }
    
    def check_docs(self) -> Dict[str, Any]:
        """Verifica documentación."""
        results = {
            "missing_docstrings": [],
            "total_files": 0,
            "files_with_docs": 0
        }
        
        for py_file in self.src_dir.rglob("*.py"):
            results["total_files"] += 1
            
            with open(py_file, "r") as f:
                try:
                    tree = ast.parse(f.read())
                    
                    # Verificar docstring del módulo
                    if ast.get_docstring(tree):
                        results["files_with_docs"] += 1
                    else:
                        results["missing_docstrings"].append(str(py_file))
                        
                    # Verificar docstrings de clases y funciones
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                            if not ast.get_docstring(node):
                                results["missing_docstrings"].append(
                                    f"{py_file}::{node.name}"
                                )
                                
                except Exception as e:
                    self.logger.error(f"Error analizando {py_file}: {e}")
        
        return results
    
    def check_complexity(self) -> Dict[str, Any]:
        """Verifica complejidad del código."""
        results = {
            "high_complexity": []
        }
        
        def analyze_complexity(node: ast.AST) -> int:
            """Calcula complejidad ciclomática."""
            complexity = 1
            for child in ast.walk(node):
                if isinstance(child, (ast.If, ast.While, ast.For, ast.Try,
                                   ast.ExceptHandler, ast.With,
                                   ast.AsyncWith, ast.AsyncFor)):
                    complexity += 1
                elif isinstance(child, ast.BoolOp):
                    complexity += len(child.values) - 1
            return complexity
        
        for py_file in self.src_dir.rglob("*.py"):
            with open(py_file, "r") as f:
                try:
                    tree = ast.parse(f.read())
                    
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            complexity = analyze_complexity(node)
                            if complexity > 10:  # Umbral de complejidad
                                results["high_complexity"].append({
                                    "file": str(py_file),
                                    "function": node.name,
                                    "complexity": complexity
                                })
                                
                except Exception as e:
                    self.logger.error(f"Error analizando complejidad de {py_file}: {e}")
        
        return results
    
    def _summarize_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Resume los resultados de todas las verificaciones."""
        summary = {
            "status": "pass",
            "warnings": [],
            "errors": []
        }
        
        # Verificar estilo
        if not results["style"]["black_ok"]:
            summary["warnings"].append("Código no cumple con formato Black")
        
        # Verificar tipos
        if results["types"]["status"] != 0:
            summary["errors"].append("Errores de tipo encontrados")
        
        # Verificar tests
        if not results["tests"]["success"]:
            summary["errors"].append("Fallos en tests")
        
        # Verificar docs
        doc_coverage = (results["docs"]["files_with_docs"] /
                       results["docs"]["total_files"]
                       if results["docs"]["total_files"] > 0 else 0)
        if doc_coverage < 0.8:
            summary["warnings"].append("Baja cobertura de documentación")
        
        # Verificar complejidad
        if len(results["complexity"]["high_complexity"]) > 0:
            summary["warnings"].append("Funciones con alta complejidad detectadas")
        
        # Determinar estado final
        if len(summary["errors"]) > 0:
            summary["status"] = "fail"
        elif len(summary["warnings"]) > 0:
            summary["status"] = "warn"
        
        return summary

def main():
    """Punto de entrada principal."""
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    
    # Obtener directorio del proyecto
    project_root = Path(__file__).parent.parent
    
    # Crear verificador
    verifier = CodeVerifier(project_root)
    
    # Ejecutar verificaciones
    results = verifier.verify_all()
    
    # Mostrar resultados
    print("\n=== Resultados de Verificación ===")
    print(f"Estado: {results['status'].upper()}")
    
    if results["warnings"]:
        print("\nAdvertencias:")
        for warning in results["warnings"]:
            print(f"- {warning}")
    
    if results["errors"]:
        print("\nErrores:")
        for error in results["errors"]:
            print(f"- {error}")
    
    # Salir con código apropiado
    sys.exit(0 if results["status"] == "pass" else 1)

if __name__ == "__main__":
    main()
