<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import {
  Scene,
  PerspectiveCamera,
  WebGLRenderer,
  SphereGeometry,
  MeshStandardMaterial,
  MeshBasicMaterial,
  Mesh,
  AmbientLight,
  DirectionalLight,
  CanvasTexture,
  AdditiveBlending,
  BackSide,
  Color,
  ShaderMaterial,
} from 'three'

/**
 * MarsGlobe — Procedural Three.js Mars globe with atmospheric glow
 *
 * Renders a realistic Mars sphere using a procedurally generated
 * canvas texture (simplex-like noise via nested sin/cos). Includes
 * Fresnel-based atmospheric glow, rim lighting, and gentle floating
 * animation.
 *
 * Non-interactive, positioned bottom-right of the hero section.
 * Falls back to a CSS radial-gradient circle if WebGL is unavailable.
 */

const canvasRef = ref(null)
const webglSupported = ref(true)

let renderer = null
let scene = null
let camera = null
let marsGroup = null
let animationId = null
let resizeTimer = null

/**
 * Procedural Mars terrain noise — layered sine/cosine to approximate
 * simplex noise without external dependencies. Multiple octaves for
 * continent-scale, mid-frequency, high-frequency, and ultra-fine detail.
 */
function marsNoise(x, y) {
  // Base continent-scale variation
  let n = Math.sin(x * 3.7 + y * 2.1) * 0.3
  n += Math.cos(x * 5.3 - y * 4.7) * 0.25
  // Mid-frequency terrain
  n += Math.sin(x * 11.3 + y * 8.9) * 0.15
  n += Math.cos(x * 14.1 - y * 12.7) * 0.1
  // High-frequency detail
  n += Math.sin(x * 23.7 + y * 19.3) * 0.08
  n += Math.cos(x * 31.1 - y * 27.9) * 0.05
  // Crater-like depressions
  n += Math.sin(x * 7.1) * Math.cos(y * 6.3) * 0.12
  // Ultra-fine grain (extra octaves)
  n += Math.sin(x * 47.3 + y * 41.7) * 0.03
  n += Math.cos(x * 63.1 - y * 58.9) * 0.02
  n += Math.sin(x * 89.7 + y * 73.3) * 0.015
  return n
}

/**
 * Procedural crater features — creates circular depressions at
 * fixed pseudo-random locations on the sphere.
 */
function craterNoise(x, y) {
  // Crater centers in normalized spherical coordinates
  const craters = [
    { cx: 2.1, cy: 1.4, r: 0.35, depth: 0.28 },
    { cx: 4.5, cy: 1.8, r: 0.25, depth: 0.22 },
    { cx: 1.0, cy: 2.3, r: 0.20, depth: 0.18 },
    { cx: 3.8, cy: 0.9, r: 0.30, depth: 0.25 },
    { cx: 5.5, cy: 2.0, r: 0.18, depth: 0.15 },
    { cx: 0.5, cy: 1.1, r: 0.22, depth: 0.20 },
    { cx: 2.8, cy: 2.6, r: 0.15, depth: 0.12 },
    { cx: 4.2, cy: 0.5, r: 0.28, depth: 0.24 },
    { cx: 5.8, cy: 1.2, r: 0.12, depth: 0.10 },
    { cx: 1.5, cy: 2.8, r: 0.16, depth: 0.13 },
    { cx: 3.2, cy: 1.6, r: 0.10, depth: 0.08 },
    { cx: 0.8, cy: 0.6, r: 0.14, depth: 0.11 },
  ]

  let result = 0
  for (const c of craters) {
    const dx = x - c.cx
    const dy = y - c.cy
    const dist = Math.sqrt(dx * dx + dy * dy)
    if (dist < c.r) {
      // Smooth circular depression with raised rim
      const t = dist / c.r
      const bowl = -c.depth * (1.0 - t * t)
      // Slight rim uplift at edge
      const rim = c.depth * 0.3 * Math.exp(-((t - 0.85) * (t - 0.85)) / 0.02)
      result += bowl + rim
    }
  }
  return result
}

/**
 * Long linear canyon feature (Valles Marineris–like) across the
 * equatorial region.
 */
