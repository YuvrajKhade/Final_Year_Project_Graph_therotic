// // ============================================================================
// // ANIMATION STATE
// // ============================================================================

// let currentStep = 0;
// let isPlaying = false;
// let animationInterval = null;
// let animationSpeed = 2000;

// // Stable node positions — computed ONCE and reused every step
// let stablePositions = null;

// // Color palette for time slots - expanded
// const colorPalette = {
//     1: '#3498db', 2: '#9b59b6', 3: '#f39c12', 4: '#1abc9c',
//     5: '#e67e22', 6: '#c0392b', 7: '#16a085', 8: '#8e44ad',
//     9: '#27ae60', 10: '#2980b9', 11: '#d35400', 12: '#2c3e50',
//     13: '#8e44ad', 14: '#16a085', 15: '#e74c3c'
// };

// // Function to get color for ANY slot number (handles > 15 slots)
// function getSlotColor(slot) {
//     if (colorPalette[slot]) return colorPalette[slot];
//     // Generate color using golden angle for good distribution
//     var hue = (slot * 137.5) % 360;
//     return 'hsl(' + hue + ', 70%, 50%)';
// }

// // ============================================================================
// // INITIALIZATION
// // ============================================================================

// function initializeAnimation() {
//     console.log('Initializing animation...');

//     if (typeof animationData === 'undefined' || !animationData) {
//         showError('Animation data not loaded. Please analyze a dataset first.');
//         return;
//     }

//     if (!animationData.history || animationData.history.length === 0) {
//         showError('No animation steps found.');
//         return;
//     }

//     console.log('Nodes:', animationData.graph.nodes.length, '| Edges:', animationData.graph.edges.length, '| Steps:', animationData.history.length);

//     document.getElementById('totalSteps').textContent = animationData.history.length;

//     // Pre-compute stable layout positions ONCE
//     computeStableLayout(function() {
//         setupControls();
//         renderStep(0);
//     });
// }

// function showError(msg) {
//     const el = document.getElementById('loadingState');
//     if (el) {
//         el.innerHTML = '<div class="alert alert-danger m-4"><i class="fas fa-exclamation-triangle"></i> <strong>Error:</strong> ' + msg + '</div>';
//         el.style.display = 'block';
//     }
// }

// // ============================================================================
// // COMPUTE STABLE LAYOUT ONCE (no jumping between steps)
// // ============================================================================

// // ============================================================================
// // COMPUTE STABLE LAYOUT — Better fitting for large graphs
// // ============================================================================

// function computeStableLayout(callback) {
//     const canvas = document.getElementById('graphCanvas');
//     const W = canvas.clientWidth || 800;
//     const H = 560;

//     const nodes = animationData.graph.nodes.map(function(d) { return Object.assign({}, d); });
//     const edges = animationData.graph.edges.map(function(d) { return Object.assign({}, d); });

//     console.log('Computing layout for', nodes.length, 'nodes,', edges.length, 'edges');

//     // Adjust forces based on graph size
//     const nodeCount = nodes.length;
//     const linkDistance = nodeCount > 50 ? 70 : nodeCount > 30 ? 85 : 90;
//     const chargeStrength = nodeCount > 50 ? -200 : nodeCount > 30 ? -300 : -400;
//     const collisionRadius = nodeCount > 50 ? 32 : 38;

//     const simulation = d3.forceSimulation(nodes)
//         .force('link', d3.forceLink(edges).id(function(d) { return d.id; }).distance(linkDistance).strength(0.7))
//         .force('charge', d3.forceManyBody().strength(chargeStrength))
//         .force('center', d3.forceCenter(W / 2, H / 2))
//         .force('collision', d3.forceCollide().radius(collisionRadius))
//         .force('x', d3.forceX(W / 2).strength(0.05))
//         .force('y', d3.forceY(H / 2).strength(0.05))
//         .alphaDecay(0.02)
//         .stop();

//     // Run simulation to completion
//     const iterations = nodeCount > 50 ? 400 : 300;
//     for (var i = 0; i < iterations; i++) simulation.tick();

//     // Calculate bounding box of all nodes
//     var minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
//     nodes.forEach(function(n) {
//         minX = Math.min(minX, n.x);
//         maxX = Math.max(maxX, n.x);
//         minY = Math.min(minY, n.y);
//         maxY = Math.max(maxY, n.y);
//     });

//     const graphWidth = maxX - minX;
//     const graphHeight = maxY - minY;

//     console.log('Graph bounds: minX=' + minX + ', maxX=' + maxX + ', width=' + graphWidth);

//     // Scale and center the graph to fit canvas with padding
//     const padding = nodeCount > 50 ? 50 : 55;
//     const availableWidth = W - (2 * padding);
//     const availableHeight = H - (2 * padding);

//     const scaleX = graphWidth > 0 ? availableWidth / graphWidth : 1;
//     const scaleY = graphHeight > 0 ? availableHeight / graphHeight : 1;
//     const scale = Math.min(scaleX, scaleY, 1.2);

//     console.log('Scale: ' + scale.toFixed(3) + ' (scaleX=' + scaleX.toFixed(3) + ', scaleY=' + scaleY.toFixed(3) + ')');

//     // Transform all positions
//     stablePositions = {};
//     nodes.forEach(function(n) {
//         const scaledX = (n.x - minX) * scale;
//         const scaledY = (n.y - minY) * scale;
        
//         const offsetX = (W - (graphWidth * scale)) / 2;
//         const offsetY = (H - (graphHeight * scale)) / 2;
        
