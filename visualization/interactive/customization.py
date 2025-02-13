"""
Chart customization system for interactive dashboards.
"""
from typing import Dict, Any, List, Optional, Union
import plotly.graph_objects as go
import plotly.express as px
from pydantic import BaseModel
import colorsys
import numpy as np

class ChartTheme(BaseModel):
    """Chart theme configuration."""
    background_color: str = "#ffffff"
    text_color: str = "#2c3e50"
    grid_color: str = "#ecf0f1"
    colorscale: str = "viridis"  # Default plotly colorscale
    font_family: str = "Arial, sans-serif"
    title_font_size: int = 18
    axis_font_size: int = 12
    legend_font_size: int = 10
    margin: Dict[str, int] = {
        "l": 50,
        "r": 30,
        "t": 50,
        "b": 50
    }

class AxisConfig(BaseModel):
    """Axis configuration."""
    title: Optional[str] = None
    type: str = "linear"  # linear, log, date, category
    range: Optional[List[Any]] = None
    show_grid: bool = True
    grid_color: Optional[str] = None
    tick_format: Optional[str] = None
    tick_angle: int = 0
    position: str = "left"  # left, right (for y-axis)

class LegendConfig(BaseModel):
    """Legend configuration."""
    show: bool = True
    position: str = "right"  # right, left, top, bottom
    orientation: str = "vertical"  # vertical, horizontal
    title: Optional[str] = None
    font_size: Optional[int] = None

class ChartConfig(BaseModel):
    """Complete chart configuration."""
    theme: ChartTheme = ChartTheme()
    title: Optional[str] = None
    subtitle: Optional[str] = None
    x_axis: AxisConfig = AxisConfig()
    y_axis: AxisConfig = AxisConfig()
    legend: LegendConfig = LegendConfig()
    height: Optional[int] = None
    width: Optional[int] = None
    interactive: bool = True
    animation: bool = True

class ColorGenerator:
    """Generate color palettes."""
    
    @staticmethod
    def generate_palette(
        n_colors: int,
        base_color: Optional[str] = None
    ) -> List[str]:
        """Generate color palette."""
        if base_color:
            # Convert hex to HSV
            rgb = tuple(int(base_color.lstrip("#")[i:i+2], 16)/255 for i in (0, 2, 4))
            hsv = colorsys.rgb_to_hsv(*rgb)
            
            # Generate colors with different saturations and values
            colors = []
            for i in range(n_colors):
                hue = (hsv[0] + i/n_colors) % 1.0
                sat = max(0.3, hsv[1] - i/(2*n_colors))
                val = min(0.9, hsv[2] + i/(2*n_colors))
                
                rgb = colorsys.hsv_to_rgb(hue, sat, val)
                colors.append(
                    "#{:02x}{:02x}{:02x}".format(
                        int(rgb[0]*255),
                        int(rgb[1]*255),
                        int(rgb[2]*255)
                    )
                )
            
            return colors
        else:
            # Use evenly spaced hues
            return [
                "#{:02x}{:02x}{:02x}".format(
                    *[int(x*255) for x in colorsys.hsv_to_rgb(i/n_colors, 0.8, 0.9)]
                )
                for i in range(n_colors)
            ]

