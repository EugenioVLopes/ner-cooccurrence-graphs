"""
ner_pipeline.py - Pipeline de Named Entity Recognition para código-fonte

Combina NER tradicional (spaCy) com extração customizada de entidades
de código (bibliotecas, classes, funções, tecnologias).
"""

import re
from dataclasses import dataclass
from collections import Counter
from typing import Optional

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False


@dataclass
class Entity:
    """Entidade reconhecida no texto."""
    text: str
    label: str  # PER, ORG, LOC, LIB, CLASS, FUNC, TECH, MISC
    source_file: str = ""
    start: int = 0
    end: int = 0

    def __hash__(self):
        return hash((self.text.lower(), self.label))

    def __eq__(self, other):
        return self.text.lower() == other.text.lower() and self.label == other.label

    @property
    def normalized(self) -> str:
        """Nome normalizado para o grafo."""
        return self.text.strip().lower()


# =============================================================================
# Padrões de entidades específicas de código
# =============================================================================

# Bibliotecas/pacotes conhecidos (npm / Node.js)
KNOWN_LIBRARIES = {
    "react", "nextjs", "express", "fastify", "koa", "nest", "nestjs",
    "axios", "node-fetch", "superagent",
    "zod", "yup", "joi", "ajv", "typebox",
    "prisma", "typeorm", "sequelize", "knex", "drizzle",
    "jest", "vitest", "mocha", "chai", "playwright", "cypress",
    "webpack", "vite", "esbuild", "rollup", "turbopack", "swc",
    "tailwind", "styled-components", "emotion", "sass",
    "redux", "zustand", "mobx", "jotai", "recoil",
    "lodash", "lodash-es", "ramda", "date-fns", "dayjs",
    "winston", "pino", "bunyan",
    "openai", "langchain", "anthropic", "claude",
    "ink", "chalk", "commander", "yargs", "meow",
    "socket.io", "rxjs",
    "puppeteer", "jimp",
    "sentry", "datadog", "growthbook",
    "eslint", "prettier", "biome",
}

# Tecnologias e frameworks
KNOWN_TECH = {
    "python", "javascript", "typescript", "rust", "java", "c++",
    "docker", "kubernetes", "k8s", "git", "github", "gitlab",
    "linux", "ubuntu", "windows", "macos",
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "api", "rest", "graphql", "grpc", "websocket",
    "ci/cd", "jenkins", "github actions", "terraform", "ansible",
    "llm", "gpt", "bert", "transformer", "embedding",
    "machine learning", "deep learning", "nlp", "ner",
    "oauth", "jwt", "mcp",
}

# Palavras a ignorar — path fragments, protocolos genéricos, palavras ambíguas
STOPWORDS = {
    # path fragments comuns em imports TS
    "src", "lib", "dist", "types", "utils", "index", "test", "tests",
    "config", "scripts", "build", "out", "tmp", "vendor",
    # protocolos genéricos (pouco valor semântico)
    "http", "https", "tcp", "udp", "ssh",
    # palavras ambíguas que geram falsos positivos
    "go", "next", "fetch", "path", "ora", "got", "ws",
    "attention", "sharp", "moment",
    # erros comuns, JS builtins
    "error", "string", "number", "boolean", "object", "array",
    "null", "undefined", "void", "any", "never", "unknown",
}


