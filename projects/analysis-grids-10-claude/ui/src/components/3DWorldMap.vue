<script setup>
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  worldState: {
    type: Object,
    default: null,
  },
  agentIds: {
    type: Array,
    default: () => [],
  },
  followAgent: {
    type: String,
    default: null,
  },
})

// Check if data is loaded (similar approach to WorldMap.vue)
const hasData = computed(() => {
  return props.worldState && props.worldState.agents;
});

// 3D Context and State Management
const canvasRef = ref(null)
let gl = null
let animationFrameId = null

// Shaders
const vsSource = `#version 300 es
in vec4 aVertexPosition;
in vec3 aVertexNormal;

uniform mat4 uModelViewMatrix;
uniform mat4 uProjectionMatrix;
uniform mat3 uNormalMatrix;

out vec3 fragNormal;
out vec3 fragPosition;
out vec3 modelPos;

void main() {
  modelPos = aVertexPosition.xyz; // Store for fragment shader to apply noise
  fragPosition = (uModelViewMatrix * aVertexPosition).xyz;
  fragNormal = normalize(uNormalMatrix * aVertexNormal);
  
  gl_Position = uProjectionMatrix * uModelViewMatrix * aVertexPosition;
}
`

// Enhanced fragment shader with procedural material effects
const fsSource = `#version 300 es
precision mediump float;

in vec3 fragNormal;
in vec3 fragPosition;
in vec3 modelPos;

uniform vec3 uLightDirection;
uniform vec3 uLightColor;
uniform vec3 uAmbientColor;
uniform float uShininess; 

out vec4 fragColor;

// Simple smooth noise function
float noise(in vec3 x) {
  vec3 p = floor(x);
  vec3 f = fract(x);
  f = f * f * (3.0 - 2.0 * f);
  
  float n = p.x + p.y * 157.0 + 113.0 * p.z;
  
  return mix(mix(mix(hash(n), hash(n + 1.0), f.x),
                   mix(hash(n + 157.0), hash(n + 158.0), f.x), f.y),
               mix(mix(hash(n + 113.0), hash(n + 114.0), f.x),
                   mix(hash(n + 270.0), hash(n + 271.0), f.x), f.y), f.z);
}

float hash(float n) { 
  return fract(sin(n) * 43758.5453);
}

// Main color based on position and terrain properties
vec3 getColorFromTerrain(vec3 pos) {
  // Mars-like colors with variation
  vec3 colorBase = vec3(0.5, 0.2, 0.1); // Default red-mars tone
  
  // Add some variation based on position
  float variation = noise(pos * 0.2) * 0.1;
  return colorBase + variation;
}

void main() {
  vec3 norm = normalize(fragNormal);
  float diff = max(dot(norm, normalize(-uLightDirection)), 0.0);
  
  // Add specular highlight
  vec3 viewDir = normalize(vec3(0.0) - fragPosition);
  vec3 reflectDir = reflect(-normalize(uLightDirection), norm);
  float spec = pow(max(dot(viewDir, reflectDir), 0.0), uShininess);
  
  vec3 ambient = uAmbientColor;
  vec3 diffuse = diff * uLightColor;
  vec3 specular = spec * uLightColor;
  
  // Get terrain color
  vec3 terrainColor = getColorFromTerrain(modelPos);
  
  vec3 result = (ambient + diffuse) * terrainColor + specular;
  
  fragColor = vec4(result, 1.0);
}
`

// Program and buffer references
let shaderProgram = null;
let terrainVertexBuffer = null;
let terrainNormalBuffer = null;
let terrainIndicesBuffer = null;

// Additional buffer references for stones and solar panels
let stoneVertexBuffer = null;
let stoneColorBuffer = null;
let solarPanelVertexBuffer = null;
let solarPanelColorBuffer = null;

// Camera state for 3D view
const camera = ref({
  x: 0,
  y: 15,
  z: 0,
  targetX: 0,
  targetZ: 0,
  angleY: 0, // Horizontal rotation
  angleX: -Math.PI/3 // Vertical perspective (-60 degrees look down)
})

