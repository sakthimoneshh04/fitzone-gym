document.addEventListener('DOMContentLoaded', function () {
	var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

	// Reveal existing content as it enters the viewport without moving layout.
	var revealItems = document.querySelectorAll(
		'[data-reveal], .page-section, .section, .program-card, .join-section, .role-box, .dashboard-card'
	);

	if ('IntersectionObserver' in window) {
		var revealObserver = new IntersectionObserver(function (entries, observer) {
			entries.forEach(function (entry) {
				if (entry.isIntersecting) {
					entry.target.classList.add('is-visible');
					observer.unobserve(entry.target);
				}
			});
		}, { threshold: 0.14 });

		revealItems.forEach(function (item, index) {
			item.classList.add('reveal-item');
			item.style.setProperty('--reveal-delay', (index % 4) * 70 + 'ms');
			revealObserver.observe(item);
		});
	} else {
		revealItems.forEach(function (item) {
			item.classList.add('is-visible');
		});
	}

	document.querySelectorAll('[data-slider]').forEach(function (slider) {
		var slides = slider.querySelectorAll('.slider-slide');
		var dots = slider.querySelectorAll('[data-slide-to]');
		var currentSlide = 0;
		var timer;

		if (slides.length < 2) {
			return;
		}

		function showSlide(nextSlide) {
			currentSlide = (nextSlide + slides.length) % slides.length;
			slides.forEach(function (slide, index) {
				slide.classList.toggle('is-active', index === currentSlide);
				slide.setAttribute('aria-hidden', index === currentSlide ? 'false' : 'true');
			});
			dots.forEach(function (dot, index) {
				dot.classList.toggle('is-active', index === currentSlide);
				dot.setAttribute('aria-current', index === currentSlide ? 'true' : 'false');
			});
		}

		function startSlider() {
			if (!prefersReducedMotion) {
				timer = window.setInterval(function () {
					showSlide(currentSlide + 1);
				}, 5000);
			}
		}

		function stopSlider() {
			window.clearInterval(timer);
		}

		dots.forEach(function (dot) {
			dot.addEventListener('click', function () {
				showSlide(Number(dot.getAttribute('data-slide-to')));
				stopSlider();
				startSlider();
			});
		});

		slider.addEventListener('mouseenter', stopSlider);
		slider.addEventListener('mouseleave', startSlider);
		slider.addEventListener('focusin', stopSlider);
		slider.addEventListener('focusout', startSlider);
		showSlide(0);
		startSlider();
	});
});
