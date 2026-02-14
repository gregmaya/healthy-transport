import matplotlib.pyplot as plt
import seaborn as sns
from cycler import cycler
import traceback

try:
    import contextily as ctx
except ImportError:
    ctx = None

# --- Color Palettes ---
# Modern, accessible, web-friendly colors
PALETTE = {
    # Brand: Deep Teal / Ocean Blue
    "brand": "#006D77",
    "brand_light": "#83C5BE",
    "brand_dark": "#003F44",

    # Accents
    "accent_warm": "#E29578",  # Soft Terra Cotta
    "accent_yellow": "#FFDDD2", # Pale Peach/Yellow

    # Neutrals
    "background": "#F9F9F9",
    "text": "#333333",
    "grid": "#E0E0E0",
    
    # Categorical (Land Use / Types)
    "residential": "#FFEDD5", # Light Orange
    "commercial": "#CBD5E1",  # Light Blue-Grey
    "park": "#A7C957",        # Soft Green
    "water": "#A2D2FF",       # Light Blue
    "transport": "#6C757D",   # Grey
}

# Diverging Palette for Heatmaps
# Example: RdBu equivalent but custom or just use standard
DIVERGING_CMAP = "RdBu_r"

# Categorical List for cycling
COLOR_CYCLE = [
    PALETTE["brand"],
    PALETTE["accent_warm"],
    PALETTE["park"],
    PALETTE["water"],
    PALETTE["brand_dark"],
    PALETTE["brand_light"],
]

def apply_style():
    """
    Applies the project's visual style to Matplotlib and Seaborn.
    """
    # Base Style
    sns.set_style("whitegrid")
    
    # Custom rcParams
    plt.rcParams.update({
        # Figure and Axes
        "figure.facecolor": PALETTE["background"],
        "axes.facecolor": PALETTE["background"],
        "axes.edgecolor": PALETTE["background"], # Hide edges mostly
        "axes.grid": True,
        "grid.color": PALETTE["grid"],
        "grid.linestyle": "-",
        "grid.linewidth": 0.8,
        
        # Fonts
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "text.color": PALETTE["text"],
        "axes.labelcolor": PALETTE["text"],
        "xtick.color": PALETTE["text"],
        "ytick.color": PALETTE["text"],
        
        # Titles
        "axes.titleweight": "bold",
        "axes.titlesize": 14,
        "axes.labelsize": 12,
        
        # Color Cycle
        "axes.prop_cycle": cycler(color=COLOR_CYCLE),
        
        # Lines
        "lines.linewidth": 2,
        
        # Legend
        "legend.frameon": False,
        "legend.numpoints": 1,
        "legend.scatterpoints": 1,
    })

def get_categorical_color(category):
    """
    Returns the color for a specific category (e.g. land use).
    """
    mapping = {
        "Residential": PALETTE["residential"],
        "Commercial": PALETTE["commercial"],
        "Park": PALETTE["park"],
        "Green": PALETTE["park"],
        "Water": PALETTE["water"],
        "Transport": PALETTE["transport"],
    }
    return mapping.get(category, "#999999") # Default grey

def add_basemap(ax, source=None, zoom=None, crs="EPSG:25832"):
    """
    Adds a basemap to the given axes.
    
    Args:
        ax: Matplotlib axes object.
        source: Contextily provider (default: CartoDB.Positron for light/clean look).
        zoom: Zoom level (optional).
        crs: Coordinate reference system of the data in the axes (default: EPSG:25832 for Denmark).
             Contextily expects Web Mercator (EPSG:3857), so this helps it convert.
             If your data is already 3857, set crs='EPSG:3857'.
    """
    if ctx is None:
        print("Error: Contextily not installed. Cannot add basemap.")
        return

    if source is None:
        try:
            source = ctx.providers.CartoDB.PositronNoLabels
        except AttributeError:
             # Fallback for older contextily versions or different structure
             source = ctx.providers.CartoDB.Positron if hasattr(ctx.providers, 'CartoDB') else None

    try:
        if source is not None:
             try:
                 ctx.add_basemap(ax, source=source, zoom=zoom, crs=crs)
             except Exception as e:
                 if zoom is None:
                     print(f"Auto-zoom failed: {e}. Retrying with zoom=13.")
                     ctx.add_basemap(ax, source=source, zoom=13, crs=crs)
                 else:
                     raise e
             ax.set_axis_off() # Usually looks better without axis ticks for maps
        else:
             print("Error: Could not determine basemap source.")
    except Exception as e:
        print(f"Error adding basemap: {e}")
        import traceback
        traceback.print_exc()
        print("Ensure 'contextily' is installed (pip install contextily).")

if __name__ == "__main__":
    # Test the style
    apply_style()
    import numpy as np
    x = np.linspace(0, 10, 100)
    plt.figure(figsize=(8, 5))
    plt.plot(x, np.sin(x), label="Sine")
    plt.plot(x, np.cos(x), label="Cosine")
    plt.title("Style Test: Sine and Cosine")
    plt.legend()
    plt.show()
