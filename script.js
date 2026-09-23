'use strict';

// Shared by every page. The footer year is the only thing that needs script.
const year = document.getElementById('year');
if (year) year.textContent = String(new Date().getFullYear());