// Track current agent positions to handle animation interpolation
const agentPositions = ref(new Map())

// Matrix utilities
function createIdentityMatrix() {
  return new Float32Array([
    1, 0, 0, 0,
    0, 1, 0, 0,
    0, 0, 1, 0,
    0, 0, 0, 1
  ]);
}

function multiplyMatrices(dst, a, b) {
  dst[0] = a[0] * b[0] + a[4] * b[1] + a[8] * b[2] + a[12] * b[3];
  dst[4] = a[0] * b[4] + a[4] * b[5] + a[8] * b[6] + a[12] * b[7];
  dst[8] = a[0] * b[8] + a[4] * b[9] + a[8] * b[10] + a[12] * b[11];
  dst[12] = a[0] * b[12] + a[4] * b[13] + a[8] * b[14] + a[12] * b[15];

  dst[1] = a[1] * b[0] + a[5] * b[1] + a[9] * b[2] + a[13] * b[3];
  dst[5] = a[1] * b[4] + a[5] * b[5] + a[9] * b[6] + a[13] * b[7];
  dst[9] = a[1] * b[8] + a[5] * b[9] + a[9] * b[10] + a[13] * b[11];
  dst[13] = a[1] * b[12] + a[5] * b[13] + a[9] * b[14] + a[13] * b[15];

  dst[2] = a[2] * b[0] + a[6] * b[1] + a[10] * b[2] + a[14] * b[3];
  dst[6] = a[2] * b[4] + a[6] * b[5] + a[10] * b[6] + a[14] * b[7];
  dst[10] = a[2] * b[8] + a[6] * b[9] + a[10] * b[10] + a[14] * b[11];
  dst[14] = a[2] * b[12] + a[6] * b[13] + a[10] * b[14] + a[14] * b[15];

  dst[3] = a[3] * b[0] + a[7] * b[1] + a[11] * b[2] + a[15] * b[3];
  dst[7] = a[3] * b[4] + a[7] * b[5] + a[11] * b[6] + a[15] * b[7];
  dst[11] = a[3] * b[8] + a[7] * b[9] + a[11] * b[10] + a[15] * b[11];
  dst[15] = a[3] * b[12] + a[7] * b[13] + a[11] * b[14] + a[15] * b[15];

  return dst;
}

function createPerspectiveMatrix(fovy, aspect, near, far) {
  const f = Math.tan(Math.PI * 0.5 - 0.5 * fovy);
  const rangeInv = 1.0 / (near - far);

  return new Float32Array([
    f / aspect, 0, 0, 0,
    0, f, 0, 0,
    0, 0, (near + far) * rangeInv, -1,
    0, 0, near * far * rangeInv * 2, 0
  ]);
}

function createLookAtMatrix(eyeX, eyeY, eyeZ, centerX, centerY, centerZ, upX, upY, upZ) {
  let fx = centerX - eyeX;
  let fy = centerY - eyeY;
  let fz = centerZ - eyeZ;

  // Normalize f
  const r = Math.sqrt(fx * fx + fy * fy + fz * fz);
  if (r === 0) return createIdentityMatrix(); // Identity matrix

  fx /= r;
  fy /= r;
  fz /= r;

  // Calculate cross product of f and up
  let sx = fy * upZ - fz * upY;
  let sy = fz * upX - fx * upZ;
  let sz = fx * upY - fy * upX;

  // Normalize s
  const sr = Math.sqrt(sx * sx + sy * sy + sz * sz);
  if (sr === 0) return createIdentityMatrix();

  sx /= sr;
  sy /= sr;
  sz /= sr;

  // Calculate u vector as cross product of s and f
  let ux = sy * fz - sz * fy;
  let uy = sz * fx - sx * fz;
  let uz = sx * fy - sy * fx;

  return new Float32Array([
    sx, ux, -fx, 0,
    sy, uy, -fy, 0,
    sz, uz, -fz, 0,
    0, 0, 0, 1
  ]);
}

