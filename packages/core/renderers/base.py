"""Renderer protocol for generating diagrams from DiagramSpec."""

import abc
from pathlib import Path

from packages.core.models import DiagramSpec


class RendererError(Exception):
    """Error raised when rendering fails."""
    pass


class DiagramRenderer(abc.ABC):
    """Protocol for diagram renderers."""

    @abc.abstractmethod
    def render(self, diagram: DiagramSpec, output_path: Path) -> Path:
        """Render a DiagramSpec to SVG.

        Args:
            diagram: The structured diagram specification.
            output_path: Where to save the output SVG.

        Returns:
            The path to the rendered SVG.

        Raises:
            RendererError: If the rendering fails.
        """
        ...
