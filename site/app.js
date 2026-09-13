/**
 * Renewable Asset Intelligence (RAI) — Official Static Site
 * Pure Vanilla JavaScript Client Logic (Zero Dependencies)
 */

document.addEventListener('DOMContentLoaded', () => {
  initNav();
  initProductTabs();
  initEvidenceFilter();
  initLoopInteraction();
});

// Mobile Navigation Toggle
function initNav() {
  const toggle = document.querySelector('.nav-toggle');
  const navLinks = document.querySelector('.nav-links');
  
  if (toggle && navLinks) {
    toggle.addEventListener('click', () => {
      const isOpen = navLinks.classList.toggle('open');
      toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });

    // Close menu when clicking link
    navLinks.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        navLinks.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
      });
    });
  }
}

// Product Walkthrough Tab Switching
function initProductTabs() {
  const tabButtons = document.querySelectorAll('.product-tab-btn');
  const tabPanels = document.querySelectorAll('.product-tab-panel');

  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetTab = btn.getAttribute('data-tab');

      // Update active states on buttons
      tabButtons.forEach(b => {
        b.classList.remove('active');
        b.setAttribute('aria-selected', 'false');
      });
      btn.classList.add('active');
      btn.setAttribute('aria-selected', 'true');

      // Update active panels
      tabPanels.forEach(panel => {
        if (panel.id === targetTab) {
          panel.classList.add('active');
        } else {
          panel.classList.remove('active');
        }
      });
    });
  });
}

// Four-Tier Scientific Evidence Filtering
function initEvidenceFilter() {
  const filterBtns = document.querySelectorAll('.filter-btn');
  const rows = document.querySelectorAll('.evidence-table tbody tr');

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const filter = btn.getAttribute('data-filter');

      // Set active button
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      // Filter rows
      rows.forEach(row => {
        const tier = row.getAttribute('data-tier');
        if (filter === 'all' || tier === filter) {
          row.style.display = '';
        } else {
          row.style.display = 'none';
        }
      });
    });
  });
}

// 10-Stage Decision Loop Interaction
function initLoopInteraction() {
  const steps = document.querySelectorAll('.loop-step-card');
  
  steps.forEach(card => {
    card.addEventListener('mouseenter', () => {
      steps.forEach(s => s.style.opacity = '0.7');
      card.style.opacity = '1';
    });

    card.addEventListener('mouseleave', () => {
      steps.forEach(s => s.style.opacity = '1');
    });
  });
}