function canyonNoise(x, y) {
  // Canyon runs along the equator (y ≈ π/2) with sinusoidal wander
  const equator = Math.PI * 0.52
  const canyonY = equator + Math.sin(x * 1.2) * 0.08 + Math.sin(x * 2.8) * 0.04
  const distFromCanyon = Math.abs(y - canyonY)
  const canyonWidth = 0.06 + Math.sin(x * 3.5) * 0.015

  if (distFromCanyon < canyonWidth && x > 1.2 && x < 4.8) {
    // Smooth canyon profile — deepest at center
    const t = distFromCanyon / canyonWidth
    const depth = -0.35 * (1.0 - t * t) * (1.0 - t * t)
    // Taper at canyon ends
    const endTaper = Math.min(
      1.0,
      (x - 1.2) / 0.4,
      (4.8 - x) / 0.4
    )
    return depth * endTaper
  }
  return 0
}

/**
 * Generate a 1024×1024 procedural Mars surface texture on a canvas.
 * Blends between Mars palette colors based on noise values with
 * crater features, canyons, and impact basins.
 */
function generateMarsTexture() {
  const size = 1024
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')

  // Enhanced Mars color palette
  const rust = { r: 178, g: 110, b: 82 }       // #b26e52 — dominant rust
  const dark = { r: 107, g: 58, b: 42 }         // #6b3a2a — dark lowlands
  const ochre = { r: 212, g: 137, b: 63 }       // #d4893f — bright highlands
  const shadow = { r: 61, g: 31, b: 20 }        // #3d1f14 — deep shadow / craters
  const highlight = { r: 196, g: 148, b: 108 }  // #c4946c — sunlit ridges
  const dustyPink = { r: 205, g: 145, b: 130 }  // #cd9182 — dusty pink highlight

  const imageData = ctx.createImageData(size, size)
  const data = imageData.data

  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      // Normalize to 0..2π for spherical mapping
      const nx = (x / size) * Math.PI * 2
      const ny = (y / size) * Math.PI

      let n = marsNoise(nx, ny)
      n += craterNoise(nx, ny)
      n += canyonNoise(nx, ny)

      // Map noise to color zones with more dramatic contrast
      let r, g, b
      if (n < -0.30) {
        // Deep craters / canyon floors — very dark
        const t = Math.max(0, (n + 0.55) / 0.25)
        r = shadow.r + (dark.r - shadow.r) * t
        g = shadow.g + (dark.g - shadow.g) * t
        b = shadow.b + (dark.b - shadow.b) * t
      } else if (n < -0.08) {
        // Dark lowlands
        const t = (n + 0.30) / 0.22
        r = dark.r + (rust.r - dark.r) * t
        g = dark.g + (rust.g - dark.g) * t
        b = dark.b + (rust.b - dark.b) * t
      } else if (n < 0.15) {
        // Standard rust terrain
        const t = (n + 0.08) / 0.23
        r = rust.r + (ochre.r - rust.r) * t
        g = rust.g + (ochre.g - rust.g) * t
        b = rust.b + (ochre.b - rust.b) * t
      } else if (n < 0.30) {
        // Bright highlands — ochre to dusty pink
        const t = (n - 0.15) / 0.15
        r = ochre.r + (dustyPink.r - ochre.r) * t
        g = ochre.g + (dustyPink.g - ochre.g) * t
        b = ochre.b + (dustyPink.b - ochre.b) * t
      } else {
        // Sunlit ridges — dusty pink to highlight
        const t = Math.min(1, (n - 0.30) / 0.25)
        r = dustyPink.r + (highlight.r - dustyPink.r) * t
        g = dustyPink.g + (highlight.g - dustyPink.g) * t
        b = dustyPink.b + (highlight.b - dustyPink.b) * t
      }

      // Procedural dark spots for impact basins
      const basinNoise = Math.sin(nx * 2.3 + 0.7) * Math.cos(ny * 3.1 + 1.2)
        * Math.sin(nx * 1.1 - ny * 0.8) * 0.5
      if (basinNoise > 0.35) {
        const basinStrength = (basinNoise - 0.35) / 0.15
        const blend = Math.min(1, basinStrength * 0.4)
        r = r * (1 - blend) + shadow.r * blend
        g = g * (1 - blend) + shadow.g * blend
        b = b * (1 - blend) + shadow.b * blend
      }

      // Add micro-variation for grain
      const grain = (Math.random() - 0.5) * 8
      const idx = (y * size + x) * 4
      data[idx] = Math.max(0, Math.min(255, r + grain))
      data[idx + 1] = Math.max(0, Math.min(255, g + grain))
      data[idx + 2] = Math.max(0, Math.min(255, b + grain))
      data[idx + 3] = 255
    }
  }

  ctx.putImageData(imageData, 0, 0)

  // Polar caps — smoother gradient with whiter tones
  const gradient = ctx.createLinearGradient(0, 0, 0, size)
  gradient.addColorStop(0, 'rgba(235, 220, 210, 0.35)')
  gradient.addColorStop(0.04, 'rgba(230, 215, 200, 0.22)')
  gradient.addColorStop(0.10, 'rgba(220, 200, 185, 0.08)')
  gradient.addColorStop(0.15, 'rgba(220, 200, 185, 0)')
  gradient.addColorStop(0.85, 'rgba(220, 200, 185, 0)')
  gradient.addColorStop(0.90, 'rgba(220, 200, 185, 0.06)')
  gradient.addColorStop(0.96, 'rgba(225, 210, 195, 0.18)')
  gradient.addColorStop(1, 'rgba(230, 215, 200, 0.28)')
  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, size, size)

  return canvas
}