//         stablePositions[n.id] = {
//             x: scaledX + offsetX,
//             y: scaledY + offsetY
//         };
//     });

//     // Verify and clamp if needed
//     var outOfBounds = 0;
//     for (var id in stablePositions) {
//         var pos = stablePositions[id];
//         if (pos.x < padding || pos.x > W - padding || pos.y < padding || pos.y > H - padding) {
//             outOfBounds++;
//         }
//     }

//     if (outOfBounds > 0) {
//         console.warn(outOfBounds + ' nodes outside bounds, clamping...');
//         for (var id in stablePositions) {
//             stablePositions[id].x = Math.max(padding, Math.min(W - padding, stablePositions[id].x));
//             stablePositions[id].y = Math.max(padding, Math.min(H - padding, stablePositions[id].y));
//         }
//     }

//     console.log('Layout ready: ' + Object.keys(stablePositions).length + ' nodes, all within bounds');
//     callback();
// }

// // ============================================================================
// // CONTROLS
// // ============================================================================

// function setupControls() {
//     document.getElementById('playBtn').addEventListener('click', play);
//     document.getElementById('pauseBtn').addEventListener('click', pause);
//     document.getElementById('resetBtn').addEventListener('click', reset);
    
//     // Edge visibility toggle
//     var edgesVisible = true;
//     document.getElementById('toggleEdgesBtn').addEventListener('click', function() {
//         edgesVisible = !edgesVisible;
//         var edgeLayer = document.querySelector('.edge-layer');
//         if (edgeLayer) {
//             edgeLayer.style.display = edgesVisible ? 'block' : 'none';
//         }
//         this.style.background = edgesVisible ? '#16a085' : '#95a5a6';
//         this.innerHTML = edgesVisible ? '<i class="fas fa-project-diagram"></i> Edges' : '<i class="fas fa-project-diagram"></i> Edges';
//     });

//     document.getElementById('speedSlider').addEventListener('input', function(e) {
//         animationSpeed = parseInt(e.target.value);
//         document.getElementById('speedValue').textContent = (animationSpeed / 1000).toFixed(1) + 's';
//         if (isPlaying) { pause(); play(); }
//     });
// }

// function play() {
//     if (isPlaying) return;

//     // If at the end, wrap back to start
//     if (currentStep >= animationData.history.length - 1) {
//         currentStep = 0;
//         hideCompletionBanner();
//     }

//     isPlaying = true;
//     document.getElementById('playBtn').style.display = 'none';
//     document.getElementById('pauseBtn').style.display = 'inline-block';

//     animationInterval = setInterval(function() {
//         if (currentStep < animationData.history.length - 1) {
//             currentStep++;
//             renderStep(currentStep);
//         } else {
//             // End reached: STOP but keep final state visible
//             pause();
//             showCompletionBanner();
//         }
//     }, animationSpeed);
// }

// function pause() {
//     isPlaying = false;
//     document.getElementById('playBtn').style.display = 'inline-block';
//     document.getElementById('pauseBtn').style.display = 'none';
//     if (animationInterval) {
//         clearInterval(animationInterval);
//         animationInterval = null;
//     }
// }

// function reset() {
//     pause();
//     hideCompletionBanner();
//     currentStep = 0;
//     renderStep(0);
// }

// function showCompletionBanner() {
//     var banner = document.getElementById('completionBanner');
//     if (banner) { banner.style.display = 'flex'; return; }
    
//     // Get final statistics
//     var totalNodes = animationData.graph.nodes.length;
//     var finalStep = animationData.history[animationData.history.length - 1];
//     var totalColors = finalStep.colored ? Math.max.apply(null, Object.values(finalStep.colored).concat([0])) : 0;
//     var totalColored = Object.keys(finalStep.colored || {}).length;
    
//     banner = document.createElement('div');
//     banner.id = 'completionBanner';
//     banner.style.cssText = [
//         'position:absolute','top:12px','left:50%','transform:translateX(-50%)',
//         'background:linear-gradient(135deg,#2ecc71,#27ae60)',
//         'color:white','padding:12px 24px','border-radius:50px',
//         'font-weight:700','font-size:0.9rem','z-index:999',
//         'box-shadow:0 4px 20px rgba(46,204,113,0.45)',
//         'display:flex','align-items:center','gap:12px','white-space:nowrap'
//     ].join(';');
    
//     var statusMsg = totalColored === totalNodes 
//         ? '✓ All ' + totalNodes + ' tasks scheduled in ' + totalColors + ' time slots' 
//         : '⚠ Only ' + totalColored + '/' + totalNodes + ' tasks colored';
    
//     banner.innerHTML = '<i class="fas fa-check-circle"></i>' + statusMsg + 
//         '<span style="opacity:0.85;font-size:0.8rem;margin-left:8px;border-left:2px solid rgba(255,255,255,0.4);padding-left:12px">Click Reset to replay</span>';
    
//     var canvas = document.getElementById('graphCanvas');
//     canvas.style.position = 'relative';
//     canvas.prepend(banner);
    
//     console.log('Completion:', totalColored, '/', totalNodes, 'nodes colored in', totalColors, 'colors');
// }

// function hideCompletionBanner() {
//     var banner = document.getElementById('completionBanner');
//     if (banner) banner.style.display = 'none';
// }

// // ============================================================================
// // RENDER STEP — updates description, panels, and graph
// // ============================================================================

// function renderStep(stepIndex) {
//     var step = animationData.history[stepIndex];
//     document.getElementById('currentStep').textContent = stepIndex + 1;

//     // Color-coded step description bar
//     var descEl = document.getElementById('stepDescription');
//     descEl.textContent = step.description;

