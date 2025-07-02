document.addEventListener('DOMContentLoaded', () => {
    const track = document.getElementById('carouselTrack');
    const leftZone = document.getElementById('leftZone');
    const rightZone = document.getElementById('rightZone');

    const animation = track.animate([
        { transform: 'translateX(0%)' },
        { transform: 'translateX(-50%)' }
    ], {
        duration: 36000,
        iterations: Infinity,
        easing: 'linear'
    });

    const setSpeed = (factor) => {
        animation.playbackRate = factor;
    };
    const speedMultiplier = 6;
    leftZone.addEventListener('mouseenter', () => setSpeed(-speedMultiplier)); // slower
    rightZone.addEventListener('mouseenter', () => setSpeed(speedMultiplier)); // faster
    leftZone.addEventListener('mouseleave', () => setSpeed(1));   // normal
    rightZone.addEventListener('mouseleave', () => setSpeed(1));  // normal

    // Touch support
    leftZone.addEventListener('touchstart', () => setSpeed(-speedMultiplier), { passive: true });
    rightZone.addEventListener('touchstart', () => setSpeed(speedMultiplier), { passive: true });
    leftZone.addEventListener('touchend', () => setSpeed(1));
    rightZone.addEventListener('touchend', () => setSpeed(1));
});
