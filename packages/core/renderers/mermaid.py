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

            # Post-process SVG for massive high-resolution block display (42px text, 450px block cards)
            try:
                import re
                svg_content = output_path.read_text(encoding="utf-8")
                
                # Replace fixed width/height with 100% responsive bounds
                svg_content = re.sub(r'width="[0-9.]+(px)?"', 'width="100%"', svg_content, count=1)
                svg_content = re.sub(r'height="[0-9.]+(px)?"', 'height="100%"', svg_content, count=1)
                svg_content = re.sub(r'style="[^"]*max-width:[^"]*"', 'style="width: 100%; height: 100%; min-height: 800px;"', svg_content)
                
                if 'preserveAspectRatio' not in svg_content:
                    svg_content = re.sub(r'<svg ', '<svg preserveAspectRatio="xMidYMid meet" ', svg_content, count=1)

                # Inject high-impact CSS for massive block cards (42px text, 450px wide blocks)
                high_impact_css = """
/* VisionOps High-Impact Custom Diagram Styles */
.node rect, .node polygon, .node path, .node circle {
    stroke-width: 5px !important;
    fill: #1e1b4b !important;
    stroke: #818cf8 !important;
    rx: 20px !important;
    ry: 20px !important;
    filter: drop-shadow(0px 10px 20px rgba(0,0,0,0.7)) !important;
}
.node foreignObject {
    min-width: 420px !important;
    min-height: 120px !important;
    overflow: visible !important;
}
.nodeLabel, .node .label, .node span, .node div, foreignObject div {
    font-size: 42px !important;
    font-weight: 900 !important;
    color: #ffffff !important;
    fill: #ffffff !important;
    line-height: 1.4 !important;
    padding: 20px 30px !important;
    text-align: center !important;
}
.edgeLabel, .edgeLabel span, .edgeLabel div {
    font-size: 30px !important;
    font-weight: 800 !important;
    color: #38bdf8 !important;
    fill: #38bdf8 !important;
    background-color: #0f172a !important;
    padding: 8px 18px !important;
    border-radius: 10px !important;
    border: 2px solid rgba(56, 189, 248, 0.5) !important;
}
.edgePath .path {
    stroke-width: 5.5px !important;
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
            "%%{init: { 'theme': 'dark', 'flowchart': { 'defaultRenderer': 'dagre', 'curve': 'basis', 'nodeSpacing': 60, 'rankSpacing': 100, 'padding': 35, 'useMaxWidth': false }, 'themeVariables': { 'darkMode': true, 'fontSize': '36px', 'primaryColor': '#1e1b4b', 'primaryTextColor': '#ffffff', 'primaryBorderColor': '#818cf8', 'lineColor': '#38bdf8', 'secondaryColor': '#065f46', 'tertiaryColor': '#1e293b' } } }%%"
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
            # Force Top-to-Bottom (TB) vertical layout for all flowcharts so steps stack cleanly top-to-bottom
            lines.append("flowchart TB")
            
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
                
            # Always enforce a strict vertical top-to-bottom process chain across nodes
            if len(diagram.nodes) > 1:
                # Map existing edge labels by pair if available
                label_map = {(e.source, e.target): e.label for e in diagram.edges if e.label}
                for i in range(len(diagram.nodes) - 1):
                    src_id = diagram.nodes[i].id
                    tgt_id = diagram.nodes[i+1].id
                    lbl = label_map.get((src_id, tgt_id)) or next((e.label for e in diagram.edges if (e.source == src_id or e.target == tgt_id) and e.label), None)
                    if lbl:
                        escaped_lbl = lbl.replace('"', '#quot;')
                        lines.append(f'    {src_id} -->|"{escaped_lbl}"| {tgt_id}')
                    else:
                        lines.append(f'    {src_id} --> {tgt_id}')

        return "\n".join(lines)