//     if (step.description.indexOf('Initial') !== -1) {
//         descEl.style.background = '#f8f9fa'; descEl.style.borderLeftColor = '#95a5a6'; descEl.style.color = '#2c3e50';
//     } else if (step.description.indexOf('random priorities') !== -1) {
//         descEl.style.background = '#ebf5fb'; descEl.style.borderLeftColor = '#3498db'; descEl.style.color = '#1a5276';
//     } else if (step.description.indexOf('Select') !== -1) {
//         descEl.style.background = '#eafaf1'; descEl.style.borderLeftColor = '#2ecc71'; descEl.style.color = '#1e8449';
//     } else if (step.description.indexOf('Assign color') !== -1) {
//         descEl.style.background = '#f5eef8'; descEl.style.borderLeftColor = '#9b59b6'; descEl.style.color = '#6c3483';
//     } else if (step.description.indexOf('Remove') !== -1) {
//         descEl.style.background = '#fdedec'; descEl.style.borderLeftColor = '#e74c3c'; descEl.style.color = '#922b21';
//     } else if (step.description.indexOf('Complete') !== -1) {
//         descEl.style.background = '#eafaf1'; descEl.style.borderLeftColor = '#27ae60'; descEl.style.color = '#1e8449';
//     }

//     updateStatusPanel(step);
//     updateSlotsPanel(step);
//     renderGraph(step);
// }

// // ============================================================================
// // STATUS + SLOTS PANELS
// // ============================================================================

// function updateStatusPanel(step) {
//     document.getElementById('activeTasks').textContent   = step.active.length;
//     document.getElementById('coloredTasks').textContent  = Object.keys(step.colored).length;
//     document.getElementById('selectedTasks').textContent = step.selected.length;
//     document.getElementById('removedTasks').textContent  = step.removed.length;
    
//     var vals = Object.values(step.colored);
//     var maxColor = vals.length > 0 ? Math.max.apply(null, vals) : 0;
//     document.getElementById('currentColor').textContent = maxColor > 0 ? 'Slot ' + maxColor : '—';
    
//     // Calculate max degree (delta)
//     if (!window.graphMaxDegree) {
//         var degrees = {};
//         animationData.graph.edges.forEach(function(e) {
//             var src = (typeof e.source === 'object') ? e.source.id : e.source;
//             var tgt = (typeof e.target === 'object') ? e.target.id : e.target;
//             degrees[src] = (degrees[src] || 0) + 1;
//             degrees[tgt] = (degrees[tgt] || 0) + 1;
//         });
//         window.graphMaxDegree = Math.max.apply(null, Object.values(degrees).concat([0]));
//     }
//     document.getElementById('maxDegree').textContent = window.graphMaxDegree;
    
//     // Total colors used (chromatic number)
//     var totalColors = vals.length > 0 ? Math.max.apply(null, vals) : 0;
//     document.getElementById('chromaticNumber').textContent = totalColors > 0 ? totalColors : '—';
// }

// function updateSlotsPanel(step) {
//     var slotsDiv = document.getElementById('slotAssignments');
//     if (Object.keys(step.colored).length === 0) {
//         slotsDiv.innerHTML = '<p class="text-muted fst-italic" style="font-size:0.9rem;">No assignments yet...</p>';
//         return;
//     }

//     var slotGroups = {};
//     for (var node in step.colored) {
//         var color = step.colored[node];
//         if (!slotGroups[color]) slotGroups[color] = [];
//         slotGroups[color].push('T' + node);
//     }

//     var html = '';
//     Object.keys(slotGroups).sort(function(a,b){return a-b;}).forEach(function(slot) {
//         var bg = getSlotColor(parseInt(slot));  // Use dynamic color function
//         html += '<div class="slot-item" style="border-left-color:' + bg + ';margin-bottom:8px;">' +
//             '<div class="slot-number" style="color:' + bg + ';font-weight:700;font-size:0.85rem;">' +
//             '<i class="fas fa-circle" style="font-size:0.5rem;margin-right:4px;"></i>Time Slot ' + slot + '</div>' +
//             '<div class="slot-tasks" style="color:#555;font-size:0.82rem;margin-top:3px;">' + slotGroups[slot].join(' &middot; ') + '</div>' +
//             '</div>';
//     });
//     slotsDiv.innerHTML = html;
// }

// // ============================================================================
// // RENDER GRAPH — stable positions, clear visual states
// // ============================================================================

// function renderGraph(step) {
//     if (!stablePositions) return;

//     var canvas = document.getElementById('graphCanvas');
//     var W = canvas.clientWidth || 800;
//     var H = 560;

//     var svg = d3.select('#graphSvg');
//     svg.selectAll('*').remove();
//     svg.attr('width', W).attr('height', H).attr('viewBox', '0 0 ' + W + ' ' + H);

//     var nodes = animationData.graph.nodes;
//     var edges = animationData.graph.edges;

//     console.log('Rendering:', nodes.length, 'nodes,', edges.length, 'edges');

//     // ── Draw edges FIRST (below nodes) ──────────────────────────
//     var edgeG = svg.append('g')
//         .attr('class', 'edge-layer')
//         .attr('id', 'edge-layer-group');
    
//     var edgesDrawn = 0;
//     var edgesFailed = 0;
    
//     edges.forEach(function(e) {
//         var srcId = (typeof e.source === 'object') ? e.source.id : e.source;
//         var tgtId = (typeof e.target === 'object') ? e.target.id : e.target;
//         var src = stablePositions[srcId];
//         var tgt = stablePositions[tgtId];
        
