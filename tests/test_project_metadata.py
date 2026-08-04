import tomllib
from pathlib import Path

REPOSITORY_ROOT = "https://github.com/l1lchucky/hermes-memory-router"


def _project_metadata() -> dict[str, object]:
    with Path("pyproject.toml").open("rb") as stream:
        return tomllib.load(stream)["project"]


def test_project_metadata_is_searchable_and_truthful() -> None:
    project = _project_metadata()
    keywords = set(project["keywords"])

    assert project["name"] == "chronalyn"
    assert "AI agent memory" in project["description"]
    assert {
        "chronalyn",
        "hermes-agent",
        "hindsight",
        "mnemosyne",
        "memory-orchestration",
        "llm-memory",
    } <= keywords
    assert "production ready" not in project["description"].lower()
    assert "production-ready" not in project["description"].lower()


def test_project_urls_use_the_current_repository_path() -> None:
    urls = _project_metadata()["urls"]

    assert urls
    assert all(str(url).startswith(REPOSITORY_ROOT) for url in urls.values())
    assert not any("github.com/l1lchucky/chronalyn" in str(url) for url in urls.values())


def test_readme_opening_names_the_implemented_memory_components() -> None:
    opening = "\n".join(Path("README.md").read_text(encoding="utf-8").splitlines()[:35])

    assert "Hermes Agent" in opening
    assert "Hindsight" in opening
    assert "Mnemosyne" in opening
    assert "not implemented" in opening
