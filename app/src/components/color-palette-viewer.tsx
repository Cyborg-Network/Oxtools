"use client";

import { Button, Card, CardContent } from "@ansospace/ui";
import { Check, Copy } from "lucide-react";
import { useEffect, useRef, useState } from "react";

interface PixelData {
	x: number;
	y: number;
	color: string;
}

interface Palette {
	palette?: Record<string, string>;
	roles?: Record<string, string>;
	colorTheory?: string;
	cssVariables?: string;
	tailwindConfig?: string;
	wcagCompliance?: string;
	extractedColors?: string[];
	image?: string;
	pixels?: PixelData[];
	imageWidth?: number;
	imageHeight?: number;
}

interface ColorPaletteViewerProps {
	data: Palette;
	enableHover?: boolean;
}

// Helper function to convert hex to RGB
const hexToRgb = (hex: string): { r: number; g: number; b: number } | null => {
	const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
	return result
		? {
				r: parseInt(result[1], 16),
				g: parseInt(result[2], 16),
				b: parseInt(result[3], 16),
			}
		: null;
};

// Helper function to calculate color distance (Delta E approximation)
const getColorDistance = (color1: string, color2: string): number => {
	const rgb1 = hexToRgb(color1);
	const rgb2 = hexToRgb(color2);
	if (!rgb1 || !rgb2) return Infinity;

	const dr = rgb1.r - rgb2.r;
	const dg = rgb1.g - rgb2.g;
	const db = rgb1.b - rgb2.b;

	return Math.sqrt(dr * dr + dg * dg + db * db);
};

// Find the closest color in palette to the hovered pixel color
const findClosestColor = (
	pixelColor: string,
	paletteColors: string[] | undefined
): string | null => {
	if (!paletteColors || paletteColors.length === 0) return null;

	let closestColor = paletteColors[0];
	let minDistance = getColorDistance(pixelColor, closestColor);

	for (const color of paletteColors) {
		const distance = getColorDistance(pixelColor, color);
		if (distance < minDistance) {
			minDistance = distance;
			closestColor = color;
		}
	}

	// Only return if color is close enough (threshold of 50 in Delta E)
	return minDistance <= 50 ? closestColor : null;
};

