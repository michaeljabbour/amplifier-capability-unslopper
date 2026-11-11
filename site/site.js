'use strict';
/* Progressive enhancement only: copy buttons. Every link, download and frame works without this file. */
document.documentElement.classList.add('js');
for (const button of document.querySelectorAll('[data-copy]')) {
  button.addEventListener('click', async () => {
    const source = document.getElementById(button.dataset.copy);
    const status = button.parentElement.querySelector('[role="status"]');
    try {
      if (!navigator.clipboard || !window.isSecureContext) throw new Error('Clipboard unavailable');
      await navigator.clipboard.writeText(source.textContent);
      status.textContent = 'Copied.';
    } catch (_) {
      const range = document.createRange();
      range.selectNodeContents(source);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      status.textContent = 'Text selected. Use your device’s copy command.';
    }
  });
}
