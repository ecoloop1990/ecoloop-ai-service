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
    "metal": 0.015,
    "plastic": 0.025,
    "glass": 0.200,
    "cardboard": 0.050,
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
        Load carbon factors from JSON file.

        Args:
            path: Path to carbon factors JSON file

        Returns:
            Dictionary mapping material names to carbon factors
        """
        try:
            carbon_path = Path(path)
            if not carbon_path.exists():
                logger.warning(f"Carbon factors file not found at {path}, using defaults")
                return self._get_default_factors()

            with open(carbon_path, "r") as f:
                factors = json.load(f)
                # Normalize keys to lowercase
                return {k.lower(): v for k, v in factors.items()}
        except Exception as e:
            logger.error(f"Error loading carbon factors: {e}, using defaults")
            return self._get_default_factors()

    def _get_default_factors(self) -> Dict[str, float]:
        """Return default carbon factors if file cannot be loaded."""
        return {
            "metal": 2.5,
            "plastic": 3.2,
            "glass": 1.8,
            "cardboard": 1.2,
        }

    def normalize_material_name(self, material: str) -> str:
        """
        Normalize material name to lowercase.

        Args:
            material: Material name to normalize

        Returns:
            Normalized material name
        """
        return material.lower().strip()

    def calculate_carbon_footprint(
        self, detected_materials: List[str]
    ) -> Dict[str, any]:
        """
        Calculate total weight and carbon footprint from detected materials.

        Args:
            detected_materials: List of detected material names

        Returns:
            Dictionary containing:
                - total_weight: Total weight in kg
                - total_carbon_footprint: Total carbon footprint
                - material_breakdown: Count of each material type
        """
        if not detected_materials:
            return {
                "total_weight": 0.0,
                "total_carbon_footprint": 0.0,
                "material_breakdown": {},
            }

        # Count materials
        material_counts: Dict[str, int] = {}
        for material in detected_materials:
            normalized = self.normalize_material_name(material)
            material_counts[normalized] = material_counts.get(normalized, 0) + 1

        # Calculate total weight and carbon footprint
        total_weight = 0.0
        total_carbon = 0.0

        for material, count in material_counts.items():
            # Get average weight (default to 0.01 if unknown)
            avg_weight = AVERAGE_WEIGHTS.get(material, 0.01)
            # Get carbon factor (default to 0 if unknown)
            carbon_factor = self.carbon_factors.get(material, 0.0)

            material_weight = count * avg_weight
            material_carbon = count * avg_weight * carbon_factor

            total_weight += material_weight
            total_carbon += material_carbon

            logger.debug(
                f"Material {material}: count={count}, weight={material_weight:.3f}kg, "
                f"carbon={material_carbon:.3f}"
            )

        return {
            "total_weight": round(total_weight, 3),
            "total_carbon_footprint": round(total_carbon, 3),
            "material_breakdown": material_counts,
        }

