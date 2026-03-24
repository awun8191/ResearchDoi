import React, { useRef, useEffect } from 'react';

export default function ParticleBackground({ particleColor = 'rgba(255, 255, 255, 0.75)', backgroundColor = '#050505' }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d', { alpha: false });
    let animationFrameId;

    const resolveColor = (color) => {
      if (color && color.startsWith('var(')) {
        const varName = color.slice(4, -1);
        return getComputedStyle(document.documentElement).getPropertyValue(varName).trim() || '#000';
      }
      return color;
    };

    const parseBaseAlpha = (color) => {
      if (typeof color !== 'string') return 1;
      if (color.startsWith('rgba(')) {
        const parts = color.slice(5, -1).split(',');
        return Math.min(1, Math.max(0, parseFloat(parts[3] ?? '1')));
      }
      return 1;
    };

    const normalize3 = (v) => {
      const len = Math.hypot(v.x, v.y, v.z) || 1;
      return { x: v.x / len, y: v.y / len, z: v.z / len };
    };

    const cross3 = (a, b) => ({
      x: a.y * b.z - a.z * b.y,
      y: a.z * b.x - a.x * b.z,
      z: a.x * b.y - a.y * b.x
    });

    let activeBg = resolveColor(backgroundColor);
    let activeParticle = resolveColor(particleColor);
    let baseAlpha = parseBaseAlpha(activeParticle);

    let width = Math.max(1, canvas.parentElement.clientWidth);
    let height = Math.max(1, canvas.parentElement.clientHeight);
    canvas.width = width;
    canvas.height = height;

    const resize = () => {
      width = Math.max(1, canvas.parentElement.clientWidth);
      height = Math.max(1, canvas.parentElement.clientHeight);
      canvas.width = width;
      canvas.height = height;
      activeBg = resolveColor(backgroundColor);
      activeParticle = resolveColor(particleColor);
      baseAlpha = parseBaseAlpha(activeParticle);
    };

    window.addEventListener('resize', resize);

    const pointCount = 2600;
    const majorRadius = 1.0;
    const minorRadius = 0.42;
    const points = [];

    for (let i = 0; i < pointCount; i += 1) {
      const u = ((i / pointCount) * Math.PI * 2 * 21) % (Math.PI * 2);
      const v = (((i * 0.61803398875) % 1) * Math.PI * 2);
      const cosU = Math.cos(u);
      const sinU = Math.sin(u);
      const cosV = Math.cos(v);
      const sinV = Math.sin(v);

      const ring = majorRadius + minorRadius * cosV;

      points.push({
        x: ring * cosU,
        y: minorRadius * sinV,
        z: ring * sinU,
        nx: cosU * cosV,
        ny: sinV,
        nz: sinU * cosV,
        jitter: Math.random() * Math.PI * 2
      });
    }

    const ripples = [];
    const hoverThreshold = 68;
    const emitEveryMs = 105;
    let lastEmit = 0;

    let mouseX = width * 0.5;
    let mouseY = height * 0.5;
    let targetMouseX = mouseX;
    let targetMouseY = mouseY;
    let mouseActive = false;
    let isDragging = false;
    let dragPointerId = null;
    let lastDragX = 0;
    let lastDragY = 0;
    let manualYaw = 0;
    let manualPitch = 0;
    let dragVelocityYaw = 0;
    let dragVelocityPitch = 0;
    let lastDragTs = 0;
    let dragSpeedSmoothed = 0;

    const getRelativePointer = (e) => {
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const inside = e.clientX >= rect.left && e.clientX <= rect.right && e.clientY >= rect.top && e.clientY <= rect.bottom;
      return { x, y, inside };
    };

    const onPointerMove = (e) => {
      const p = getRelativePointer(e);
      targetMouseX = p.x;
      targetMouseY = p.y;
      mouseActive = p.inside;

      if (!isDragging || e.pointerId !== dragPointerId) return;

      const dx = p.x - lastDragX;
      const dy = p.y - lastDragY;
      const nowTs = typeof e.timeStamp === 'number' ? e.timeStamp : performance.now();
      const dtMove = Math.max(0.008, Math.min(0.05, (nowTs - lastDragTs) / 1000 || 0.016));
      lastDragX = p.x;
      lastDragY = p.y;
      lastDragTs = nowTs;

      manualYaw += dx * 0.006;
      manualPitch += dy * 0.0045;
      manualPitch = Math.max(-1.1, Math.min(1.1, manualPitch));

      const speed = Math.hypot(dx, dy) / dtMove;
      dragSpeedSmoothed += (speed - dragSpeedSmoothed) * 0.28;
      const momentumScale = Math.min(1.85, Math.max(0.5, dragSpeedSmoothed / 850));
      const targetVelYaw = (dx / dtMove) * 0.0000088 * momentumScale;
      const targetVelPitch = (dy / dtMove) * 0.0000068 * momentumScale;
      dragVelocityYaw += (targetVelYaw - dragVelocityYaw) * 0.42;
      dragVelocityPitch += (targetVelPitch - dragVelocityPitch) * 0.42;
    };

    const onPointerLeave = () => {
      mouseActive = false;
      targetMouseX = width * 0.5;
      targetMouseY = height * 0.5;
    };

    const onPointerDown = (e) => {
      const p = getRelativePointer(e);
      if (!p.inside) return;
      isDragging = true;
      dragPointerId = e.pointerId;
      lastDragX = p.x;
      lastDragY = p.y;
      dragVelocityYaw = 0;
      dragVelocityPitch = 0;
      dragSpeedSmoothed = 0;
      lastDragTs = typeof e.timeStamp === 'number' ? e.timeStamp : performance.now();
      mouseActive = true;
      canvas.style.cursor = 'grabbing';
      if (canvas.setPointerCapture) {
        canvas.setPointerCapture(e.pointerId);
      }
    };

    const onPointerUp = (e) => {
      if (!isDragging || e.pointerId !== dragPointerId) return;
      isDragging = false;
      dragPointerId = null;
      const releaseBoost = Math.min(1.35, 0.75 + dragSpeedSmoothed / 1200);
      dragVelocityYaw = Math.max(-0.06, Math.min(0.06, dragVelocityYaw * releaseBoost));
      dragVelocityPitch = Math.max(-0.045, Math.min(0.045, dragVelocityPitch * releaseBoost));
      canvas.style.cursor = 'grab';
      if (canvas.releasePointerCapture) {
        try {
          canvas.releasePointerCapture(e.pointerId);
        } catch (_) {
          // Ignore pointer capture errors from stale ids.
        }
      }
    };

    canvas.style.cursor = 'grab';
    canvas.style.touchAction = 'none';
    canvas.addEventListener('pointerdown', onPointerDown);
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerleave', onPointerLeave);
    window.addEventListener('mouseout', onPointerLeave);
    window.addEventListener('pointerup', onPointerUp);
    window.addEventListener('pointercancel', onPointerUp);

    const rotateY = (v, a) => {
      const c = Math.cos(a);
      const s = Math.sin(a);
      return { x: v.x * c - v.z * s, y: v.y, z: v.x * s + v.z * c };
    };

    const rotateX = (v, a) => {
      const c = Math.cos(a);
      const s = Math.sin(a);
      return { x: v.x, y: v.y * c - v.z * s, z: v.y * s + v.z * c };
    };

    const rotateZ = (v, a) => {
      const c = Math.cos(a);
      const s = Math.sin(a);
      return { x: v.x * c - v.y * s, y: v.x * s + v.y * c, z: v.z };
    };

    let time = 0;
    let lastFrameMs = performance.now();
    let velocityX = 0;
    let velocityY = 0;

    const animate = () => {
      ctx.fillStyle = activeBg;
      ctx.fillRect(0, 0, width, height);

      const now = performance.now();
      const dt = Math.min(0.04, (now - lastFrameMs) / 1000);
      lastFrameMs = now;
      time += dt;

      const cx = width * 0.5;
      const cy = height * 0.5;
      const sphereRadius = Math.min(width, height) * 0.72;
      const cameraZ = sphereRadius * 4.2;
      const perspective = sphereRadius * 1.8;

      const baseYawY = -0.78;
      const baseTiltX = -0.48;
      const baseRollZ = -0.62;
      if (!isDragging) {
        manualYaw += dragVelocityYaw;
        manualPitch += dragVelocityPitch;
        dragVelocityYaw *= 0.93;
        dragVelocityPitch *= 0.9;
      }
      manualPitch = Math.max(-1.1, Math.min(1.1, manualPitch));

      const orbitY = baseYawY + time * 0.18 + manualYaw;
      const orbitX = baseTiltX + Math.sin(time * 0.2) * 0.06 + manualPitch;
      const orbitZ = baseRollZ + Math.sin(time * 0.16) * 0.04;

      const prevMouseX = mouseX;
      const prevMouseY = mouseY;
      mouseX += (targetMouseX - mouseX) * 0.12;
      mouseY += (targetMouseY - mouseY) * 0.12;
      const instVelX = (mouseX - prevMouseX) / Math.max(dt, 0.0001);
      const instVelY = (mouseY - prevMouseY) / Math.max(dt, 0.0001);
      velocityX += (instVelX - velocityX) * 0.22;
      velocityY += (instVelY - velocityY) * 0.22;

      const mouseRotY = 0;
      const mouseRotX = 0;

      const projected = [];
      let nearestModelPoint = null;
      let nearestModelNormal = null;
      let nearestDistSq = Infinity;

      for (let i = 0; i < points.length; i += 1) {
        const p = points[i];

        const pulse = Math.sin(time * 2.1 + p.jitter) * 0.018;
        const base = {
          x: p.x + p.nx * pulse,
          y: p.y + p.ny * pulse,
          z: p.z + p.nz * pulse
        };

        let normalPush = 0;
        let flowPush = { x: 0, y: 0, z: 0 };

        for (let r = 0; r < ripples.length; r += 1) {
          const rp = ripples[r];
          const age = (time - rp.start) * 2.0;
          if (age > 2.2) continue;

          const dx = base.x - rp.cx;
          const dy = base.y - rp.cy;
          const dz = base.z - rp.cz;
          const dist = Math.hypot(dx, dy, dz);
          if (dist > 0.9) continue;

          const invDist = 1 / Math.max(dist, 0.0001);
          const dirNorm = { x: dx * invDist, y: dy * invDist, z: dz * invDist };
          const dirFactor = dirNorm.x * rp.dx + dirNorm.y * rp.dy + dirNorm.z * rp.dz;

          const waveFront = age * (0.17 + 0.08 * Math.max(0, dirFactor));
          const ring = Math.sin((dist - waveFront) * 20);
          const falloff = Math.exp(-Math.pow((dist - waveFront) * 6.8, 2));
          const localMask = Math.exp(-Math.pow(dist * 6.2, 2));
          const directionalBias = 0.8 + 0.35 * Math.max(0, dirFactor);
          const impact = ring * falloff * (1.18 - age * 0.17) * directionalBias;

          normalPush += impact * localMask * 0.14;
          flowPush.x += dx * impact * localMask * 0.028;
          flowPush.y += dy * impact * localMask * 0.028;
          flowPush.z += dz * impact * localMask * 0.028;
        }

        const displaced = {
          x: base.x + p.nx * normalPush + flowPush.x,
          y: base.y + p.ny * normalPush + flowPush.y,
          z: base.z + p.nz * normalPush + flowPush.z
        };

        let rotated = rotateY(displaced, orbitY + mouseRotY);
        rotated = rotateX(rotated, orbitX + mouseRotX);
        rotated = rotateZ(rotated, orbitZ);

        const worldX = rotated.x * sphereRadius;
        const worldY = rotated.y * sphereRadius;
        const worldZ = rotated.z * sphereRadius;

        const z = worldZ + cameraZ;
        if (z <= 0) continue;

        const scale = perspective / z;
        const sx = cx + worldX * scale;
        const sy = cy + worldY * scale;

        const depth = (worldZ / sphereRadius + 1) * 0.5;
        const radius = Math.max(0.8, 2.4 * scale + depth * 0.45);

        if (mouseActive) {
          const px = sx - mouseX;
          const py = sy - mouseY;
          const distSq = px * px + py * py;
          if (distSq < nearestDistSq) {
            nearestDistSq = distSq;
            nearestModelPoint = base;
            nearestModelNormal = { x: p.nx, y: p.ny, z: p.nz };
          }
        }

        projected.push({ sx, sy, radius, depth });
      }

      if (mouseActive && !isDragging && nearestModelPoint && nearestModelNormal && nearestDistSq < hoverThreshold * hoverThreshold) {
        const nowMs = performance.now();
        if (nowMs - lastEmit >= emitEveryMs) {
          lastEmit = nowMs;

          const speed = Math.hypot(velocityX, velocityY);
          const dir2x = speed > 5 ? velocityX / speed : 1;
          const dir2y = speed > 5 ? velocityY / speed : 0;

          const normal = normalize3(nearestModelNormal);
          const up = Math.abs(normal.y) > 0.92 ? { x: 1, y: 0, z: 0 } : { x: 0, y: 1, z: 0 };
          const t1 = normalize3(cross3(up, normal));
          const t2 = normalize3(cross3(normal, t1));
          const dir3 = normalize3({
            x: t1.x * dir2x + t2.x * dir2y,
            y: t1.y * dir2x + t2.y * dir2y,
            z: t1.z * dir2x + t2.z * dir2y
          });

          ripples.push({
            cx: nearestModelPoint.x,
            cy: nearestModelPoint.y,
            cz: nearestModelPoint.z,
            dx: dir3.x,
            dy: dir3.y,
            dz: dir3.z,
            start: time
          });
        }
      }

      while (ripples.length > 0 && time - ripples[0].start > 1.45) {
        ripples.shift();
      }

      projected.sort((a, b) => a.depth - b.depth);
      ctx.fillStyle = activeParticle;

      for (let i = 0; i < projected.length; i += 1) {
        const p = projected[i];
        const alpha = Math.max(0.08, Math.min(1, baseAlpha * (0.38 + p.depth * 0.85)));
        ctx.globalAlpha = alpha;
        ctx.beginPath();
        ctx.arc(p.sx, p.sy, p.radius, 0, Math.PI * 2);
        ctx.fill();
      }

      ctx.globalAlpha = 1;
      animationFrameId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      canvas.removeEventListener('pointerdown', onPointerDown);
      window.removeEventListener('resize', resize);
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerleave', onPointerLeave);
      window.removeEventListener('mouseout', onPointerLeave);
      window.removeEventListener('pointerup', onPointerUp);
      window.removeEventListener('pointercancel', onPointerUp);
      cancelAnimationFrame(animationFrameId);
    };
  }, [particleColor, backgroundColor]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        display: 'block',
        width: '100%',
        height: '100%'
      }}
    />
  );
}
