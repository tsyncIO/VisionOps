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
        """Convert DiagramSpec to Mermaid syntax."""
        lines = []
        
        if diagram.layout == "sequence":
            lines.append("sequenceDiagram")
            lines.append(f"    autonumber")
            
            # Add nodes as participants
            for node in diagram.nodes:
                escaped_label = node.label.replace('"', '\\"')
                lines.append(f'    participant {node.id} as {escaped_label}')
                
            # Add edges as messages
            for edge in diagram.edges:
                label = edge.label or ""
                arrow = "->>" if edge.direction == "forward" else "-->>"
                lines.append(f'    {edge.source}{arrow}{edge.target}: {label}')
        else:
            # Default to flowchart
            lines.append("graph TD")
            
            # Nodes
            for node in diagram.nodes:
                # Flowchart supports different shapes based on type, but for simplicity
                # we'll use rounded rectangles for everything or specific ones if requested.
                escaped_label = node.label.replace('"', '#quot;')
                shape_start, shape_end = ("(", ")") if node.type == "process" else ("[", "]")
                lines.append(f'    {node.id}{shape_start}"{escaped_label}"{shape_end}')
                
            # Edges
            for edge in diagram.edges:
                label = edge.label
                
                if edge.direction == "bidirectional":
                    arrow = "<-->"
                elif edge.direction == "backward":
                    # While mermaid doesn't strictly have a "backward" arrow that flips the node order, 
                    # we can represent it as a directed edge.
                    # Usually better to just swap source/target if backward, but mermaid supports it.
                    arrow = "-->" 
                else:
                    arrow = "-->"
                    
                if label:
                    escaped_edge_label = label.replace('"', '#quot;')
                    lines.append(f'    {edge.source} {arrow}|"{escaped_edge_label}"| {edge.target}')
                else:
                    lines.append(f'    {edge.source} {arrow} {edge.target}')

        return "\n".join(lines)