//         if (!src || !tgt) {
//             console.warn('Missing position for edge:', srcId, '->', tgtId);
//             edgesFailed++;
//             return;
//         }
        
//         // Verify coordinates are valid numbers
//         if (isNaN(src.x) || isNaN(src.y) || isNaN(tgt.x) || isNaN(tgt.y)) {
//             console.error('Invalid coordinates for edge', srcId, '->', tgtId, src, tgt);
//             edgesFailed++;
//             return;
//         }

//         var srcSel = step.selected.indexOf(srcId) !== -1;
//         var tgtSel = step.selected.indexOf(tgtId) !== -1;
//         var srcRem = step.removed.indexOf(srcId) !== -1;
//         var tgtRem = step.removed.indexOf(tgtId) !== -1;
//         var isConflict = (srcSel && tgtRem) || (tgtSel && srcRem);

//         // VERY VISIBLE edges - almost black, thick lines
//         var strokeColor = isConflict ? '#e74c3c' : '#000000';  // BLACK for normal edges!
//         var strokeWidth = isConflict ? 5 : 3;
//         var opacity = 1.0;

//         var line = edgeG.append('line')
//             .attr('x1', src.x)
//             .attr('y1', src.y)
//             .attr('x2', tgt.x)
//             .attr('y2', tgt.y)
//             .attr('stroke', strokeColor)
//             .attr('stroke-width', strokeWidth)
//             .attr('stroke-dasharray', isConflict ? '8,4' : null)
//             .attr('opacity', opacity)
//             .attr('stroke-linecap', 'round')
//             .attr('class', 'graph-edge');
        
//         edgesDrawn++;
//     });
    
//     console.log('Drew', edgesDrawn, 'edges successfully,', edgesFailed, 'failed');

//     // ── Draw nodes SECOND (on top) ───────────────────────────────────────────────
//     var nodeG = svg.append('g')
//         .attr('class', 'node-layer')
//         .attr('id', 'node-layer-group');
//     nodes.forEach(function(n) {
//         var pos = stablePositions[n.id];
//         if (!pos) return;

//         var isSel   = step.selected.indexOf(n.id) !== -1;
//         var isRem   = step.removed.indexOf(n.id) !== -1;
//         var slot    = step.colored[n.id] !== undefined ? step.colored[n.id] : step.colored[String(n.id)];
//         var isAct   = step.active.indexOf(n.id) !== -1;

//         var fillColor, strokeColor, strokeW, textColor, opacity;

//         if (isSel) {
//             fillColor = '#2ecc71'; strokeColor = '#f39c12'; strokeW = 4; textColor = 'white'; opacity = 1;
//         } else if (isRem && !slot) {
//             fillColor = '#e74c3c'; strokeColor = '#c0392b'; strokeW = 3; textColor = 'white'; opacity = 0.85;
//         } else if (slot !== undefined && slot !== null) {
//             fillColor = getSlotColor(slot);  // Use dynamic color function
//             strokeColor = '#2c3e50'; strokeW = 3; textColor = 'white'; opacity = 1;
//         } else if (isAct) {
//             fillColor = '#f0f3f4'; strokeColor = '#7f8c8d'; strokeW = 2; textColor = '#2c3e50'; opacity = 1;
//         } else {
//             // This shouldn't happen - all nodes should be active, colored, selected, or removed
//             fillColor = '#ecf0f1'; strokeColor = '#95a5a6'; strokeW = 2; textColor = '#7f8c8d'; opacity = 0.6;
//             console.warn('Node', n.id, 'in undefined state! slot:', slot, 'active:', isAct, 'selected:', isSel, 'removed:', isRem);
//         }

//         var g = nodeG.append('g').attr('transform', 'translate(' + pos.x + ',' + pos.y + ')').attr('opacity', opacity);

//         // Pulse ring for selected
//         if (isSel) {
//             g.append('circle').attr('r', 36).attr('fill','none').attr('stroke','#f39c12').attr('stroke-width',2).attr('stroke-dasharray','5,3').attr('opacity',0.6);
//         }

//         // Main node circle
//         g.append('circle').attr('r', 26).attr('fill', fillColor).attr('stroke', strokeColor).attr('stroke-width', strokeW);

//         // Task label inside node
//         g.append('text')
//             .attr('text-anchor','middle').attr('dy','0.35em')
//             .attr('font-size', nodes.length > 20 ? 10 : 12)
//             .attr('font-weight','bold').attr('fill',textColor).attr('pointer-events','none')
//             .text('T' + n.id);

//         // Small slot badge top-right
//         if (slot !== undefined && slot !== null) {
//             var badgeColor = getSlotColor(slot);  // Use dynamic color function
//             g.append('circle').attr('cx',18).attr('cy',-18).attr('r',11).attr('fill',badgeColor).attr('stroke','white').attr('stroke-width',2.5);
//             g.append('text').attr('x',18).attr('y',-14).attr('text-anchor','middle').attr('font-size',9).attr('font-weight','bold').attr('fill','white').attr('pointer-events','none').text(slot);
//         }

//         // Random priority pill above node
//         var rv = step.random_values[n.id] !== undefined ? step.random_values[n.id] : step.random_values[String(n.id)];
//         if (rv !== undefined && isAct) {
//             g.append('rect').attr('x',-20).attr('y',-50).attr('width',40).attr('height',17).attr('rx',5).attr('fill','#e74c3c').attr('opacity',0.92);
//             g.append('text').attr('text-anchor','middle').attr('dy',-37).attr('font-size',10).attr('font-weight','bold').attr('fill','white').attr('pointer-events','none').text(rv.toFixed(2));
//         }