def extract_code_entities(text: str, source_file: str = "") -> list[Entity]:
    """
    Extrai entidades específicas de código usando regex e heurísticas.
    """
    entities = []
    text_lower = text.lower()

    # 1. TS/JS imports: import ... from 'package'
    for match in re.finditer(r"""import\s+(?:type\s+)?(?:[\w*${}\s,]+\s+from\s+)?['"]([^'"]+)['"]""", text):
        pkg = match.group(1)
        if not pkg.startswith("."):
            base = pkg.split("/")[0].lstrip("@")
            name = base.lower()
            if name not in STOPWORDS and (name in KNOWN_LIBRARIES or len(base) > 2):
                entities.append(Entity(
                    text=name, label="LIB", source_file=source_file,
                    start=match.start(), end=match.end()
                ))

    # 2. Classes: "class NomeDaClasse" ou "Classe NomeDaClasse"
    for match in re.finditer(r'[Cc]lass[e]?\s+([A-Z][a-zA-Z0-9_]+)', text):
        entities.append(Entity(
            text=match.group(1), label="CLASS", source_file=source_file,
            start=match.start(), end=match.end()
        ))

    # 3. Funções: "function nome" ou "Função nome"
    for match in re.finditer(r'(?:function|[Ff]unção)\s+([a-zA-Z_][a-zA-Z0-9_]+)', text):
        name = match.group(1)
        entities.append(Entity(
            text=name, label="FUNC", source_file=source_file,
            start=match.start(), end=match.end()
        ))

    # 4. Bibliotecas conhecidas mencionadas no texto
    for lib in KNOWN_LIBRARIES:
        if lib in text_lower:
            pattern = r'\b' + re.escape(lib) + r'\b'
            if re.search(pattern, text_lower):
                entities.append(Entity(
                    text=lib, label="LIB", source_file=source_file,
                ))

    # 5. Tecnologias mencionadas
    for tech in KNOWN_TECH:
        if tech in text_lower:
            pattern = r'\b' + re.escape(tech) + r'\b'
            if re.search(pattern, text_lower):
                entities.append(Entity(
                    text=tech, label="TECH", source_file=source_file,
                ))

    # 6. CamelCase como possíveis classes/tipos
    camelcase_ignore = {
        "TypeError", "ValueError", "KeyError", "IndexError",
        "RangeError", "SyntaxError", "ReferenceError",
        "PowerShell", "JavaScript", "TypeScript",
    }
    for match in re.finditer(r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b', text):
        name = match.group(1)
        if name not in camelcase_ignore and name.lower() not in STOPWORDS:
            entities.append(Entity(
                text=name, label="CLASS", source_file=source_file,
                start=match.start(), end=match.end()
            ))

    return entities


def extract_spacy_entities(text: str, nlp, source_file: str = "") -> list[Entity]:
    """
    Extrai entidades usando spaCy (PER, ORG, LOC, MISC).
    """
    doc = nlp(text)
    entities = []

    # Mapeamento de labels do spaCy para nosso esquema
    label_map = {
        "PERSON": "PER", "PER": "PER",
        "ORG": "ORG", "ORGANIZATION": "ORG",
        "GPE": "LOC", "LOC": "LOC", "FAC": "LOC",
        "PRODUCT": "TECH", "WORK_OF_ART": "MISC",
        "EVENT": "MISC", "LANGUAGE": "TECH",
    }

    for ent in doc.ents:
        label = label_map.get(ent.label_, "MISC")
        if len(ent.text.strip()) > 1:  # ignora entidades de 1 caractere
            entities.append(Entity(
                text=ent.text.strip(),
                label=label,
                source_file=source_file,
                start=ent.start_char,
                end=ent.end_char,
            ))

    return entities


class NERPipeline:
    """
    Pipeline completo de NER que combina spaCy com extração customizada.
    """

    def __init__(self, spacy_model: str = "pt_core_news_lg", use_spacy: bool = True):
        self.use_spacy = use_spacy and SPACY_AVAILABLE
        self.nlp = None

        if self.use_spacy:
            try:
                self.nlp = spacy.load(spacy_model)
                # Aumentar limite para textos grandes
                self.nlp.max_length = 2_000_000
                print(f"✅ Modelo spaCy carregado: {spacy_model}")
            except OSError:
                print(f"⚠️  Modelo '{spacy_model}' não encontrado. "
                      f"Instale com: python -m spacy download {spacy_model}")
                print("   Continuando apenas com extração customizada.")
                self.use_spacy = False

    def extract(self, text: str, source_file: str = "") -> list[Entity]:
        """
        Extrai entidades de um texto combinando múltiplas estratégias.
        """
        entities = []

        # Extração customizada de código
        entities.extend(extract_code_entities(text, source_file))

        # Extração com spaCy (se disponível)
        if self.use_spacy and self.nlp:
            # Limitar tamanho do texto para spaCy
            truncated = text[:1_000_000] if len(text) > 1_000_000 else text
            entities.extend(extract_spacy_entities(truncated, self.nlp, source_file))

        # Deduplicar
        entities = self._deduplicate(entities)

        return entities

    def extract_batch(self, texts: list[dict]) -> list[list[Entity]]:
        """
        Extrai entidades de múltiplos textos.
        
        Args:
            texts: Lista de dicts com 'text' e opcionalmente 'source_file'
        
        Returns:
            Lista de listas de entidades (uma por texto)
        """
        results = []
        for item in texts:
            text = item["text"] if isinstance(item, dict) else item
            source = item.get("source_file", "") if isinstance(item, dict) else ""
            results.append(self.extract(text, source))
        return results

    @staticmethod
    def _deduplicate(entities: list[Entity]) -> list[Entity]:
        """Remove entidades duplicadas mantendo a ordem."""
        seen = set()
        unique = []
        for e in entities:
            key = (e.normalized, e.label)
            if key not in seen:
                seen.add(key)
                unique.append(e)
        return unique

    @staticmethod
    def summarize(entities: list[Entity]) -> dict:
        """Gera um resumo das entidades encontradas."""
        by_label = {}
        for e in entities:
            by_label.setdefault(e.label, []).append(e.text)

        return {
            "total": len(entities),
            "by_label": {k: len(v) for k, v in by_label.items()},
            "top_entities": Counter(e.normalized for e in entities).most_common(20),
            "unique_entities": len(set(e.normalized for e in entities)),
        }


if __name__ == "__main__":
    # Exemplo de uso
    sample_text = """
    import { Tool } from './tools';
    import Anthropic from '@anthropic-ai/sdk';
    The BashTool class extends BaseTool and implements
    the execute method. The project uses React for the UI
    and PostgreSQL as the database. Uses zod for validation.
    """

    pipeline = NERPipeline(use_spacy=True)
    entities = pipeline.extract(sample_text)

    print("\n🏷️  Entidades encontradas:")
    for e in entities:
        print(f"  [{e.label}] {e.text}")

    print(f"\n📊 Resumo:")
    summary = NERPipeline.summarize(entities)
    for k, v in summary.items():
        print(f"  {k}: {v}")
