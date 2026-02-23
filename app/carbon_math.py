"""
Carbon footprint calculation module.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

# Average weights in kg per item
AVERAGE_WEIGHTS = {
    "METAL": 0.015,
    "PLASTIC": 0.025,
    "GLASS": 0.200,
    "CARDBOARD": 0.050,
    "WOOD": 0.100,
    "BIODEGRADABLE": 0.030,
}


class CarbonCalculator:
    """Handles carbon footprint calculations based on detected materials."""

    def __init__(self, carbon_factors_path: str = "carbon_factors.json"):
        """
        Initialize the carbon calculator.

        Args:
            carbon_factors_path: Path to the carbon factors JSON file
        """
        self.carbon_factors = self._load_carbon_factors(carbon_factors_path)

    def _load_carbon_factors(self, path: str) -> Dict[str, float]:
        """
        Load carbon factors from JSON file (v2.0 format).

        Args:
            path: Path to carbon factors JSON file

        Returns:
            Dictionary mapping material names (uppercase) to carbon factors
        """
        try:
            carbon_path = Path(path)
            if not carbon_path.exists():
                logger.warning(f"Carbon factors file not found at {path}, using defaults")
                return self._get_default_factors()

            with open(carbon_path, "r") as f:
                data = json.load(f)
                
                # Handle v2.0 structure with nested factors
                if isinstance(data, dict) and "factors" in data:
                    factors = data["factors"]
                    version = data.get("version", "unknown")
                    logger.info(f"Loaded carbon factors v{version} from {path}")
                else:
                    # Fallback for old format
                    logger.warning("Using legacy carbon factors format")
                    factors = data
                
                # Normalize keys to uppercase
                return {k.upper(): float(v) for k, v in factors.items()}
        except Exception as e:
            logger.error(f"Error loading carbon factors: {e}, using defaults", exc_info=True)
            return self._get_default_factors()

    def _get_default_factors(self) -> Dict[str, float]:
        """Return default carbon factors if file cannot be loaded."""
        return {
            "METAL": 2.5,
            "PLASTIC": 1.5,
            "WOOD": 2.0,
            "CARDBOARD": 0.9,
            "GLASS": 0.5,
            "BIODEGRADABLE": 1.0,
        }

    def normalize_material_name(self, material: str) -> str:
        """
        Normalize material name to uppercase.

        Args:
            material: Material name to normalize

        Returns:
            Normalized material name (uppercase)
        """
        return material.upper().strip()

    def calculate_carbon_footprint(
        self, detected_materials: List[str]
    ) -> Dict[str, any]:
        """
        Calculate total weight and carbon footprint from detected materials.
        Returns per-item details with individual carbon footprints.

        Args:
            detected_materials: List of detected material names/class names

        Returns:
            Dictionary containing:
                - detected_items: List of items with name, material, weight, carbon_footprint
                - total_weight: Total weight in kg
                - total_carbon_footprint: Total carbon footprint
        """
        if not detected_materials:
            return {
                "detected_items": [],
                "total_weight": 0.0,
                "total_carbon_footprint": 0.0,
            }

        # Process each detected item
        item_details = []
        total_weight = 0.0
        total_carbon = 0.0

        for item_name in detected_materials:
            # Normalize material name to uppercase
            material = self.normalize_material_name(item_name)
            
            # Get average weight (default to 0.01 if unknown)
            avg_weight = AVERAGE_WEIGHTS.get(material, 0.01)
            
            # Get carbon factor (default to 1.0 if unknown)
            carbon_factor = self.carbon_factors.get(material, 1.0)
            
            # Calculate carbon footprint for this item
            item_carbon = avg_weight * carbon_factor
            
            # Add to totals
            total_weight += avg_weight
            total_carbon += item_carbon
            
            # Create item detail
            item_details.append({
                "name": item_name,
                "material": material,
                "weight": round(avg_weight, 3),
                "carbon_footprint": round(item_carbon, 3),
            })
            
            logger.debug(
                f"Item: {item_name} -> Material: {material}, "
                f"weight={avg_weight:.3f}kg, factor={carbon_factor}, "
                f"carbon={item_carbon:.3f}"
            )

        return {
            "detected_items": item_details,
            "total_weight": round(total_weight, 3),
            "total_carbon_footprint": round(total_carbon, 3),
        }