//         // Tooltip
//         g.append('title').text(
//             slot !== undefined ? 'Task ' + n.id + ' → Time Slot ' + slot :
//             isSel ? 'Task ' + n.id + ' — Selected (MIS)' :
//             isRem ? 'Task ' + n.id + ' — Removed (conflict)' :
//             'Task ' + n.id + ' — Waiting'
//         );
//     });
// }


// ============================================================================
// ANIMATION STATE
// ============================================================================

let currentStep = 0;
let isPlaying = false;
let animationInterval = null;
let animationSpeed = 2000;

// Stable node positions — computed ONCE and reused every step
let stablePositions = null;

// Color palette for time slots - expanded
const colorPalette = {
    1: '#3498db', 2: '#9b59b6', 3: '#f39c12', 4: '#1abc9c',
    5: '#e67e22', 6: '#c0392b', 7: '#16a085', 8: '#8e44ad',
    9: '#27ae60', 10: '#2980b9', 11: '#d35400', 12: '#2c3e50',
    13: '#8e44ad', 14: '#16a085', 15: '#e74c3c'
};

// Function to get color for ANY slot number (handles > 15 slots)
function getSlotColor(slot) {
    if (colorPalette[slot]) return colorPalette[slot];
    // Generate color using golden angle for good distribution
    var hue = (slot * 137.5) % 360;
    return 'hsl(' + hue + ', 70%, 50%)';
}

// ============================================================================
// INITIALIZATION
// ============================================================================

function initializeAnimation() {
    console.log('Initializing animation...');

    if (typeof animationData === 'undefined' || !animationData) {
        showError('Animation data not loaded. Please analyze a dataset first.');
        return;
    }

    if (!animationData.history || animationData.history.length === 0) {
        showError('No animation steps found.');
        return;
    }

    console.log('Nodes:', animationData.graph.nodes.length, '| Edges:', animationData.graph.edges.length, '| Steps:', animationData.history.length);

    document.getElementById('totalSteps').textContent = animationData.history.length;

    // Pre-compute stable layout positions ONCE
    computeStableLayout(function() {
        setupControls();
        renderStep(0);
    });
}

function showError(msg) {
    const el = document.getElementById('loadingState');
    if (el) {
        el.innerHTML = '<div class="alert alert-danger m-4"><i class="fas fa-exclamation-triangle"></i> <strong>Error:</strong> ' + msg + '</div>';
        el.style.display = 'block';
    }
}

// ============================================================================
// COMPUTE STABLE LAYOUT ONCE (no jumping between steps)
// ============================================================================

// ============================================================================
// COMPUTE STABLE LAYOUT — Better fitting for large graphs
// ============================================================================

function computeStableLayout(callback) {
    const canvas = document.getElementById('graphCanvas');
    const W = canvas.clientWidth || 800;
    const H = 560;

    const nodes = animationData.graph.nodes.map(function(d) { return Object.assign({}, d); });
    const edges = animationData.graph.edges.map(function(d) { return Object.assign({}, d); });

    console.log('Computing layout for', nodes.length, 'nodes,', edges.length, 'edges');

    // Adjust forces based on graph size - INCREASED spacing to prevent overlap
    const nodeCount = nodes.length;
    const linkDistance = nodeCount > 50 ? 80 : nodeCount > 30 ? 100 : 200;  // Increased from 70/85/90
    const chargeStrength = nodeCount > 50 ? -300 : nodeCount > 30 ? -400 : -500;  // Stronger repulsion
    const collisionRadius = nodeCount > 50 ? 28 : 32;  // Smaller collision for smaller nodes

    const simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(edges).id(function(d) { return d.id; }).distance(linkDistance).strength(0.6))
        .force('charge', d3.forceManyBody().strength(chargeStrength))
        .force('center', d3.forceCenter(W / 2, H / 2))
        .force('collision', d3.forceCollide().radius(collisionRadius))
        .force('x', d3.forceX(W / 2).strength(0.05))
        .force('y', d3.forceY(H / 2).strength(0.05))
        .alphaDecay(0.02)
        .stop();

    // Run simulation to completion
    const iterations = nodeCount > 50 ? 400 : 300;
    for (var i = 0; i < iterations; i++) simulation.tick();

    // Calculate bounding box of all nodes
    var minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    nodes.forEach(function(n) {
        minX = Math.min(minX, n.x);
        maxX = Math.max(maxX, n.x);
        minY = Math.min(minY, n.y);
        maxY = Math.max(maxY, n.y);
    });

    const graphWidth = maxX - minX;
    const graphHeight = maxY - minY;

    console.log('Graph bounds: minX=' + minX + ', maxX=' + maxX + ', width=' + graphWidth);

    // Scale and center the graph to fit canvas with padding
    const padding = nodeCount > 50 ? 50 : 55;
    const availableWidth = W - (2 * padding);
    const availableHeight = H - (2 * padding);

    const scaleX = graphWidth > 0 ? availableWidth / graphWidth : 1;
    const scaleY = graphHeight > 0 ? availableHeight / graphHeight : 1;
    const scale = Math.min(scaleX, scaleY, 1.2);

    console.log('Scale: ' + scale.toFixed(3) + ' (scaleX=' + scaleX.toFixed(3) + ', scaleY=' + scaleY.toFixed(3) + ')');

    // Transform all positions
    stablePositions = {};
    nodes.forEach(function(n) {
        const scaledX = (n.x - minX) * scale;
        const scaledY = (n.y - minY) * scale;
        
        const offsetX = (W - (graphWidth * scale)) / 2;
        const offsetY = (H - (graphHeight * scale)) / 2;
        
        stablePositions[n.id] = {
            x: scaledX + offsetX,
            y: scaledY + offsetY
        };
    });

    // Verify and clamp if needed
    var outOfBounds = 0;
    for (var id in stablePositions) {
        var pos = stablePositions[id];
        if (pos.x < padding || pos.x > W - padding || pos.y < padding || pos.y > H - padding) {
            outOfBounds++;
        }
    }

    if (outOfBounds > 0) {
        console.warn(outOfBounds + ' nodes outside bounds, clamping...');
        for (var id in stablePositions) {
            stablePositions[id].x = Math.max(padding, Math.min(W - padding, stablePositions[id].x));
            stablePositions[id].y = Math.max(padding, Math.min(H - padding, stablePositions[id].y));
        }
    }

    console.log('Layout ready: ' + Object.keys(stablePositions).length + ' nodes, all within bounds');
    callback();
}

