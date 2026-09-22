"""Tests for the renderer subsystem."""

from pathlib import Path

import pytest

from packages.core.models import DiagramEdge, DiagramNode, DiagramSpec
from packages.core.renderers.mermaid import MermaidRenderer


def test_mermaid_generate():
    renderer = MermaidRenderer()
    diagram = DiagramSpec(
        title="Test Diagram",
        nodes=[
            DiagramNode(id="A", label="Node A", type="component"),
            DiagramNode(id="B", label="Node B", type="process"),
        ],
        edges=[
            DiagramEdge(source="A", target="B", label="Flow", direction="forward")
        ],
        layout="flowchart"
    )
    
    mermaid_src = renderer._generate_mermaid(diagram)
    
    assert "graph TD" in mermaid_src
    assert 'A["Node A"]' in mermaid_src
    assert 'B("Node B")' in mermaid_src
    assert 'A -->|"Flow"| B' in mermaid_src


@pytest.mark.asyncio
async def test_mermaid_render_svg(tmp_path):
    renderer = MermaidRenderer()
    diagram = DiagramSpec(
        title="Test Diagram",
        nodes=[
            DiagramNode(id="A", label="Node A"),
            DiagramNode(id="B", label="Node B"),
        ],
        edges=[
            DiagramEdge(source="A", target="B", label="Flow")
        ]
    )
    
    output_path = tmp_path / "output.svg"
    rendered_path = renderer.render(diagram, output_path)
    
    assert rendered_path.exists()
    assert rendered_path.suffix == ".svg"
    
    content = rendered_path.read_text()
    assert "<svg" in content