// Initialize WebGL when component mounts
onMounted(async () => {
  if (!hasData.value) return;
  
  const canvas = canvasRef.value
  if (!canvas) return
  
  gl = canvas.getContext('webgl2', { 
    antialias: true,
    alpha: true,
    depth: true,
    preserveDrawingBuffer: true
  })

  if (!gl) {
    console.error('WebGL2 not supported in this browser')
    return
  }

  // Compile shaders
  const shaderSuccess = initShaders()
  if (!shaderSuccess) {
    console.error('Failed to initialize shaders')
    return
  }
  
  // Create buffers and scene geometry
  initBuffers()
  
  // Start animation loop
  animationFrameId = requestAnimationFrame(render)
})

onUnmounted(() => {
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
  }
  
  // Clean up WebGL resources
  if (gl) {
    gl.getExtension('WEBGL_lose_context')?.loseContext()
  }
})

// Watch for world state changes to update agent positions
watch(() => props.worldState, (newState) => {
  if (newState?.agents) {
    // Update agent positions based on world state
    for (const [id, agent] of Object.entries(newState.agents)) {
      if (agent.position) {
        const [x, y] = agent.position
        agentPositions.value.set(id, { 
          prevX: agentPositions.value.get(id)?.currentX ?? x, 
          prevY: agentPositions.value.get(id)?.currentY ?? y, 
          currentX: x, 
          currentY: y,
          lastUpdate: Date.now()
        })
      }
    }
  }
}, { deep: true })

// Watch for follow agent changes to update camera position
watch(() => props.followAgent, () => {
  if (props.followAgent && props.worldState?.agents?.[props.followAgent]?.position) {
    const pos = props.worldState.agents[props.followAgent].position
    camera.value.targetX = pos[0]
    camera.value.targetZ = pos[1] 
  }
}, { immediate: true })

// Initialize shaders
function initShaders() {
  // Create vertex shader
  const vertexShader = gl.createShader(gl.VERTEX_SHADER)
  gl.shaderSource(vertexShader, vsSource)
  gl.compileShader(vertexShader)

  if (!gl.getShaderParameter(vertexShader, gl.COMPILE_STATUS)) {
    console.error('VS Error:', gl.getShaderInfoLog(vertexShader))
    return false
  }

  // Create fragment shader
  const fragmentShader = gl.createShader(gl.FRAGMENT_SHADER)
  gl.shaderSource(fragmentShader, fsSource)
  gl.compileShader(fragmentShader)

  if (!gl.getShaderParameter(fragmentShader, gl.COMPILE_STATUS)) {
    console.error('FS Error:', gl.getShaderInfoLog(fragmentShader))
    return false
  }

  // Create shader program
  shaderProgram = gl.createProgram()
  gl.attachShader(shaderProgram, vertexShader)
  gl.attachShader(shaderProgram, fragmentShader)
  gl.linkProgram(shaderProgram)

  if (!gl.getProgramParameter(shaderProgram, gl.LINK_STATUS)) {
    console.error('Link Error:', gl.getProgramInfoLog(shaderProgram))
    return false
  }

  return true
}

// Initialize geometry buffers
function initBuffers() {
  initTerrainBuffers()
  initStonesBuffers()
  initSolarPanelsBuffers()
}

