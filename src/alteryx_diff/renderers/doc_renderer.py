# ruff: noqa: E501
"""DocRenderer — renders WorkflowDocumentation to Markdown and HTML fragment.

Lives in renderers/ (not llm/) so it can be imported without LLM extras.
WorkflowDocumentation is only imported under TYPE_CHECKING to preserve
the core-import-safety guarantee from CORE-01.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Environment

if TYPE_CHECKING:
    from alteryx_diff.llm.models import WorkflowDocumentation

_MD_TEMPLATE = """# {{ doc.workflow_name }}

## Intent
{{ doc.intent }}

## Data Flow
{{ doc.data_flow }}

## Tool Inventory
| Tool ID | Type | Role |
|---------|------|------|
{% for note in doc.tool_notes -%}
| {{ note.tool_id }} | {{ note.tool_type }} | {{ note.role }} |
{% endfor %}
## Production Risks
{% for risk in doc.risks -%}
- {{ risk }}
{% endfor %}"""

_HTML_TEMPLATE = """<section class="workflow-doc" id="workflow-doc">
  <h2>{{ doc.workflow_name | e }}</h2>
  <h3>Intent</h3>
  <p>{{ doc.intent | e }}</p>
  <h3>Data Flow</h3>
  <p>{{ doc.data_flow | e }}</p>
  <h3>Tool Inventory</h3>
  <table>
    <thead><tr><th>Tool ID</th><th>Type</th><th>Role</th></tr></thead>
    <tbody>
    {% for note in doc.tool_notes -%}
    <tr><td>{{ note.tool_id }}</td><td>{{ note.tool_type | e }}</td><td>{{ note.role | e }}</td></tr>
    {% endfor -%}
    </tbody>
  </table>
  <h3>Production Risks</h3>
  <ul>
  {% for risk in doc.risks -%}
  <li>{{ risk | e }}</li>
  {% endfor -%}
  </ul>
</section>"""


class DocRenderer:
    """Renders WorkflowDocumentation to Markdown or HTML fragment.

    Stateless class — creates Jinja2 environments once on init.
    Does NOT import alteryx_diff.llm at module level; safe to use
    without the [llm] extras installed.
    """

    def __init__(self) -> None:
        # autoescape=False for Markdown (literal output — no entity encoding)
        self._env = Environment(autoescape=False)
        # autoescape=True for HTML (escapes <script> etc. via | e filter)
        self._env_html = Environment(autoescape=True)

    def to_markdown(self, doc: "WorkflowDocumentation") -> str:
        """Render WorkflowDocumentation to a complete Markdown document.

        Args:
            doc: The WorkflowDocumentation to render.

        Returns:
            A Markdown string ending with a newline.
        """
        template = self._env.from_string(_MD_TEMPLATE)
        return template.render(doc=doc).strip() + "\n"

    def to_html_fragment(self, doc: "WorkflowDocumentation") -> str:
        """Render WorkflowDocumentation to an embeddable HTML ``<section>`` fragment.

        All user-supplied content fields are HTML-escaped via Jinja2 autoescape
        (``autoescape=True``) to prevent XSS injection.

        Args:
            doc: The WorkflowDocumentation to render.

        Returns:
            An HTML string starting with ``<section class="workflow-doc"``
            and ending with ``</section>``.
        """
        template = self._env_html.from_string(_HTML_TEMPLATE)
        return template.render(doc=doc).strip()

    def write_markdown(self, doc: "WorkflowDocumentation", output_path: Path) -> Path:
        """Write the Markdown rendering of ``doc`` to ``output_path``.

        Args:
            doc: The WorkflowDocumentation to render.
            output_path: Destination file path (created or overwritten).

        Returns:
            The resolved output path.
        """
        content = self.to_markdown(doc)
        output_path.write_text(content, encoding="utf-8")
        return output_path
