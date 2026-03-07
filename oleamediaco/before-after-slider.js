(function () {
  var sliders = document.querySelectorAll('[data-compare-slider]');
  if (!sliders.length) return;

  sliders.forEach(function (slider) {
    var range = slider.querySelector('input[type="range"]');
    if (!range) return;
    var min = Number(range.min || 0);
    var max = Number(range.max || 100);
    var autoStart = 10;
    var autoEnd = 90;
    var autoEnabled = true;
    var rafId = 0;
    var lastTs = 0;
    var durationSeconds = 3;
    var speedPerSecond = (autoEnd - autoStart) / durationSeconds; // 10% -> 90% in ~3s

    function clamp(v, lo, hi) {
      return Math.min(hi, Math.max(lo, v));
    }

    function updateSplit() {
      slider.style.setProperty('--split', range.value + '%');
    }

    function stopAuto() {
      autoEnabled = false;
      if (rafId) {
        cancelAnimationFrame(rafId);
        rafId = 0;
      }
    }

    function autoTick(ts) {
      if (!autoEnabled) return;
      if (!lastTs) lastTs = ts;
      var dt = (ts - lastTs) / 1000;
      lastTs = ts;

      var next = clamp(Number(range.value) + speedPerSecond * dt, autoStart, autoEnd);
      range.value = String(next);
      updateSplit();

      if (next >= autoEnd) {
        stopAuto();
        return;
      }
      rafId = requestAnimationFrame(autoTick);
    }

    // Start near the left edge and animate to near the right edge once.
    range.value = String(clamp(autoStart, min, max));
    updateSplit();
    range.addEventListener('input', updateSplit);
    range.addEventListener('change', updateSplit);

    // Stop only when user explicitly interacts with the photo slider area.
    slider.addEventListener('pointerdown', stopAuto, { passive: true });
    slider.addEventListener('touchstart', stopAuto, { passive: true });
    slider.addEventListener('mousedown', stopAuto, { passive: true });
    slider.addEventListener('click', stopAuto, { passive: true });

    if (autoEnabled) {
      rafId = requestAnimationFrame(autoTick);
    }
  });
})();