function initTerrainBuffers() {
  if (!hasData.value) return;
  
  // Create a simple flat grid with some elevation variation
  const vertices = [];
  const normals = [];
  const indices = [];
  
  const gridSize = 20; // Match the 2D grid size
  const tileSize = 2; // Each tile is 2 units wide
  
  // Create grid of tiles
  for (let z = -gridSize/2; z <= gridSize/2; z++) {
    for (let x = -gridSize/2; x <= gridSize/2; x++) {
      // Calculate elevation based on position for varied terrain
      const elevation = calculateTileElevation(x, z);
      
      // Create a vertex for each corner of the tile
      // Bottom left
      vertices.push(x * tileSize, elevation, z * tileSize)
      normals.push(0, 1, 0)
      
      // Bottom right
      vertices.push((x + 1) * tileSize, calculateTileElevation(x + 1, z), z * tileSize)
      normals.push(0, 1, 0)
      
      // Top right
      vertices.push((x + 1) * tileSize, calculateTileElevation(x + 1, z + 1), (z + 1) * tileSize)
      normals.push(0, 1, 0)
      
      // Top left
      vertices.push(x * tileSize, calculateTileElevation(x, z + 1), (z + 1) * tileSize)
      normals.push(0, 1, 0)
    }
  }
  
  // Create indices to form triangles
  const tilesPerRow = gridSize + 1;
  for (let z = 0; z < gridSize; z++) {
    for (let x = 0; x < gridSize; x++) {
      const topLeft = z * tilesPerRow + x
      const topRight = topLeft + 1
      const bottomLeft = (z + 1) * tilesPerRow + x
      const bottomRight = bottomLeft + 1
      
      // Triangle 1: Top left, top right, bottom left
      indices.push(topLeft, topRight, bottomLeft)
      
      // Triangle 2: Top right, bottom right, bottom left
      indices.push(topRight, bottomRight, bottomLeft)
    }
  }

  // Create terrain position buffer
  terrainVertexBuffer = gl.createBuffer()
  gl.bindBuffer(gl.ARRAY_BUFFER, terrainVertexBuffer)
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(vertices), gl.STATIC_DRAW)

  // Create terrain normal buffer
  terrainNormalBuffer = gl.createBuffer()
  gl.bindBuffer(gl.ARRAY_BUFFER, terrainNormalBuffer)
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(normals), gl.STATIC_DRAW)

  // Create terrain indices buffer
  terrainIndicesBuffer = gl.createBuffer()
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, terrainIndicesBuffer)
  gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(indices), gl.STATIC_DRAW)
}

function initStonesBuffers() {
  if (!hasData.value) return;
  
  // Buffer to hold all the stones from the world state
  const vertices = [];
  const colors = [];
  
  if (props.worldState?.stones) {
    for (const stone of props.worldState.stones) {
      const [x, z] = stone.position;
      
      // Simple cubic representation of a stone
      const size = getStoneSize(stone.grade);
      const y = calculateTileElevation(x, z) + size/2; // Halfway above ground
      
      // Define a simple cube centered at (x, y, z)
      const scaledX = x * 2;
      const scaledZ = z * 2;
      
      const vertexOffset = vertices.length / 3;
      
      // Add 8 vertices for the cube (with position scaling)
      vertices.push(scaledX - size, y - size, scaledZ - size); // 0: back-bottom-left  
      vertices.push(scaledX + size, y - size, scaledZ - size); // 1: back-bottom-right
      vertices.push(scaledX - size, y + size, scaledZ - size); // 2: back-top-left
      vertices.push(scaledX + size, y + size, scaledZ - size); // 3: back-top-right
      vertices.push(scaledX - size, y - size, scaledZ + size); // 4: front-bottom-left
      vertices.push(scaledX + size, y - size, scaledZ + size); // 5: front-bottom-right
      vertices.push(scaledX - size, y + size, scaledZ + size); // 6: front-top-left
      vertices.push(scaledX + size, y + size, scaledZ + size); // 7: front-top-right
      
      // Add associated vertex colors
      const stoneColor = getStoneColor(stone.grade);
      for (let i = 0; i < 8; i++) {
        colors.push(stoneColor[0], stoneColor[1], stoneColor[2]); // RGB
      }
    }
  }
  
  // Create stone buffers
  if (vertices.length > 0) {
    stoneVertexBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, stoneVertexBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(vertices), gl.STATIC_DRAW);
    
    stoneColorBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, stoneColorBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(colors), gl.STATIC_DRAW);
  }
}

