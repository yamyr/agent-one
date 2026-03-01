<script setup>
/**
 * FooterSection — Minimal branded footer with three-column layout.
 *
 * Left: built-with attribution, Center: hackathon label, Right: copyright.
 * Collapses to stacked layout on mobile.
 */
</script>

<template>
  <footer class="footer">
    <div class="footer__inner">
      <span class="footer__built">{{ $t('footer.built_with') }}</span>
      <span class="footer__hackathon">{{ $t('footer.hackathon') }}</span>
      <span class="footer__copyright">{{ $t('footer.copyright') }}</span>
    </div>
  </footer>
</template>

<style scoped>
.footer {
  padding: 3rem 5%;
  border-top: 1px solid var(--glass-border);
}

.footer__inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.footer__built {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.footer__hackathon {
  font-size: 0.75rem;
  color: var(--text-dim);
}

.footer__copyright {
  font-size: 0.75rem;
  color: var(--text-dim);
}

/* ─── Responsive ─── */

@media (max-width: 768px) {
  .footer__inner {
    flex-direction: column;
    gap: 0.5rem;
    text-align: center;
  }
}
</style>
