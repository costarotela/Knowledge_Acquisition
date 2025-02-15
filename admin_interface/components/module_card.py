"""
Component for displaying admin module cards with status.
"""

import streamlit as st
from typing import Callable, Optional
from ..config.module_status import ModuleConfig, ModuleStatus

def get_status_color(status: ModuleStatus) -> str:
    """Get color for status badge."""
    colors = {
        ModuleStatus.PLANNED: "gray",
        ModuleStatus.IN_DEVELOPMENT: "blue",
        ModuleStatus.TESTING: "yellow",
        ModuleStatus.BETA: "orange",
        ModuleStatus.PRODUCTION: "green",
        ModuleStatus.DEPRECATED: "red"
    }
    return colors.get(status, "gray")

def render_module_card(
    config: ModuleConfig,
    on_click: Optional[Callable] = None
) -> None:
    """Render a module card with status information."""
    
    # Card container
    with st.container():
        # Título y badge de estado
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(config.name)
        with col2:
            st.markdown(
                f'<span style="background-color: {get_status_color(config.status)}; '
                f'padding: 4px 8px; border-radius: 4px; color: white;">'
                f'{config.status.value.upper()}</span>',
                unsafe_allow_html=True
            )
        
        # Descripción
        st.markdown(config.description)
        
        # Métricas y tags
        col1, col2, col3 = st.columns(3)
        with col1:
            if config.test_coverage > 0:
                st.metric("Test Coverage", f"{config.test_coverage*100:.0f}%")
        with col2:
            if config.implementation_date:
                st.metric("Implemented", config.implementation_date.strftime("%Y-%m-%d"))
        with col3:
            st.markdown(" ".join([f"`{tag}`" for tag in config.tags]))
        
        # Dependencias
        if config.dependencies:
            st.markdown("#### Dependencies")
            for dep in config.dependencies:
                st.markdown(f"- {dep.description}")
        
        # Botón de acción
        if config.enabled and on_click:
            st.button(
                "Open Module",
                on_click=on_click,
                disabled=not config.enabled,
                key=f"btn_{config.id}"
            )
        elif not config.enabled:
            st.button(
                "Coming Soon",
                disabled=True,
                key=f"btn_{config.id}"
            )