function initSolarPanelsBuffers() {
  if (!hasData.value) return;
  
  // Buffer to hold all the solar panels from the world state
  const vertices = [];
  const colors = [];
  
  if (props.worldState?.solar_panels) {
    for (const panel of props.worldState.solar_panels) {
      const [x, z] = panel.position;
      
      // Simple solar panel representation
      const size = 1.5;
      const thickness = 0.1;
      const y = calculateTileElevation(x, z) + thickness/2;
      
      // Define a flat rectangular panel
      const scaledX = x * 2;
      const scaledZ = z * 2;
      
      const vertexOffset = vertices.length / 3;
      
      // Add 4 vertices for the solar panel
      vertices.push(scaledX - size, y, scaledZ - size); // 0: back-left  
      vertices.push(scaledX + size, y, scaledZ - size); // 1: back-right
      vertices.push(scaledX - size, y, scaledZ + size); // 2: front-left
      vertices.push(scaledX + size, y, scaledZ + size); // 3: front-right
      
      // Add associated vertex colors
      const panelColor = panel.depleted ? [0.2, 0.2, 0.2] : [0.9, 0.7, 0.2]; // Depleted = gray, active = orange
      
      for (let i = 0; i < 4; i++) {
        colors.push(panelColor[0], panelColor[1], panelColor[2]);
      }
    }
  }
  
  // Create solar panel buffers
  if (vertices.length > 0) {
    solarPanelVertexBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, solarPanelVertexBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(vertices), gl.STATIC_DRAW);
    
    solarPanelColorBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, solarPanelColorBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(colors), gl.STATIC_DRAW);
  }
}

// Simple function for tile elevation based on concentration or position
function calculateTileElevation(x, z) {
  // Add slight variation based on position to create natural-looking terrain
  const noise = Math.sin(x / 2) * Math.cos(z / 2) * 0.3;
  return noise;
}

// Size based on grade
function getStoneSize(grade) {
  const sizes = {
    'pristine': 0.7,
    'rich': 0.6,
    'high': 0.5,
    'medium': 0.4,
    'low': 0.3,
    'unknown': 0.3
  };
  
  return sizes[grade] || 0.3;
}

// Color based on grade
function getStoneColor(grade) {
  const colors = {
    'pristine': [0.9, 0.8, 0.1], // Yellow
    'rich': [0.8, 0.6, 0.1],     // Brownish-yellow
    'high': [0.8, 0.4, 0.1],     // Orange
    'medium': [0.5, 0.5, 0.5],   // Gray
    'low': [0.4, 0.4, 0.4],      // Dark Gray
    'unknown': [0.3, 0.3, 0.4]   // Purple-ish
  };
  
  return colors[grade] || [0.3, 0.3, 0.4];
}

