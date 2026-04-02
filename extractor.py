"""
extractor.py - Extração de texto de repositórios TypeScript

Percorre um repositório e extrai texto de múltiplas fontes:
- Código-fonte (.ts, .tsx): classes, interfaces, funções, imports
- Comentários e JSDoc
- Documentação (.md, .txt, .rst)
"""

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ExtractedText:
    """Representa um bloco de texto extraído com metadados."""
    text: str
    source_file: str
    source_type: str  # 'code', 'comment', 'docstring', 'markdown', 'import'
    line_start: int = 0
    line_end: int = 0

    def __repr__(self):
        preview = self.text[:80].replace('\n', ' ')
        return f"ExtractedText({self.source_type}, '{preview}...')"


@dataclass
class RepoExtraction:
    """Resultado completo da extração de um repositório."""
    repo_path: str
    texts: list[ExtractedText] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    @property
    def all_text(self) -> str:
        return "\n\n".join(t.text for t in self.texts)

    @property
    def by_type(self) -> dict[str, list[ExtractedText]]:
        result = {}
        for t in self.texts:
            result.setdefault(t.source_type, []).append(t)
        return result

    def save_jsonl(self, output_path: str):
        """Salva os blocos extraídos em JSONL (1 objeto por linha)."""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        with output.open("w", encoding="utf-8") as f:
            for text in self.texts:
                row = {
                    "text": text.text,
                    "source_file": text.source_file,
                    "source_type": text.source_type,
                    "line_start": text.line_start,
                    "line_end": text.line_end,
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_jsonl_extractions(input_path: str, repo_path: str = "") -> RepoExtraction:
    """Carrega um JSONL de extrações e retorna RepoExtraction."""
    texts: list[ExtractedText] = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            texts.append(ExtractedText(
                text=row.get("text", ""),
                source_file=row.get("source_file", ""),
                source_type=row.get("source_type", "code"),
                line_start=row.get("line_start", 0),
                line_end=row.get("line_end", 0),
            ))

    extraction = RepoExtraction(repo_path=repo_path, texts=texts)
    extraction.stats = {
        "total_texts": len(extraction.texts),
        "ts_files": len({t.source_file for t in texts if t.source_file.endswith((".ts", ".tsx"))}),
        "doc_files": len({t.source_file for t in texts if t.source_file.endswith((".md", ".txt", ".rst"))}),
        "by_type": {k: len(v) for k, v in extraction.by_type.items()},
        "total_chars": sum(len(t.text) for t in extraction.texts),
    }
    return extraction


def extract_markdown(filepath: str) -> list[ExtractedText]:
    """Extrai texto de arquivos Markdown."""
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    sections = re.split(r'\n#{1,3}\s+', content)
    extractions = []
    for section in sections:
        clean = section.strip()
        if len(clean) > 10:
            extractions.append(ExtractedText(
                text=clean,
                source_file=filepath,
                source_type="markdown",
            ))
    return extractions


def extract_typescript(source_code: str, filepath: str) -> list[ExtractedText]:
    """Extrai estruturas relevantes de arquivos TypeScript/TSX via regex."""
    extractions: list[ExtractedText] = []
    lines = source_code.splitlines()

    # Imports: import ... from '...'; e import '...';
    import_pattern = re.compile(
        r"^\s*import\s+(?:type\s+)?(?:[\w*${}\s,]+\s+from\s+)?['\"]([^'\"]+)['\"]",
        re.MULTILINE,
    )
    for match in import_pattern.finditer(source_code):
        line = source_code.count("\n", 0, match.start()) + 1
        extractions.append(ExtractedText(
            text=match.group(0).strip(),
            source_file=filepath,
            source_type="import",
            line_start=line,
            line_end=line,
        ))

    # Classes, interfaces, tipos, enums.
    decl_pattern = re.compile(
        r"^\s*export\s+(?:default\s+)?(class|interface|type|enum)\s+(\w+)",
        re.MULTILINE,
    )
    for match in decl_pattern.finditer(source_code):
        line = source_code.count("\n", 0, match.start()) + 1
        kind = match.group(1)
        name = match.group(2)
        extractions.append(ExtractedText(
            text=f"{kind.capitalize()} {name}",
            source_file=filepath,
            source_type="code",
            line_start=line,
            line_end=line,
        ))

    # Funções e funções exportadas.
    fn_pattern = re.compile(
        r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)",
        re.MULTILINE,
    )
    for match in fn_pattern.finditer(source_code):
        line = source_code.count("\n", 0, match.start()) + 1
        fn_name = match.group(1)
        raw_params = match.group(2).strip()
        params = []
        if raw_params:
            for param in raw_params.split(","):
                clean = re.sub(r"[:=].*$", "", param.strip())
                clean = clean.lstrip("...").strip()
                if clean:
                    params.append(clean)
        text = f"Função {fn_name} com parâmetros {', '.join(params)}" if params else f"Função {fn_name}"
        extractions.append(ExtractedText(
            text=text,
            source_file=filepath,
            source_type="code",
            line_start=line,
            line_end=line,
        ))

    # Arrow functions atribuídas a const/let/var.
    arrow_pattern = re.compile(
        r"^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>",
        re.MULTILINE,
    )
    for match in arrow_pattern.finditer(source_code):
        line = source_code.count("\n", 0, match.start()) + 1
        fn_name = match.group(1)
        raw_params = match.group(2).strip()
        params = []
        if raw_params:
            for param in raw_params.split(","):
                clean = re.sub(r"[:=].*$", "", param.strip())
                clean = clean.lstrip("...").strip()
                if clean:
                    params.append(clean)
        text = f"Função {fn_name} com parâmetros {', '.join(params)}" if params else f"Função {fn_name}"
        extractions.append(ExtractedText(
            text=text,
            source_file=filepath,
            source_type="code",
            line_start=line,
            line_end=line,
        ))

    # Comentários de linha.
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("//"):
            comment = stripped[2:].strip()
            if len(comment) > 3:
                extractions.append(ExtractedText(
                    text=comment,
                    source_file=filepath,
                    source_type="comment",
                    line_start=i,
                    line_end=i,
                ))

    # Comentários em bloco e JSDoc.
    block_pattern = re.compile(r"/\*\*?[\s\S]*?\*/", re.MULTILINE)
    for match in block_pattern.finditer(source_code):
        block = match.group(0)
        line_start = source_code.count("\n", 0, match.start()) + 1
        line_end = source_code.count("\n", 0, match.end()) + 1
        cleaned_lines = []
        for raw_line in block.splitlines():
            cleaned = raw_line.strip()
            cleaned = re.sub(r"^/\*\*?", "", cleaned)
            cleaned = re.sub(r"\*/$", "", cleaned)
            cleaned = cleaned.lstrip("*").strip()
            if cleaned:
                cleaned_lines.append(cleaned)
        cleaned_text = "\n".join(cleaned_lines).strip()
        if len(cleaned_text) > 3:
            extractions.append(ExtractedText(
                text=cleaned_text,
                source_file=filepath,
                source_type="docstring",
                line_start=line_start,
                line_end=line_end,
            ))

    return extractions


