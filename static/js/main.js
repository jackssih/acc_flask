// Auto-dismiss flash messages after 5 seconds
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.flash').forEach(el => {
    setTimeout(() => el.style.opacity = '0', 4500);
    setTimeout(() => el.remove(), 5000);
  });
});