// Render function - main 3D drawing loop
function render(timestamp) {
  if (!gl || !shaderProgram || !hasData.value) return
  
  resizeCanvas()
  
  // Clear the canvas with background color
  gl.clearColor(0.1, 0.12, 0.18, 1.0)  // Dark deep space background
  gl.clearDepth(1.0)
  gl.enable(gl.CULL_FACE)
  gl.enable(gl.DEPTH_TEST)
  gl.depthFunc(gl.LEQUAL)
  gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT)

  // Activate the shader program
  gl.useProgram(shaderProgram)

  // Set up camera based on follow status  
  let lookTargetX = (props.followAgent && props.worldState?.agents?.[props.followAgent]?.position) 
    ? props.worldState.agents[props.followAgent].position[0] * 2  // Scale to 3D
    : camera.value.targetX * 2
    
  let lookTargetZ = (props.followAgent && props.worldState?.agents?.[props.followAgent]?.position) 
    ? props.worldState.agents[props.followAgent].position[1] * 2  // Scale to 3D
    : camera.value.targetZ * 2
    
  let eyeX, eyeY, eyeZ;

  // Set camera based on view mode (follow agent or free)
  if (props.followAgent && props.worldState?.agents?.[props.followAgent]) {
    // Follow mode: position camera behind and above the agent
    eyeX = lookTargetX - 4;  // Slightly offset
    eyeY = 10;               // Height above terrain
    eyeZ = lookTargetZ - 6;  // Behind the target  
  } else {
    // Free camera: position is static for now 
    eyeX = camera.value.x;
    eyeY = 15;
    eyeZ = camera.value.z;
  }
  
  // Create view matrix
  const projectionMatrix = createPerspectiveMatrix(
    Math.PI / 3, // Field of view (60 degrees)
    gl.canvas.width / gl.canvas.height, // Aspect ratio
    0.1, // Near clipping plane
    100.0 // Far clipping plane
  )
  
  const viewMatrix = createLookAtMatrix(
    eyeX, eyeY, eyeZ, // Camera position
    lookTargetX, 0, lookTargetZ, // Look at point
    0, 1, 0 // Up vector
  )
  
  // Combine model-view matrix 
  const modelViewMatrix = createIdentityMatrix()
  const mvm = multiplyMatrices(new Float32Array(16), viewMatrix, modelViewMatrix)

  // Set up lighting parameters
  const lightDirection = [0.4, 1.0, 0.3] // Direction from sun (slightly above and right)
  const lightColor = [0.9, 0.9, 0.7]     // Yellowish directional lighting (sun)
  const ambientColor = [0.15, 0.1, 0.15] // Purple-tinged ambient  
  const shininess = 8.0                  // How shiny surfaces appear

  // Get attribute and uniform locations
  const vertexPositionAttribute = gl.getAttribLocation(shaderProgram, 'aVertexPosition')
  const vertexNormalAttribute = gl.getAttribLocation(shaderProgram, 'aVertexNormal')
  
  const uProjectionMatrix = gl.getUniformLocation(shaderProgram, 'uProjectionMatrix')
  const uModelViewMatrix = gl.getUniformLocation(shaderProgram, 'uModelViewMatrix')
  const uNormalMatrix = gl.getUniformLocation(shaderProgram, 'uNormalMatrix')
  const uShininess = gl.getUniformLocation(shaderProgram, 'uShininess')
  
  const uLightDirection = gl.getUniformLocation(shaderProgram, 'uLightDirection')
  const uLightColor = gl.getUniformLocation(shaderProgram, 'uLightColor')
  const uAmbientColor = gl.getUniformLocation(shaderProgram, 'uAmbientColor')

  if (terrainVertexBuffer) {
    // Draw terrain with shader program
    gl.uniformMatrix4fv(uProjectionMatrix, false, projectionMatrix)
    gl.uniformMatrix4fv(uModelViewMatrix, false, mvm)
    
    // Calculate normal matrix  
    const normalMatrix = getNormalMatrix(mvm)
    gl.uniformMatrix3fv(uNormalMatrix, false, normalMatrix)
    
    gl.uniform3fv(uLightDirection, lightDirection)
    gl.uniform3fv(uLightColor, lightColor)
    gl.uniform3fv(uAmbientColor, ambientColor)
    gl.uniform1f(uShininess, shininess)

    // Set up position attribute
    gl.bindBuffer(gl.ARRAY_BUFFER, terrainVertexBuffer)
    gl.vertexAttribPointer(
      vertexPositionAttribute, 3, gl.FLOAT, false, 0, 0)
    gl.enableVertexAttribArray(vertexPositionAttribute)

    // Set up normal attribute
    gl.bindBuffer(gl.ARRAY_BUFFER, terrainNormalBuffer)
    gl.vertexAttribPointer(
      vertexNormalAttribute, 3, gl.FLOAT, false, 0, 0)
    gl.enableVertexAttribArray(vertexNormalAttribute)

    // Bind and draw indices for terrain
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, terrainIndicesBuffer)
    const indexCount = 20 * 20 * 6 // For a 20x20 grid with triangles * 6 indices per tile pair
    gl.drawElements(gl.TRIANGLES, indexCount, gl.UNSIGNED_SHORT, 0)
  }

  // Draw stones if they exist
  drawStones()

  // Draw solar panels if they exist
  drawSolarPanels()

  // Draw agents as cubes
  drawAgents()

  // Continue the animation loop
  animationFrameId = requestAnimationFrame(render)
}

