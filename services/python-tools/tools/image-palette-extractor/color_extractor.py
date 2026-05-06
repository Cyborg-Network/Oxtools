"""
Color Extraction Module
========================
Extracts dominant colors from images using KMeans clustering.
Handles preprocessing, noise removal, and color sorting.
"""

import io
import logging
from base64 import b64decode
from typing import List, Tuple

import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
from colorsys import rgb_to_hsv

logger = logging.getLogger(__name__)


class ColorExtractor:
    """Extracts and processes dominant colors from images."""
    
    def __init__(self, num_colors: int = 8, resize_size: int = 150):
        """
        Initialize color extractor.
        
        Args:
            num_colors: Number of dominant colors to extract (default 8)
            resize_size: Size to resize image for processing (smaller = faster)
        """
        self.num_colors = num_colors
        self.resize_size = resize_size
    
    def extract_from_base64(self, image_base64: str) -> List[str]:
        """
        Extract colors from base64-encoded image.
        
        Args:
            image_base64: Base64 string with data URI prefix (e.g., "data:image/png;base64,...")
            
        Returns:
            List of dominant colors as hex strings
        """
        try:
            # Remove data URI prefix if present
            if image_base64.startswith("data:"):
                image_base64 = image_base64.split(",", 1)[1]
            
            # Decode base64 to bytes
            image_bytes = b64decode(image_base64)
            image = Image.open(io.BytesIO(image_bytes))
            
            return self.extract_from_image(image)
        except Exception as e:
            logger.error(f"Failed to extract from base64: {e}")
            raise ValueError(f"Invalid image data: {str(e)}")
    
    def get_pixel_map(
        self,
        image_base64: str,
        max_pixels: int = 15000,
        max_dim: int = 800,
    ) -> Tuple[str, List[dict], int, int]:
        """
        Get a safely-sized pixel map and a downscaled image data URI suitable for frontend preview.

        Args:
            image_base64: Base64 string of image (may include data: prefix)
            max_pixels: Maximum number of pixels to return in the pixel map (safety cap)
            max_dim: Maximum longest edge (width or height) for the returned image

        Returns:
            Tuple of (data_uri_image, pixel_list, width, height)
        """
        try:
            # Normalize base64 payload
            if image_base64.startswith("data:"):
                header, image_base64 = image_base64.split(",", 1)
            else:
                header = "data:image/png;base64"

            image_bytes = b64decode(image_base64)
            image = Image.open(io.BytesIO(image_bytes))

            if image.mode != "RGB":
                image = image.convert("RGB")

            # Resize image to limit dimensions for frontend preview and sampling
            width, height = image.size
            if max(width, height) > max_dim:
                ratio = min(max_dim / width, max_dim / height)
                new_w = int(width * ratio)
                new_h = int(height * ratio)
                image = image.resize((new_w, new_h), Image.LANCZOS)
                width, height = image.size

            image_array = np.array(image)

            # Determine sampling step to keep pixel count <= max_pixels
            total = width * height
            pixels = []
            if max_pixels and max_pixels > 0:
                if total <= max_pixels:
                    step = 1
                else:
                    # sample roughly uniformly using a square step
                    step = int(max(1, (total / max_pixels) ** 0.5))

                for y in range(0, height, step):
                    for x in range(0, width, step):
                        rgb = image_array[y, x]
                        hex_color = self._rgb_to_hex(tuple(rgb))
                        pixels.append({"x": int(x), "y": int(y), "color": hex_color})
            else:
                step = 0

            # Re-encode resized image to data URI (jpeg to reduce size)
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=85)
            buffer.seek(0)
            resized_b64 = buffer.getvalue()
            from base64 import b64encode

            data_uri = f"{header};base64,{b64encode(resized_b64).decode('utf-8')}"

            logger.info(f"Generated pixel map: {len(pixels)} sampled pixels from {width}x{height} (step={step})")
            return data_uri, pixels, width, height

        except Exception as e:
            logger.error(f"Failed to get pixel map: {e}")
            raise
    
    
    def extract_from_image(self, image: Image.Image) -> List[str]:
        """
        Extract dominant colors from PIL Image.
        
        Args:
            image: PIL Image object
            
        Returns:
            List of dominant colors as hex strings, sorted by brightness
        """
        try:
            # Convert to RGB if needed
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            # Resize for faster processing
            image = image.resize((self.resize_size, self.resize_size))
            
            # Convert to array and reshape
            image_array = np.array(image)
            pixels = image_array.reshape(-1, 3)
            
            # Remove grayscale/near-grayscale pixels (low saturation)
            pixels = self._filter_grayscale(pixels)
            
            # Cluster colors
            kmeans = KMeans(n_clusters=min(self.num_colors, len(pixels)), 
                           n_init=10, random_state=42)
            kmeans.fit(pixels)
            
            # Get cluster centers and sort by brightness
            colors = kmeans.cluster_centers_.astype(int)
            colors = self._sort_by_luminance(colors)
            
            # Convert to hex
            hex_colors = [self._rgb_to_hex(rgb) for rgb in colors]
            
            logger.info(f"Extracted {len(hex_colors)} colors from image")
            return hex_colors
        
        except Exception as e:
            logger.error(f"Color extraction failed: {e}")
            raise
    
    @staticmethod
    def _filter_grayscale(pixels: np.ndarray, sat_threshold: float = 0.15) -> np.ndarray:
        """
        Remove grayscale pixels (low saturation) to focus on colored regions.
        
        Args:
            pixels: Array of RGB pixels
            sat_threshold: Minimum saturation to keep (0-1)
            
        Returns:
            Filtered pixel array
        """
        # Convert to HSV and check saturation
        hsv_pixels = []
        for rgb in pixels:
            h, s, v = rgb_to_hsv(rgb[0]/255, rgb[1]/255, rgb[2]/255)
            hsv_pixels.append((h, s, v))
        
        hsv_pixels = np.array(hsv_pixels)
        mask = hsv_pixels[:, 1] > sat_threshold  # saturation channel
        
        return pixels[mask] if mask.sum() > 0 else pixels
    
    @staticmethod
    def _sort_by_luminance(colors: np.ndarray) -> np.ndarray:
        """
        Sort colors by perceived luminance (brightness).
        
        Args:
            colors: Array of RGB colors
            
        Returns:
            Sorted array
        """
        # Perceived luminance formula
        luminance = 0.299 * colors[:, 0] + 0.587 * colors[:, 1] + 0.114 * colors[:, 2]
        indices = np.argsort(luminance)[::-1]  # Descending order
        return colors[indices]
    
    @staticmethod
    def _rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
        """Convert RGB tuple to hex string."""
        return f"#{int(rgb[0]):02x}{int(rgb[1]):02x}{int(rgb[2]):02x}"
    
    @staticmethod
    def _hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
        """Convert hex string to RGB tuple."""
        hex_str = hex_str.lstrip("#")
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
    
    @staticmethod
    def calculate_contrast(hex1: str, hex2: str) -> float:
        """
        Calculate WCAG contrast ratio between two colors.
        
        Args:
            hex1: First color in hex format
            hex2: Second color in hex format
            
        Returns:
            Contrast ratio (1-21)
        """
        def relative_luminance(rgb):
            """Calculate relative luminance per WCAG formula."""
            r, g, b = [x / 255 for x in rgb]
            r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
            g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
            b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
            return 0.2126 * r + 0.7152 * g + 0.0722 * b
        
        rgb1 = ColorExtractor._hex_to_rgb(hex1)
        rgb2 = ColorExtractor._hex_to_rgb(hex2)
        
        l1 = relative_luminance(rgb1)
        l2 = relative_luminance(rgb2)
        
        lighter = max(l1, l2)
        darker = min(l1, l2)
        
        return (lighter + 0.05) / (darker + 0.05)