// ============================================================================
// CONTROLS
// ============================================================================

function setupControls() {
    document.getElementById('playBtn').addEventListener('click', play);
    document.getElementById('pauseBtn').addEventListener('click', pause);
    document.getElementById('resetBtn').addEventListener('click', reset);
    
    // Edge visibility toggle
    var edgesVisible = true;
    document.getElementById('toggleEdgesBtn').addEventListener('click', function() {
        edgesVisible = !edgesVisible;
        var edgeLayer = document.querySelector('.edge-layer');
        if (edgeLayer) {
            edgeLayer.style.display = edgesVisible ? 'block' : 'none';
        }
        this.style.background = edgesVisible ? '#16a085' : '#95a5a6';
        this.innerHTML = edgesVisible ? '<i class="fas fa-project-diagram"></i> Edges' : '<i class="fas fa-project-diagram"></i> Edges';
    });

    document.getElementById('speedSlider').addEventListener('input', function(e) {
        animationSpeed = parseInt(e.target.value);
        document.getElementById('speedValue').textContent = (animationSpeed / 1000).toFixed(1) + 's';
        if (isPlaying) { pause(); play(); }
    });
}

function play() {
    if (isPlaying) return;

    // If at the end, wrap back to start
    if (currentStep >= animationData.history.length - 1) {
        currentStep = 0;
        hideCompletionBanner();
    }

    isPlaying = true;
    document.getElementById('playBtn').style.display = 'none';
    document.getElementById('pauseBtn').style.display = 'inline-block';

    animationInterval = setInterval(function() {
        if (currentStep < animationData.history.length - 1) {
            currentStep++;
            renderStep(currentStep);
        } else {
            // End reached: STOP but keep final state visible
            pause();
            showCompletionBanner();
        }
    }, animationSpeed);
}

function pause() {
    isPlaying = false;
    document.getElementById('playBtn').style.display = 'inline-block';
    document.getElementById('pauseBtn').style.display = 'none';
    if (animationInterval) {
        clearInterval(animationInterval);
        animationInterval = null;
    }
}

function reset() {
    pause();
    hideCompletionBanner();
    currentStep = 0;
    renderStep(0);
}

function showCompletionBanner() {
    var banner = document.getElementById('completionBanner');
    if (banner) { banner.style.display = 'flex'; return; }
    
    // Get final statistics
    var totalNodes = animationData.graph.nodes.length;
    var finalStep = animationData.history[animationData.history.length - 1];
    var totalColors = finalStep.colored ? Math.max.apply(null, Object.values(finalStep.colored).concat([0])) : 0;
    var totalColored = Object.keys(finalStep.colored || {}).length;
    
    banner = document.createElement('div');
    banner.id = 'completionBanner';
    banner.style.cssText = [
        'position:absolute','top:12px','left:50%','transform:translateX(-50%)',
        'background:linear-gradient(135deg,#2ecc71,#27ae60)',
        'color:white','padding:12px 24px','border-radius:50px',
        'font-weight:700','font-size:0.9rem','z-index:999',
        'box-shadow:0 4px 20px rgba(46,204,113,0.45)',
        'display:flex','align-items:center','gap:12px','white-space:nowrap'
    ].join(';');
    
    var statusMsg = totalColored === totalNodes 
        ? '✓ All ' + totalNodes + ' tasks scheduled in ' + totalColors + ' time slots' 
        : '⚠ Only ' + totalColored + '/' + totalNodes + ' tasks colored';
    
    banner.innerHTML = '<i class="fas fa-check-circle"></i>' + statusMsg + 
        '<span style="opacity:0.85;font-size:0.8rem;margin-left:8px;border-left:2px solid rgba(255,255,255,0.4);padding-left:12px">Click Reset to replay</span>';
    
    var canvas = document.getElementById('graphCanvas');
    canvas.style.position = 'relative';
    canvas.prepend(banner);
    
    console.log('Completion:', totalColored, '/', totalNodes, 'nodes colored in', totalColors, 'colors');
}

function hideCompletionBanner() {
    var banner = document.getElementById('completionBanner');
    if (banner) banner.style.display = 'none';
}

// ============================================================================
// RENDER STEP — updates description, panels, and graph
// ============================================================================