// Helper to extract 3x3 matrix for normal calculation
function getNormalMatrix(mvMatrix) {
  // Simplified computation: extract 3x3 upper left of model-view matrix's transpose
  const normalMatrix = new Float32Array(9);
  
  // Transpose of 3x3 upper left part
  normalMatrix[0] = mvMatrix[0]; // m00
  normalMatrix[1] = mvMatrix[4]; // m10  
  normalMatrix[2] = mvMatrix[8]; // m20
  normalMatrix[3] = mvMatrix[1]; // m01
  normalMatrix[4] = mvMatrix[5]; // m11
  normalMatrix[5] = mvMatrix[9]; // m21
  normalMatrix[6] = mvMatrix[2]; // m02
  normalMatrix[7] = mvMatrix[6]; // m12
  normalMatrix[8] = mvMatrix[10]; // m22

  // Return the computed normal matrix
  return normalMatrix;
}

// Draw agents as 3D objects at their positions
function drawAgents() {
  if (!gl || !shaderProgram || !props.worldState || !props.worldState.agents) return

  // Set up the agent-specific shader attributes
  const vertexPositionAttribute = gl.getAttribLocation(shaderProgram, 'aVertexPosition')
  const vertexNormalAttribute = gl.getAttribLocation(shaderProgram, 'aVertexNormal')
  
  for (const [id, agent] of Object.entries(props.worldState.agents)) {
    if (!agent.position) continue
    
    const [x, z] = agent.position // Use z as the depth coordinate
    const scaledX = x * 2  // Scale to match our 3D tile system
    const scaledZ = z * 2
    const y = calculateTileElevation(x, z) + 0.5; // Slightly above ground
    
    // Create a temporary simple cube for the agent
    const agentVertices = [
      // Front face
      scaledX - 0.4, y - 0.4, scaledZ + 0.4, // 0: BL
      scaledX + 0.4, y - 0.4, scaledZ + 0.4, // 1: BR
      scaledX + 0.4, y + 0.4, scaledZ + 0.4, // 2: TR
      scaledX - 0.4, y + 0.4, scaledZ + 0.4, // 3: TL
      
      // Back face
      scaledX - 0.4, y - 0.4, scaledZ - 0.4, // 4: BL
      scaledX + 0.4, y - 0.4, scaledZ - 0.4, // 5: BR
      scaledX + 0.4, y + 0.4, scaledZ - 0.4, // 6: TR
      scaledX - 0.4, y + 0.4, scaledZ - 0.4  // 7: TL
    ];
    
    // Normal vectors pointing outward from cube faces
    const agentNormals = [
       // Front face (normal pointing out of screen)
      0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1,
      // Back face (normal pointing towards screen)
      0, 0, -1, 0, 0, -1, 0, 0, -1, 0, 0, -1
    ];
    
    // Indices to define triangles
    const cubeIndices = [
      // Front face
      0, 1, 2,  0, 2, 3,
      // Back face  
      4, 6, 5,  4, 7, 6,
      // Top face
      3, 2, 6,  3, 6, 7,
      // Bottom face
      4, 0, 1,  4, 1, 5, 
      // Right face
      1, 5, 6,  1, 6, 2,
      // Left face
      4, 7, 0,  0, 7, 3
    ];
    
    // Create temporary buffers for the single agent
    const tempVertexBuffer = gl.createBuffer();
    const tempNormalBuffer = gl.createBuffer();
    const tempIndexBuffer = gl.createBuffer();
    
    gl.bindBuffer(gl.ARRAY_BUFFER, tempVertexBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(agentVertices), gl.STATIC_DRAW);
    
    gl.bindBuffer(gl.ARRAY_BUFFER, tempNormalBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(agentNormals), gl.STATIC_DRAW);
    
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, tempIndexBuffer);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(cubeIndices), gl.STATIC_DRAW);
    
    // Render this agent cube using current matrices and lighting values
    gl.bindBuffer(gl.ARRAY_BUFFER, tempVertexBuffer);
    gl.vertexAttribPointer(vertexPositionAttribute, 3, gl.FLOAT, false, 0, 0);
    gl.enableVertexAttribArray(vertexPositionAttribute);
    
    gl.bindBuffer(gl.ARRAY_BUFFER, tempNormalBuffer);
    gl.vertexAttribPointer(vertexNormalAttribute, 3, gl.FLOAT, false, 0, 0);
    gl.enableVertexAttribArray(vertexNormalAttribute);
    
    // Render the cube as a single agent entity
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, tempIndexBuffer);
    gl.drawElements(gl.TRIANGLES, cubeIndices.length, gl.UNSIGNED_SHORT, 0);
    
    // Clean up temporary buffers
    gl.deleteBuffer(tempVertexBuffer);
    gl.deleteBuffer(tempNormalBuffer);
    gl.deleteBuffer(tempIndexBuffer);
  }
}

