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
} from 'three'

/**
 * MarsGlobe — Procedural Three.js Mars globe with atmospheric glow
 *
 * Renders a realistic Mars sphere using a procedurally generated
 * canvas texture (simplex-like noise via nested sin/cos). Includes
 * an outer atmospheric glow shell and gentle floating animation.
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
 * simplex noise without external dependencies.
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
  return n
}

/**
 * Generate a 512x512 procedural Mars surface texture on a canvas.
 * Blends between Mars palette colors based on noise values.
 */
function generateMarsTexture() {
  const size = 512
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')

  // Mars color palette
  const rust = { r: 178, g: 110, b: 82 }       // #b26e52 — dominant rust
  const dark = { r: 107, g: 58, b: 42 }         // #6b3a2a — dark lowlands
  const ochre = { r: 212, g: 137, b: 63 }       // #d4893f — bright highlands
  const shadow = { r: 61, g: 31, b: 20 }        // #3d1f14 — deep shadow / craters
  const highlight = { r: 196, g: 148, b: 108 }  // #c4946c — sunlit ridges

  const imageData = ctx.createImageData(size, size)
  const data = imageData.data

  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      // Normalize to 0..2π for spherical mapping
      const nx = (x / size) * Math.PI * 2
      const ny = (y / size) * Math.PI

      const n = marsNoise(nx, ny)

      // Map noise to color zones
      let r, g, b
      if (n < -0.25) {
        // Deep craters / shadow
        const t = (n + 0.5) / 0.25
        r = shadow.r + (dark.r - shadow.r) * Math.max(0, t)
        g = shadow.g + (dark.g - shadow.g) * Math.max(0, t)
        b = shadow.b + (dark.b - shadow.b) * Math.max(0, t)
      } else if (n < 0.0) {
        // Dark lowlands
        const t = (n + 0.25) / 0.25
        r = dark.r + (rust.r - dark.r) * t
        g = dark.g + (rust.g - dark.g) * t
        b = dark.b + (rust.b - dark.b) * t
      } else if (n < 0.2) {
        // Standard rust terrain
        const t = n / 0.2
        r = rust.r + (ochre.r - rust.r) * t
        g = rust.g + (ochre.g - rust.g) * t
        b = rust.b + (ochre.b - rust.b) * t
      } else {
        // Bright highlands
        const t = Math.min(1, (n - 0.2) / 0.3)
        r = ochre.r + (highlight.r - ochre.r) * t
        g = ochre.g + (highlight.g - ochre.g) * t
        b = ochre.b + (highlight.b - ochre.b) * t
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

  // Add a few procedural "polar caps" — lighter blending at top/bottom
  const gradient = ctx.createLinearGradient(0, 0, 0, size)
  gradient.addColorStop(0, 'rgba(210, 180, 155, 0.25)')
  gradient.addColorStop(0.12, 'rgba(210, 180, 155, 0)')
  gradient.addColorStop(0.88, 'rgba(210, 180, 155, 0)')
  gradient.addColorStop(1, 'rgba(200, 170, 145, 0.18)')
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

  // Lighting
  const ambientLight = new AmbientLight(0xffffff, 0.3)
  scene.add(ambientLight)

  const dirLight = new DirectionalLight(0xfff4e6, 1.0)
  dirLight.position.set(-3, 2, 1)
  scene.add(dirLight)

  // Mars globe
  const marsTexture = new CanvasTexture(generateMarsTexture())
  const marsGeometry = new SphereGeometry(1, 64, 64)
  const marsMaterial = new MeshStandardMaterial({
    map: marsTexture,
    roughness: 0.85,
    metalness: 0.05,
  })
  const mars = new Mesh(marsGeometry, marsMaterial)

  // Atmospheric glow — slightly larger sphere, additive blending, BackSide
  const glowGeometry = new SphereGeometry(1.08, 64, 64)
  const glowMaterial = new MeshBasicMaterial({
    color: new Color('#ff6b35'),
    transparent: true,
    opacity: 0.08,
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

  // Store references for rotation
  marsGroup = { mars, glow, haze }
}

/**
 * Animation loop — slow rotation on Y and slight X wobble.
 */
function animate() {
  if (!renderer || !scene || !camera || !marsGroup) return

  marsGroup.mars.rotation.y += 0.001
  marsGroup.mars.rotation.x += 0.0003
  marsGroup.glow.rotation.y += 0.0008
  marsGroup.haze.rotation.y += 0.0005

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
