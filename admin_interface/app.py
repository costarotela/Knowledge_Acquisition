"""
Main application for the admin interface.
"""

import streamlit as st
from typing import Dict, Callable
from .config.module_status import ADMIN_MODULES, ModuleConfig, is_module_available
from .components.module_card import render_module_card

# Configuración de la página
st.set_page_config(
    page_title="Knowledge Acquisition Admin",
    page_icon="🧠",
    layout="wide"
)

def get_module_handlers() -> Dict[str, Callable]:
    """Get handler functions for each module."""
    return {
        "knowledge_explorer": lambda: st.switch_page("pages/knowledge_explorer.py"),
        "performance_monitor": lambda: st.switch_page("pages/performance_monitor.py"),
        "validation_tools": lambda: st.switch_page("pages/validation_tools.py"),
        "agent_manager": lambda: st.switch_page("pages/agent_manager.py")
    }

def main():
    """Main application."""
    st.title("Knowledge Acquisition Admin")
    st.markdown("""
    Welcome to the Knowledge Acquisition Admin Interface. 
    Here you can manage and monitor all aspects of the knowledge acquisition system.
    """)
    
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.multiselect(
            "Filter by Status",
            options=[status.value for status in ModuleStatus],
            default=[]
        )
    with col2:
        tag_filter = st.multiselect(
            "Filter by Tags",
            options=list(set(
                tag 
                for config in ADMIN_MODULES.values() 
                for tag in config.tags
            )),
            default=[]
        )
    
    # Grid de módulos
    st.markdown("### Available Modules")
    
    handlers = get_module_handlers()
    
    # Filtrar módulos
    filtered_modules = {
        module_id: config
        for module_id, config in ADMIN_MODULES.items()
        if (not status_filter or config.status.value in status_filter) and
           (not tag_filter or any(tag in config.tags for tag in tag_filter))
    }
    
    # Mostrar módulos en grid
    cols = st.columns(2)
    for idx, (module_id, config) in enumerate(filtered_modules.items()):
        with cols[idx % 2]:
            render_module_card(
                config,
                on_click=handlers.get(module_id) if is_module_available(module_id) else None
            )
            st.markdown("---")

if __name__ == "__main__":
    main()