/**
 * Check for WebGL support.
 */
function isWebGLAvailable() {
  try {
    const testCanvas = document.createElement('canvas')
    return !!(
      window.WebGLRenderingContext &&
      (testCanvas.getContext('webgl') || testCanvas.getContext('experimental-webgl'))
    )
  } catch {
    return false
  }
}

/**
 * Fresnel atmosphere vertex shader — computes view-normal dot product
 * and passes it to the fragment shader for edge brightening.
 */
const fresnelVertexShader = `
  varying float vFresnel;
  void main() {
    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    vec3 viewDir = normalize(-mvPosition.xyz);
    vec3 worldNormal = normalize(normalMatrix * normal);
    vFresnel = 1.0 - dot(viewDir, worldNormal);
    gl_Position = projectionMatrix * mvPosition;
  }
`

/**
 * Fresnel atmosphere fragment shader — edge glow using pow(fresnel, 3.0)
 * for a natural atmospheric falloff.
 */
const fresnelFragmentShader = `
  uniform vec3 glowColor;
  uniform float opacity;
  varying float vFresnel;
  void main() {
    float intensity = pow(vFresnel, 3.0);
    gl_FragColor = vec4(glowColor, intensity * opacity);
  }
`

/**
 * Initialize the Three.js scene, camera, lights, Mars sphere, and glow.
 */