function renderStep(stepIndex) {
    var step = animationData.history[stepIndex];
    document.getElementById('currentStep').textContent = stepIndex + 1;

    // Color-coded step description bar
    var descEl = document.getElementById('stepDescription');
    descEl.textContent = step.description;

    if (step.description.indexOf('Initial') !== -1) {
        descEl.style.background = '#f8f9fa'; descEl.style.borderLeftColor = '#95a5a6'; descEl.style.color = '#2c3e50';
    } else if (step.description.indexOf('random priorities') !== -1) {
        descEl.style.background = '#ebf5fb'; descEl.style.borderLeftColor = '#3498db'; descEl.style.color = '#1a5276';
    } else if (step.description.indexOf('Select') !== -1) {
        descEl.style.background = '#eafaf1'; descEl.style.borderLeftColor = '#2ecc71'; descEl.style.color = '#1e8449';
    } else if (step.description.indexOf('Assign color') !== -1) {
        descEl.style.background = '#f5eef8'; descEl.style.borderLeftColor = '#9b59b6'; descEl.style.color = '#6c3483';
    } else if (step.description.indexOf('Remove') !== -1) {
        descEl.style.background = '#fdedec'; descEl.style.borderLeftColor = '#e74c3c'; descEl.style.color = '#922b21';
    } else if (step.description.indexOf('Complete') !== -1) {
        descEl.style.background = '#eafaf1'; descEl.style.borderLeftColor = '#27ae60'; descEl.style.color = '#1e8449';
    }

    updateStatusPanel(step);
    updateSlotsPanel(step);
    renderGraph(step);
}

// ============================================================================
// STATUS + SLOTS PANELS
// ============================================================================

function updateStatusPanel(step) {
    document.getElementById('activeTasks').textContent   = step.active.length;
    document.getElementById('coloredTasks').textContent  = Object.keys(step.colored).length;
    document.getElementById('selectedTasks').textContent = step.selected.length;
    document.getElementById('removedTasks').textContent  = step.removed.length;
    
    var vals = Object.values(step.colored);
    var maxColor = vals.length > 0 ? Math.max.apply(null, vals) : 0;
    document.getElementById('currentColor').textContent = maxColor > 0 ? 'Slot ' + maxColor : '—';
    
    // Calculate max degree (delta)
    if (!window.graphMaxDegree) {
        var degrees = {};
        animationData.graph.edges.forEach(function(e) {
            var src = (typeof e.source === 'object') ? e.source.id : e.source;
            var tgt = (typeof e.target === 'object') ? e.target.id : e.target;
            degrees[src] = (degrees[src] || 0) + 1;
            degrees[tgt] = (degrees[tgt] || 0) + 1;
        });
        window.graphMaxDegree = Math.max.apply(null, Object.values(degrees).concat([0]));
    }
    document.getElementById('maxDegree').textContent = window.graphMaxDegree;
    
    // Total colors used (chromatic number)
    var totalColors = vals.length > 0 ? Math.max.apply(null, vals) : 0;
    document.getElementById('chromaticNumber').textContent = totalColors > 0 ? totalColors : '—';
}

function updateSlotsPanel(step) {
    var slotsDiv = document.getElementById('slotAssignments');
    if (Object.keys(step.colored).length === 0) {
        slotsDiv.innerHTML = '<p class="text-muted fst-italic" style="font-size:0.9rem;">No assignments yet...</p>';
        return;
    }

    var slotGroups = {};
    for (var node in step.colored) {
        var color = step.colored[node];
        if (!slotGroups[color]) slotGroups[color] = [];
        slotGroups[color].push('T' + node);
    }

    var html = '';
    Object.keys(slotGroups).sort(function(a,b){return a-b;}).forEach(function(slot) {
        var bg = getSlotColor(parseInt(slot));  // Use dynamic color function
        html += '<div class="slot-item" style="border-left-color:' + bg + ';margin-bottom:8px;">' +
            '<div class="slot-number" style="color:' + bg + ';font-weight:700;font-size:0.85rem;">' +
            '<i class="fas fa-circle" style="font-size:0.5rem;margin-right:4px;"></i>Time Slot ' + slot + '</div>' +
            '<div class="slot-tasks" style="color:#555;font-size:0.82rem;margin-top:3px;">' + slotGroups[slot].join(' &middot; ') + '</div>' +
            '</div>';
    });
    slotsDiv.innerHTML = html;
}

// ============================================================================
// RENDER GRAPH — stable positions, clear visual states
// ============================================================================

