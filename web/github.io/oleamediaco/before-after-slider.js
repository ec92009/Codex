(function () {
  var sliders = document.querySelectorAll('[data-compare-slider]');
  if (!sliders.length) return;

  sliders.forEach(function (slider) {
    var range = slider.querySelector('input[type="range"]');
    if (!range) return;

    function updateSplit() {
      slider.style.setProperty('--split', range.value + '%');
    }

    updateSplit();
    range.addEventListener('input', updateSplit);
    range.addEventListener('change', updateSplit);
  });
})();