// Draw stones using a new program if needed or continue using shaderProgram for now
function drawStones() {
  if (!gl || !stoneVertexBuffer) return;
  
  // In a future implementation, stones would be drawn here
}

// Draw solar panels similarly to stones
function drawSolarPanels() {
  if (!gl || !solarPanelVertexBuffer) return;
  
  // In a future implementation, panels would be drawn here
}

// Handle resizing
function resizeCanvas() {
  const canvas = canvasRef.value
  if (!canvas) return
  
  const displayWidth = canvas.clientWidth
  const displayHeight = canvas.clientHeight
  
  if (canvas.width !== displayWidth || canvas.height !== displayHeight) {
    canvas.width = displayWidth
    canvas.height = displayHeight
    gl.viewport(0, 0, canvas.width, canvas.height)
  }
}

// Mouse controls for camera rotation
// (Implementation would go here for user control of the 3rd-person camera)
</script>

<template>
  <section class="world-map-3d">
    <h2>
      3D Mars Environment
      <span
        v-if="followAgent"
        class="cam-hint"
      >(following {{ followAgent }})</span>
      <span
        v-else
        class="cam-hint"
      >(3D view)</span>
    </h2>
    <div class="map-controls">
      <small>3D View</small>
    </div>
    <canvas
      v-if="hasData"
      ref="canvasRef"
      class="map-canvas"
      role="img"
      aria-label="3D visualization of Mars environment with rovers and drones"
    >
      Canvas is not supported in your browser
    </canvas>
    <div
      v-else
      class="map-skeleton"
    >
      <div class="skeleton-grid">
        <div
          v-for="i in 100"
          :key="i"
          class="skeleton-tile"
        />
      </div>
      <div class="skeleton-message">
        Connecting to satellite feed...
      </div>
    </div>
  </section>
</template>

<style scoped>
.world-map-3d {
  flex: 3;
  padding: 0.75rem;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  min-width: 0;
  position: relative;
  overflow: hidden;
}

.map-canvas {
  width: 100%;
  height: auto;
  display: block;
  min-height: 400px;
}

.cam-hint {
  font-size: 0.6rem;
  color: var(--text-dimmer);
  font-weight: normal;
  text-transform: none;
  letter-spacing: 0;
}

.map-controls {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  margin-bottom: 0.35rem;
}

.map-controls small {
  font-size: 0.65rem;
  color: var(--text-muted);
}

/* Similar loading skeleton as WorldMap.vue */
.map-skeleton {
  width: 100%;
  aspect-ratio: 1;
  background: var(--bg-primary);
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(10, 1fr);
  grid-template-rows: repeat(10, 1fr);
  width: 100%;
  height: 100%;
  opacity: 0.1;
}

.skeleton-tile {
  border: 1px solid var(--accent-blue);
  animation: pulse-grid 2s infinite;
}

.skeleton-message {
  position: absolute;
  color: var(--accent-blue);
  font-family: var(--font-mono);
  font-size: 0.8rem;
  background: rgba(10, 10, 15, 0.8);
  padding: 0.5rem 1rem;
  border-radius: var(--radius-md);
  border: 1px solid var(--accent-blue);
  animation: pulse-text 1.5s infinite alternate;
}

@keyframes pulse-grid {
  0%, 100% { opacity: 0.1; }
  50% { opacity: 0.3; }
}

@keyframes pulse-text {
  from { opacity: 0.7; }
  to { opacity: 1; }
}
</style>