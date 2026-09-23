"""Mermaid diagram renderer."""

import logging
import subprocess
import tempfile
from pathlib import Path

from packages.core.models import DiagramSpec
from packages.core.renderers.base import DiagramRenderer, RendererError

logger = logging.getLogger("visionops.renderers.mermaid")


class MermaidRenderer(DiagramRenderer):
    """Renders DiagramSpec to SVG using mermaid-cli (mmdc)."""

    def render(self, diagram: DiagramSpec, output_path: Path) -> Path:
        """Generate Mermaid source and render to SVG."""
        # 1. Validate spec
        errors = diagram.validate_edge_references()
        if errors:
            raise RendererError(f"Invalid diagram specification: {', '.join(errors)}")
            
        # 2. Generate Mermaid source
        mermaid_src = self._generate_mermaid(diagram)
        logger.debug(f"Mermaid source:\n{mermaid_src}")

        # 3. Render using mmdc
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with tempfile.NamedTemporaryFile(suffix=".mmd", mode="w", delete=False) as f:
            f.write(mermaid_src)
            temp_mmd_path = f.name
            
        try:
            # We use npx to run the locally installed mermaid-cli
            result = subprocess.run(
                ["npx", "mmdc", "-i", temp_mmd_path, "-o", str(output_path), "-b", "transparent"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                raise RendererError(f"mmdc failed: {result.stderr}")
                
            if not output_path.exists():
                raise RendererError("mmdc completed but output file not found")
                
            return output_path
            
        finally:
            Path(temp_mmd_path).unlink(missing_ok=True)

    def _generate_mermaid(self, diagram: DiagramSpec) -> str:
        """Convert DiagramSpec to Mermaid syntax with modern styling."""
        lines = [
            "%%{init: { 'theme': 'dark', 'themeVariables': { 'darkMode': true, 'fontSize': '18px', 'primaryColor': '#1e1b4b', 'primaryTextColor': '#f8fafc', 'primaryBorderColor': '#818cf8', 'lineColor': '#38bdf8', 'secondaryColor': '#065f46', 'tertiaryColor': '#1e293b' } } }%%"
        ]
        
        if diagram.layout == "sequence":
            lines.append("sequenceDiagram")
            lines.append("    autonumber")
            
            # Add nodes as participants
            for node in diagram.nodes:
                escaped_label = node.label.replace('"', '\\"').replace(" (", "<br/>(").replace(" [", "<br/>[")
                lines.append(f'    participant {node.id} as {escaped_label}')
                
            # Add edges as messages
            for edge in diagram.edges:
                label = edge.label or ""
                arrow = "->>" if edge.direction == "forward" else "-->>"
                lines.append(f'    {edge.source}{arrow}{edge.target}: {label}')
        else:
            # Default to Top-Down (TD) for readable vertical process flowcharts
            direction = "LR" if diagram.layout == "flowchart_lr" else "TD"
            lines.append(f"graph {direction}")
            
            # Nodes
            for node in diagram.nodes:
                escaped_label = node.label.replace('"', '#quot;').replace(" (", "<br/>(").replace(" [", "<br/>[")
                if node.type in ("input", "output"):
                    shape_start, shape_end = ("([", "])")
                elif node.type == "process":
                    shape_start, shape_end = ("[", "]")
                else:
                    shape_start, shape_end = ("([", "])")
                    
                lines.append(f'    {node.id}{shape_start}"{escaped_label}"{shape_end}')
                
            # Edges
            for edge in diagram.edges:
                label = edge.label
                arrow = "<-->" if edge.direction == "bidirectional" else "-->"
                    
                if label:
                    escaped_edge_label = label.replace('"', '#quot;')
                    lines.append(f'    {edge.source} {arrow}|"{escaped_edge_label}"| {edge.target}')
                else:
                    lines.append(f'    {edge.source} {arrow} {edge.target}')

        return "\n".join(lines)