function initScene() {
  const container = canvasRef.value
  if (!container) return

  const width = container.clientWidth
  const height = container.clientHeight

  // Renderer
  renderer = new WebGLRenderer({ antialias: true, alpha: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.setSize(width, height)
  renderer.setClearColor(0x000000, 0)
  container.appendChild(renderer.domElement)

  // Scene
  scene = new Scene()

  // Camera
  camera = new PerspectiveCamera(45, width / height, 0.1, 100)
  camera.position.z = 2.5

  // Lighting — warmed up main light
  const ambientLight = new AmbientLight(0xffffff, 0.3)
  scene.add(ambientLight)

  const dirLight = new DirectionalLight(0xfff2e0, 1.0)
  dirLight.position.set(-3, 2, 1)
  scene.add(dirLight)

  // Rim light from behind-right for depth
  const rimLight = new DirectionalLight(0xff9060, 0.3)
  rimLight.position.set(2, -1, -2)
  scene.add(rimLight)

  // Mars globe
  const marsTexture = new CanvasTexture(generateMarsTexture())
  const marsGeometry = new SphereGeometry(1, 64, 64)
  const marsMaterial = new MeshStandardMaterial({
    map: marsTexture,
    roughness: 0.85,
    metalness: 0.05,
  })
  const mars = new Mesh(marsGeometry, marsMaterial)

  // Fresnel atmospheric glow — brighter at edges, transparent at center
  const glowGeometry = new SphereGeometry(1.08, 64, 64)
  const glowMaterial = new ShaderMaterial({
    uniforms: {
      glowColor: { value: new Color('#ff8c52') },
      opacity: { value: 0.15 },
    },
    vertexShader: fresnelVertexShader,
    fragmentShader: fresnelFragmentShader,
    transparent: true,
    blending: AdditiveBlending,
    side: BackSide,
    depthWrite: false,
  })
  const glow = new Mesh(glowGeometry, glowMaterial)

  // Outer haze for soft edge
  const hazeGeometry = new SphereGeometry(1.18, 32, 32)
  const hazeMaterial = new MeshBasicMaterial({
    color: new Color('#ff6b35'),
    transparent: true,
    opacity: 0.035,
    blending: AdditiveBlending,
    side: BackSide,
    depthWrite: false,
  })
  const haze = new Mesh(hazeGeometry, hazeMaterial)

  scene.add(mars)
  scene.add(glow)
  scene.add(haze)

  // Store references for rotation and animation
  marsGroup = { mars, glow, haze }
}

/**
 * Animation loop — slow rotation on Y and slight X wobble,
 * plus subtle atmosphere opacity pulsing.
 */
function animate() {
  if (!renderer || !scene || !camera || !marsGroup) return

  marsGroup.mars.rotation.y += 0.001
  marsGroup.mars.rotation.x += 0.0003
  marsGroup.glow.rotation.y += 0.0008
  marsGroup.haze.rotation.y += 0.0005

  // Subtle atmosphere opacity pulsing
  marsGroup.glow.material.uniforms.opacity.value =
    0.08 + Math.sin(Date.now() * 0.001) * 0.02

  renderer.render(scene, camera)
  animationId = requestAnimationFrame(animate)
}

/**
 * Debounced resize handler.
 */
function handleResize() {
  clearTimeout(resizeTimer)
  resizeTimer = setTimeout(() => {
    if (!canvasRef.value || !renderer || !camera) return
    const width = canvasRef.value.clientWidth
    const height = canvasRef.value.clientHeight
    camera.aspect = width / height
    camera.updateProjectionMatrix()
    renderer.setSize(width, height)
  }, 150)
}

/**
 * Dispose all Three.js resources.
 */
function cleanup() {
  if (animationId) {
    cancelAnimationFrame(animationId)
    animationId = null
  }

  clearTimeout(resizeTimer)
  window.removeEventListener('resize', handleResize)

  if (marsGroup) {
    marsGroup.mars.geometry.dispose()
    marsGroup.mars.material.map?.dispose()
    marsGroup.mars.material.dispose()
    marsGroup.glow.geometry.dispose()
    marsGroup.glow.material.dispose()
    marsGroup.haze.geometry.dispose()
    marsGroup.haze.material.dispose()
  }

  if (renderer) {
    renderer.dispose()
    if (canvasRef.value && renderer.domElement.parentNode === canvasRef.value) {
      canvasRef.value.removeChild(renderer.domElement)
    }
    renderer = null
  }

  scene = null
  camera = null
  marsGroup = null
}

onMounted(() => {
  if (!isWebGLAvailable()) {
    webglSupported.value = false
    return
  }

  initScene()
  animate()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(cleanup)
</script>

<template>
  <div class="mars-globe-wrapper" aria-hidden="true">
    <!-- Three.js canvas container -->
    <div
      v-if="webglSupported"
      ref="canvasRef"
      class="mars-canvas"
    />

    <!-- CSS fallback when WebGL unavailable -->
    <div
      v-else
      class="mars-fallback"
    />
  </div>
</template>

<style scoped>
.mars-globe-wrapper {
  position: fixed;
  right: -5%;
  top: 15%;
  width: 45vw;
  height: 45vw;
  max-width: 600px;
  max-height: 600px;
  z-index: 1;
  pointer-events: none;
  opacity: 0.7;
  animation: globe-float 8s ease-in-out infinite;
}

.mars-canvas {
  width: 100%;
  height: 100%;
}

/* WebGL fallback — pure CSS Mars-like sphere */
.mars-fallback {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: radial-gradient(
    circle at 35% 35%,
    #d4893f 0%,
    #b26e52 30%,
    #924737 55%,
    #6b3a2a 75%,
    #3d1f14 100%
  );
  box-shadow:
    0 0 60px 15px rgba(255, 107, 53, 0.08),
    inset -20px -15px 40px rgba(61, 31, 20, 0.6),
    inset 15px 10px 30px rgba(212, 137, 63, 0.2);
}

/* Gentle floating animation */
@keyframes globe-float {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-20px);
  }
}

/* Accessibility — disable motion */
@media (prefers-reduced-motion: reduce) {
  .mars-globe-wrapper {
    animation: none !important;
  }
}

/* Responsive: scale down on tablets */
@media (max-width: 1024px) {
  .mars-globe-wrapper {
    width: 40vw;
    height: 40vw;
    right: -8%;
    top: 20%;
  }
}

/* Mobile: smaller, reposition */
@media (max-width: 640px) {
  .mars-globe-wrapper {
    width: 55vw;
    height: 55vw;
    right: -12%;
    top: 10%;
    opacity: 0.5;
  }
}
</style>
