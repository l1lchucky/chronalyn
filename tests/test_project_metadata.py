import tomllib
from pathlib import Path

REPOSITORY_ROOT = "https://github.com/l1lchucky/chronalyn"


def _project_metadata() -> dict[str, object]:
    with Path("pyproject.toml").open("rb") as stream:
        return tomllib.load(stream)["project"]


def test_project_metadata_is_searchable_and_truthful() -> None:
    project = _project_metadata()
    keywords = set(project["keywords"])

    assert project["name"] == "chronalyn"
    assert "memory" in project["description"].lower()
    assert "Hermes" in project["description"]
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
    # The canonical repository is chronalyn; the old slug must not appear.
    assert all("hermes-memory-router" not in str(url) for url in urls.values())


def test_readme_opening_names_the_implemented_memory_components() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    opening = "\n".join(readme.splitlines()[:35])

    assert "Hermes Agent" in opening
    assert "Hindsight" in opening
    assert "Mnemosyne" in opening
    # The README must separate current features from future ideas.
    assert "What is not in Chronalyn 1.0" in readme