export function ColorPaletteViewer({ data, enableHover = true }: ColorPaletteViewerProps) {
	const [copiedColor, setCopiedColor] = useState<string | null>(null);
	const [hoveredPixel, setHoveredPixel] = useState<{ x: number; y: number; color: string } | null>(
		null
	);
	const [cursorPos, setCursorPos] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
	const [highlightBox, setHighlightBox] = useState<{ x: number; y: number; size: number } | null>(
		null
	);
	const [canvasReady, setCanvasReady] = useState(false);
	const [highlightedPaletteColor, setHighlightedPaletteColor] = useState<string | null>(null);
	const canvasRef = useRef<HTMLCanvasElement>(null);
	const wrapperRef = useRef<HTMLDivElement>(null);
	const containerRef = useRef<HTMLDivElement>(null);
	const rafRef = useRef<number | null>(null);

	const copyToClipboard = (text: string, id: string) => {
		navigator.clipboard.writeText(text);
		setCopiedColor(id);
		setTimeout(() => setCopiedColor(null), 2000);
	};

	const copyAllColors = () => {
		if (!data.extractedColors) return;
		const allColors = data.extractedColors.join("\n");
		navigator.clipboard.writeText(allColors);
		setCopiedColor("all");
		setTimeout(() => setCopiedColor(null), 2000);
	};

	useEffect(() => {
		if (!data.image || !canvasRef.current) {
			setCanvasReady(false);
			return;
		}

		const canvas = canvasRef.current;
		const context = canvas.getContext("2d");
		if (!context) return;

		const image = new window.Image();
		image.onload = () => {
			// Limit canvas size to prevent memory issues (max 1000x1000 for interactive preview)
			const MAX_CANVAS_DIMENSION = 1000;
			let width = image.naturalWidth;
			let height = image.naturalHeight;

			if (width > MAX_CANVAS_DIMENSION || height > MAX_CANVAS_DIMENSION) {
				const ratio = Math.min(MAX_CANVAS_DIMENSION / width, MAX_CANVAS_DIMENSION / height);
				width = Math.floor(width * ratio);
				height = Math.floor(height * ratio);
			}

			canvas.width = width;
			canvas.height = height;
			context.clearRect(0, 0, canvas.width, canvas.height);
			context.drawImage(image, 0, 0, width, height);
			setCanvasReady(true);
		};
		image.onerror = () => {
			console.error("[ERROR] Failed to load image from data URI");
		};
		image.src = data.image;

		return () => {
			// Cleanup RAF if any
			if (rafRef.current) {
				window.cancelAnimationFrame(rafRef.current);
				rafRef.current = null;
			}
		};
	}, [data.image]);

	const handleCanvasMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
		if (!enableHover) return;

		const canvas = canvasRef.current;
		if (!canvas || !canvas.width || !canvas.height) return;

		const rect = canvas.getBoundingClientRect();
		const displayX = e.clientX - rect.left;
		const displayY = e.clientY - rect.top;

		const scaleX = canvas.width / rect.width;
		const scaleY = canvas.height / rect.height;

		const x = Math.max(0, Math.min(canvas.width - 1, Math.floor(displayX * scaleX)));
		const y = Math.max(0, Math.min(canvas.height - 1, Math.floor(displayY * scaleY)));

		const context = canvas.getContext("2d");
		if (!context) return;

		// Throttle using requestAnimationFrame to prevent spamming getImageData
		if (rafRef.current) return;

		rafRef.current = window.requestAnimationFrame(() => {
			try {
				const pixel = context.getImageData(x, y, 1, 1).data;
				const color = `#${[pixel[0], pixel[1], pixel[2]]
					.map((value) => value.toString(16).padStart(2, "0"))
					.join("")}`;

				setHoveredPixel({ x, y, color });
				setCursorPos({
					x: e.clientX - (wrapperRef.current?.getBoundingClientRect().left || 0),
					y: e.clientY - (wrapperRef.current?.getBoundingClientRect().top || 0),
				});

				const pixelWidth = Math.max(6, Math.ceil(rect.width / canvas.width));
				const pixelHeight = Math.max(6, Math.ceil(rect.height / canvas.height));
				setHighlightBox({
					x: displayX,
					y: displayY,
					size: Math.max(pixelWidth, pixelHeight),
				});

				// Find and highlight the matching color from the palette
				const matchedColor = findClosestColor(color, data.extractedColors);
				setHighlightedPaletteColor(matchedColor);
			} finally {
				if (rafRef.current) {
					window.cancelAnimationFrame(rafRef.current);
					rafRef.current = null;
				}
			}
		});
	};

	const handleCanvasLeave = () => {
		setHoveredPixel(null);
		setHighlightBox(null);
		setHighlightedPaletteColor(null);
	};

	return (
		<div className="space-y-6">
			{/* Image Display with Hover Interaction */}
			{data.image && (
				<Card className="border-primary/20 bg-gradient-to-br from-primary/[0.05] to-primary/[0.02] overflow-hidden">
					<CardContent className="p-6">
						<div className="flex items-center justify-between gap-3 mb-4">
							<h3 className="text-lg font-semibold">Uploaded Image</h3>
							{enableHover ? (
								canvasReady && (
									<span className="rounded-full bg-muted px-2 py-1 text-[11px] text-muted-foreground">
										Hover to inspect pixels
									</span>
								)
							) : (
								<span className="rounded-full bg-destructive/10 px-2 py-1 text-[11px] text-destructive/70">
									Click "Run" to enable interaction
								</span>
							)}
						</div>
						<div ref={wrapperRef} className="relative w-full max-w-2xl mx-auto">
							<div
								ref={containerRef}
								className="relative w-full overflow-hidden rounded-lg border border-border/50 shadow-lg"
							>
								<canvas
									ref={canvasRef}
									className={`block w-full h-auto ${enableHover ? "cursor-crosshair" : "cursor-not-allowed opacity-75"}`}
									onMouseMove={handleCanvasMove}
									onMouseLeave={handleCanvasLeave}
								/>

								{highlightBox && hoveredPixel && (
									<div
										className="pointer-events-none absolute z-20 rounded border border-white/80 bg-white/20 shadow-[0_0_0_1px_rgba(0,0,0,0.25)]"
										style={{
											left: `${highlightBox.x}px`,
											top: `${highlightBox.y}px`,
											width: `${highlightBox.size}px`,
											height: `${highlightBox.size}px`,
											transform: "translate(-50%, -50%)",
											boxShadow: `0 0 0 1px ${hoveredPixel.color}, 0 0 0 2px rgba(0,0,0,0.35)`,
										}}
									/>
								)}

								{/* Pixel Color Tooltip */}
								{hoveredPixel && (
									<div
										className="absolute z-30 rounded bg-black/90 px-3 py-2 text-sm font-mono text-white shadow-lg pointer-events-none"
										style={{
											left: `${cursorPos.x + 10}px`,
											top: `${cursorPos.y + 10}px`,
											whiteSpace: "nowrap",
										}}
									>
										<div className="flex items-center gap-2">
											<div
												className="w-6 h-6 rounded border border-white/50"
												style={{ backgroundColor: hoveredPixel.color }}
											/>
											<span>{hoveredPixel.color}</span>
											<button
												type="button"
												onClick={() => copyToClipboard(hoveredPixel.color, hoveredPixel.color)}
												className="ml-2 p-1 hover:bg-white/20 rounded transition-colors"
												title="Copy color"
											>
												<Copy className="h-3 w-3" />
											</button>
										</div>
										<div className="text-xs text-gray-400 mt-1">
											({hoveredPixel.x}, {hoveredPixel.y})
										</div>
										{highlightedPaletteColor && (
											<div className="text-xs text-green-400 mt-2 border-t border-white/20 pt-2">
												Match: {highlightedPaletteColor}
											</div>
										)}
									</div>
								)}
							</div>
						</div>
						{data.imageWidth && data.imageHeight && (
							<p className="text-xs text-muted-foreground mt-3">
								Resolution: {data.imageWidth} × {data.imageHeight}px
							</p>
						)}
						{!canvasReady && (
							<p className="mt-3 text-xs text-muted-foreground">Loading image preview…</p>
						)}
					</CardContent>
				</Card>
			)}
			{data.extractedColors && data.extractedColors.length > 0 && (
				<Card className="border-primary/20 bg-gradient-to-br from-primary/[0.05] to-primary/[0.02] overflow-hidden">
					<CardContent className="p-6">
						<div className="flex items-center justify-between mb-6">
							<h3 className="text-lg font-semibold">Top Colors from Image</h3>
							<Button
								size="sm"
								variant={copiedColor === "all" ? "default" : "ghost"}
								onClick={copyAllColors}
								className="gap-2"
							>
								{copiedColor === "all" ? (
									<>
										<Check className="h-4 w-4" />
										Copied!
									</>
								) : (
									<>
										<Copy className="h-4 w-4" />
										Copy All
									</>
								)}
							</Button>
						</div>
						<div className="flex flex-wrap gap-4">
							{data.extractedColors.map((color) => {
								const isHighlighted = highlightedPaletteColor === color;
								return (
									<button
										key={color}
										type="button"
										className={`group cursor-pointer transition-all duration-200 ${
											isHighlighted ? "scale-105" : ""
										}`}
										onClick={() => copyToClipboard(color, color)}
										title="Click to copy"
									>
										<div
											className={`w-24 h-24 rounded-lg mb-3 border-2 shadow-md transition-all hover:shadow-lg relative overflow-hidden ${
												isHighlighted
													? "border-green-400/80 shadow-lg shadow-green-400/50"
													: "border-border/50"
											}`}
											style={{ backgroundColor: color }}
										>
											{/* Overlay on hover */}
											<div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors flex items-center justify-center">
												{copiedColor === color && (
													<Check className="h-6 w-6 text-white drop-shadow-lg" />
												)}
											</div>
										</div>
										<div className="space-y-1.5">
											<code className="text-xs bg-muted px-2 py-1 rounded font-mono block text-center">
												{color}
											</code>
											{isHighlighted && (
												<div className="text-xs text-green-400 font-semibold text-center">
													In use
												</div>
											)}
										</div>
									</button>
								);
							})}
						</div>
					</CardContent>
				</Card>
			)}
		</div>
	);
}