function renderGraph(step) {
    if (!stablePositions) return;

    var canvas = document.getElementById('graphCanvas');
    var W = canvas.clientWidth || 800;
    var H = 560;

    var svg = d3.select('#graphSvg');
    svg.selectAll('*').remove();
    svg.attr('width', W).attr('height', H).attr('viewBox', '0 0 ' + W + ' ' + H);

    var nodes = animationData.graph.nodes;
    var edges = animationData.graph.edges;

    console.log('Rendering:', nodes.length, 'nodes,', edges.length, 'edges');

    // ── Draw edges FIRST (below nodes) ──────────────────────────
    var edgeG = svg.append('g')
        .attr('class', 'edge-layer')
        .attr('id', 'edge-layer-group');
    
    var edgesDrawn = 0;
    var edgesFailed = 0;
    
    edges.forEach(function(e) {
        var srcId = (typeof e.source === 'object') ? e.source.id : e.source;
        var tgtId = (typeof e.target === 'object') ? e.target.id : e.target;
        var src = stablePositions[srcId];
        var tgt = stablePositions[tgtId];
        
        if (!src || !tgt) {
            console.warn('Missing position for edge:', srcId, '->', tgtId);
            edgesFailed++;
            return;
        }
        
        // Verify coordinates are valid numbers
        if (isNaN(src.x) || isNaN(src.y) || isNaN(tgt.x) || isNaN(tgt.y)) {
            console.error('Invalid coordinates for edge', srcId, '->', tgtId, src, tgt);
            edgesFailed++;
            return;
        }

        var srcSel = step.selected.indexOf(srcId) !== -1;
        var tgtSel = step.selected.indexOf(tgtId) !== -1;
        var srcRem = step.removed.indexOf(srcId) !== -1;
        var tgtRem = step.removed.indexOf(tgtId) !== -1;
        var isConflict = (srcSel && tgtRem) || (tgtSel && srcRem);

        // VERY VISIBLE edges - almost black, thick lines
        var strokeColor = isConflict ? '#e74c3c' : '#000000';  // BLACK for normal edges!
        var strokeWidth = isConflict ? 5 : 3;
        var opacity = 1.0;

        var line = edgeG.append('line')
            .attr('x1', src.x)
            .attr('y1', src.y)
            .attr('x2', tgt.x)
            .attr('y2', tgt.y)
            .attr('stroke', strokeColor)
            .attr('stroke-width', strokeWidth)
            .attr('stroke-dasharray', isConflict ? '8,4' : null)
            .attr('opacity', opacity)
            .attr('stroke-linecap', 'round')
            .attr('class', 'graph-edge');
        
        edgesDrawn++;
    });
    
    console.log('Drew', edgesDrawn, 'edges successfully,', edgesFailed, 'failed');

    // ── Draw nodes SECOND (on top) ───────────────────────────────────────────────
    var nodeG = svg.append('g')
        .attr('class', 'node-layer')
        .attr('id', 'node-layer-group');
    nodes.forEach(function(n) {
        var pos = stablePositions[n.id];
        if (!pos) return;

        var isSel   = step.selected.indexOf(n.id) !== -1;
        var isRem   = step.removed.indexOf(n.id) !== -1;
        var slot    = step.colored[n.id] !== undefined ? step.colored[n.id] : step.colored[String(n.id)];
        var isAct   = step.active.indexOf(n.id) !== -1;

        var fillColor, strokeColor, strokeW, textColor, opacity;

        if (isSel) {
            fillColor = '#2ecc71'; strokeColor = '#f39c12'; strokeW = 4; textColor = 'white'; opacity = 1;
        } else if (isRem && !slot) {
            fillColor = '#e74c3c'; strokeColor = '#c0392b'; strokeW = 3; textColor = 'white'; opacity = 0.85;
        } else if (slot !== undefined && slot !== null) {
            fillColor = getSlotColor(slot);  // Use dynamic color function
            strokeColor = '#2c3e50'; strokeW = 3; textColor = 'white'; opacity = 1;
        } else if (isAct) {
            fillColor = '#f0f3f4'; strokeColor = '#7f8c8d'; strokeW = 2; textColor = '#2c3e50'; opacity = 1;
        } else {
            // This shouldn't happen - all nodes should be active, colored, selected, or removed
            fillColor = '#ecf0f1'; strokeColor = '#95a5a6'; strokeW = 2; textColor = '#7f8c8d'; opacity = 0.6;
            console.warn('Node', n.id, 'in undefined state! slot:', slot, 'active:', isAct, 'selected:', isSel, 'removed:', isRem);
        }

        var g = nodeG.append('g').attr('transform', 'translate(' + pos.x + ',' + pos.y + ')').attr('opacity', opacity);

        // Pulse ring for selected - smaller
        if (isSel) {
            g.append('circle').attr('r', 24).attr('fill','none').attr('stroke','#f39c12').attr('stroke-width',2).attr('stroke-dasharray','5,3').attr('opacity',0.6);
        }

        // Main node circle - SMALLER (18 instead of 26)
        g.append('circle').attr('r', 18).attr('fill', fillColor).attr('stroke', strokeColor).attr('stroke-width', strokeW);

        // Task label inside node - smaller font to fit
        g.append('text')
            .attr('text-anchor','middle').attr('dy','0.35em')
            .attr('font-size', nodes.length > 50 ? 8 : nodes.length > 30 ? 9 : 10)
            .attr('font-weight','bold').attr('fill',textColor).attr('pointer-events','none')
            .text('T' + n.id);

        // Small slot badge top-right - adjusted position for smaller node
        if (slot !== undefined && slot !== null) {
            var badgeColor = getSlotColor(slot);
            g.append('circle').attr('cx',13).attr('cy',-13).attr('r',8).attr('fill',badgeColor).attr('stroke','white').attr('stroke-width',1.5);
            g.append('text').attr('x',13).attr('y',-10).attr('text-anchor','middle').attr('font-size',7).attr('font-weight','bold').attr('fill','white').attr('pointer-events','none').text(slot);
        }

        // Random priority pill above node - smaller
        var rv = step.random_values[n.id] !== undefined ? step.random_values[n.id] : step.random_values[String(n.id)];
        if (rv !== undefined && isAct) {
            g.append('rect').attr('x',-16).attr('y',-38).attr('width',32).attr('height',13).attr('rx',4).attr('fill','#e74c3c').attr('opacity',0.92);
            g.append('text').attr('text-anchor','middle').attr('dy',-29).attr('font-size',8).attr('font-weight','bold').attr('fill','white').attr('pointer-events','none').text(rv.toFixed(2));
        }

        // Tooltip
        g.append('title').text(
            slot !== undefined ? 'Task ' + n.id + ' → Time Slot ' + slot :
            isSel ? 'Task ' + n.id + ' — Selected (MIS)' :
            isRem ? 'Task ' + n.id + ' — Removed (conflict)' :
            'Task ' + n.id + ' — Waiting'
        );
    });
}