def extract_repository(repo_path: str,
                       extensions: Optional[list[str]] = None) -> RepoExtraction:
    """
    Pipeline principal: extrai texto de todo o repositório.

    Args:
        repo_path: Caminho para o repositório
        extensions: Extensões de arquivo para processar
            (default: .ts, .tsx, .md, .txt, .rst)

    Returns:
        RepoExtraction com todos os textos extraídos
    """
    if extensions is None:
        extensions = [".ts", ".tsx", ".md", ".txt", ".rst"]

    result = RepoExtraction(repo_path=repo_path)
    repo = Path(repo_path)

    ignore_dirs = {".git", "__pycache__", ".venv", "venv", "node_modules", ".tox", "egg-info"}

    ts_files = 0
    doc_files = 0

    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]

        for filename in files:
            filepath = os.path.join(root, filename)
            ext = Path(filename).suffix.lower()

            if ext not in extensions:
                continue

            try:
                if ext in (".ts", ".tsx"):
                    ts_files += 1
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        source = f.read()
                    result.texts.extend(extract_typescript(source, filepath))

                elif ext in (".md", ".txt", ".rst"):
                    doc_files += 1
                    result.texts.extend(extract_markdown(filepath))

            except (IOError, PermissionError) as e:
                print(f"Erro ao ler {filepath}: {e}")

    result.stats = {
        "total_texts": len(result.texts),
        "ts_files": ts_files,
        "doc_files": doc_files,
        "by_type": {k: len(v) for k, v in result.by_type.items()},
        "total_chars": sum(len(t.text) for t in result.texts),
    }

    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extrai texto estruturado de repositórios")
    parser.add_argument("repo_path", help="Caminho do repositório para extração")
    parser.add_argument(
        "--out-jsonl",
        dest="out_jsonl",
        help="Arquivo de saída JSONL com blocos extraídos",
    )
    args = parser.parse_args()

    repo_path = args.repo_path
    extraction = extract_repository(repo_path)

    if args.out_jsonl:
        extraction.save_jsonl(args.out_jsonl)
        print(f"  JSONL salvo em: {args.out_jsonl}")

    print(f"\n📊 Estatísticas da Extração:")
    print(f"  Arquivos TypeScript: {extraction.stats['ts_files']}")
    print(f"  Arquivos de documentação: {extraction.stats['doc_files']}")
    print(f"  Total de blocos de texto: {extraction.stats['total_texts']}")
    print(f"  Total de caracteres: {extraction.stats['total_chars']:,}")
    print(f"  Por tipo: {extraction.stats['by_type']}")