class ChartCustomizer:
    """Customize Plotly charts."""
    
    def __init__(self, config: ChartConfig):
        """Initialize customizer."""
        self.config = config
    
    def apply_theme(self, fig: go.Figure) -> go.Figure:
        """Apply theme to figure."""
        fig.update_layout(
            plot_bgcolor=self.config.theme.background_color,
            paper_bgcolor=self.config.theme.background_color,
            font=dict(
                family=self.config.theme.font_family,
                color=self.config.theme.text_color
            ),
            title=dict(
                text=self.config.title,
                font=dict(
                    size=self.config.theme.title_font_size
                )
            ) if self.config.title else None,
            margin=self.config.theme.margin
        )
        
        # Update colorscale if applicable
        if hasattr(fig.data[0], "colorscale"):
            fig.update_traces(colorscale=self.config.theme.colorscale)
        
        return fig
    
    def apply_axes(self, fig: go.Figure) -> go.Figure:
        """Apply axis configurations."""
        # X-axis
        fig.update_xaxes(
            title=self.config.x_axis.title,
            type=self.config.x_axis.type,
            range=self.config.x_axis.range,
            showgrid=self.config.x_axis.show_grid,
            gridcolor=self.config.x_axis.grid_color or self.config.theme.grid_color,
            tickformat=self.config.x_axis.tick_format,
            tickangle=self.config.x_axis.tick_angle,
            tickfont=dict(
                size=self.config.theme.axis_font_size
            )
        )
        
        # Y-axis
        fig.update_yaxes(
            title=self.config.y_axis.title,
            type=self.config.y_axis.type,
            range=self.config.y_axis.range,
            showgrid=self.config.y_axis.show_grid,
            gridcolor=self.config.y_axis.grid_color or self.config.theme.grid_color,
            tickformat=self.config.y_axis.tick_format,
            side=self.config.y_axis.position,
            tickfont=dict(
                size=self.config.theme.axis_font_size
            )
        )
        
        return fig
    
    def apply_legend(self, fig: go.Figure) -> go.Figure:
        """Apply legend configuration."""
        fig.update_layout(
            showlegend=self.config.legend.show,
            legend=dict(
                x=1 if self.config.legend.position == "right" else 0,
                y=1 if self.config.legend.position == "top" else 0,
                orientation=self.config.legend.orientation,
                title=dict(
                    text=self.config.legend.title
                ) if self.config.legend.title else None,
                font=dict(
                    size=self.config.legend.font_size or self.config.theme.legend_font_size
                )
            )
        )
        
        return fig
    
    def apply_size(self, fig: go.Figure) -> go.Figure:
        """Apply size configuration."""
        if self.config.height or self.config.width:
            fig.update_layout(
                height=self.config.height,
                width=self.config.width
            )
        
        return fig
    
    def apply_interactivity(self, fig: go.Figure) -> go.Figure:
        """Apply interactivity configuration."""
        fig.update_layout(
            hovermode="closest" if self.config.interactive else False
        )
        
        # Disable animations if configured
        if not self.config.animation:
            fig.update_layout(
                transition_duration=0
            )
        
        return fig
    
    def customize(self, fig: go.Figure) -> go.Figure:
        """Apply all customizations."""
        fig = self.apply_theme(fig)
        fig = self.apply_axes(fig)
        fig = self.apply_legend(fig)
        fig = self.apply_size(fig)
        fig = self.apply_interactivity(fig)
        return fig

class ChartFactory:
    """Factory for creating customized charts."""
    
    def __init__(self, config: ChartConfig):
        """Initialize factory."""
        self.config = config
        self.customizer = ChartCustomizer(config)
    
    def create_line(
        self,
        x: List[Any],
        y: List[Any],
        **kwargs
    ) -> go.Figure:
        """Create line chart."""
        fig = go.Figure()
        
        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="lines+markers",
                **kwargs
            )
        )
        
        return self.customizer.customize(fig)
    
    def create_bar(
        self,
        x: List[Any],
        y: List[Any],
        **kwargs
    ) -> go.Figure:
        """Create bar chart."""
        fig = go.Figure()
        
        fig.add_trace(
            go.Bar(
                x=x,
                y=y,
                **kwargs
            )
        )
        
        return self.customizer.customize(fig)
    
    def create_scatter(
        self,
        x: List[Any],
        y: List[Any],
        **kwargs
    ) -> go.Figure:
        """Create scatter plot."""
        fig = go.Figure()
        
        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="markers",
                **kwargs
            )
        )
        
        return self.customizer.customize(fig)
    
    def create_pie(
        self,
        values: List[Any],
        labels: List[str],
        **kwargs
    ) -> go.Figure:
        """Create pie chart."""
        fig = go.Figure()
        
        fig.add_trace(
            go.Pie(
                values=values,
                labels=labels,
                **kwargs
            )
        )
        
        return self.customizer.customize(fig)
    
    def create_heatmap(
        self,
        z: List[List[Any]],
        x: Optional[List[Any]] = None,
        y: Optional[List[Any]] = None,
        **kwargs
    ) -> go.Figure:
        """Create heatmap."""
        fig = go.Figure()
        
        fig.add_trace(
            go.Heatmap(
                z=z,
                x=x,
                y=y,
                colorscale=self.config.theme.colorscale,
                **kwargs
            )
        )
        
        return self.customizer.customize(fig)
