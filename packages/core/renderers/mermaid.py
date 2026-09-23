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
        
        with tempfile.NamedTemporaryFile(suffix=".mmd", mode="w", delete=False) as f_mmd, \
             tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f_cfg:
            f_mmd.write(mermaid_src)
            temp_mmd_path = f_mmd.name
            
            import json
            json.dump({"args": ["--no-sandbox", "--disable-setuid-sandbox"]}, f_cfg)
            temp_cfg_path = f_cfg.name
            
        try:
            # We use npx to run the locally installed mermaid-cli with puppeteer sandbox options
            result = subprocess.run(
                ["npx", "mmdc", "-p", temp_cfg_path, "-i", temp_mmd_path, "-o", str(output_path), "-b", "transparent"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                raise RendererError(f"mmdc failed: {result.stderr}")
                
            if not output_path.exists():
                raise RendererError("mmdc completed but output file not found")

            # Post-process SVG for 100% full-panel responsive display with enlarged text & blocks
            try:
                import re
                svg_content = output_path.read_text(encoding="utf-8")
                
                # Replace fixed width/height with 100% responsive bounds
                svg_content = re.sub(r'width="[0-9.]+(px)?"', 'width="100%"', svg_content, count=1)
                svg_content = re.sub(r'height="[0-9.]+(px)?"', 'height="100%"', svg_content, count=1)
                svg_content = re.sub(r'style="[^"]*max-width:[^"]*"', 'style="width: 100%; height: 100%; max-width: 100%;"', svg_content)
                
                if 'preserveAspectRatio' not in svg_content:
                    svg_content = re.sub(r'<svg ', '<svg preserveAspectRatio="xMidYMid meet" ', svg_content, count=1)

                # Inject high-impact CSS for massive block cards, huge 36px text, and 5px thick lines
                high_impact_css = """
/* VisionOps High-Impact Custom Diagram Styles */
.node rect, .node polygon, .node path, .node circle {
    stroke-width: 4px !important;
    fill: #1e1b4b !important;
    stroke: #818cf8 !important;
    rx: 16px !important;
    ry: 16px !important;
    filter: drop-shadow(0px 8px 16px rgba(0,0,0,0.6)) !important;
}
.node foreignObject {
    min-width: 320px !important;
    min-height: 90px !important;
    overflow: visible !important;
}
.nodeLabel, .node .label, .node span, .node div, foreignObject div {
    font-size: 34px !important;
    font-weight: 900 !important;
    color: #ffffff !important;
    fill: #ffffff !important;
    line-height: 1.4 !important;
    padding: 16px 24px !important;
    text-align: center !important;
}
.edgeLabel, .edgeLabel span, .edgeLabel div {
    font-size: 26px !important;
    font-weight: 800 !important;
    color: #38bdf8 !important;
    fill: #38bdf8 !important;
    background-color: #0f172a !important;
    padding: 6px 14px !important;
    border-radius: 8px !important;
    border: 1px solid rgba(56, 189, 248, 0.4) !important;
}
.edgePath .path {
    stroke-width: 4.5px !important;
    stroke: #38bdf8 !important;
}
"""
                if '</style>' in svg_content:
                    svg_content = svg_content.replace('</style>', high_impact_css + '</style>')

                output_path.write_text(svg_content, encoding="utf-8")
            except Exception as e:
                logger.warning(f"SVG post-processing warning: {e}")

            return output_path
            
        finally:
            Path(temp_mmd_path).unlink(missing_ok=True)
            Path(temp_cfg_path).unlink(missing_ok=True)

    def _generate_mermaid(self, diagram: DiagramSpec) -> str:
        """Convert DiagramSpec to Mermaid syntax with modern high-impact styling."""
        lines = [
            "%%{init: { 'theme': 'dark', 'flowchart': { 'nodeSpacing': 80, 'rankSpacing': 100, 'padding': 40, 'useMaxWidth': false }, 'themeVariables': { 'darkMode': true, 'fontSize': '36px', 'primaryColor': '#1e1b4b', 'primaryTextColor': '#ffffff', 'primaryBorderColor': '#818cf8', 'lineColor': '#38bdf8', 'secondaryColor': '#065f46', 'tertiaryColor': '#1e293b' } } }%%"
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
            # Force Top-Down (TD) layout for all flowcharts so process steps stack vertically and fit the screen panel
            lines.append("graph TD")
            
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
